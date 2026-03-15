"""Quiz generator service."""
import json
from typing import Any

from sqlalchemy.orm import Session

from tcm_study_app.core import SubjectDefinition, get_subject_definition
from tcm_study_app.models import KnowledgeCard, Quiz, StudyCollection

OPTION_KEYS = ["A", "B", "C", "D"]

PAPER_MODES = {"quick_practice", "chapter_drill", "final_mock"}

FALLBACK_DISTRACTORS = {
    "formula": {
        "title": ["银翘散", "小柴胡汤", "白虎汤", "四君子汤"],
        "effect": ["辛凉透表，清热解毒", "和解少阳", "清气泄热", "益气健脾"],
        "indication": ["温病初起", "少阳证", "气分热盛证", "脾胃气虚证"],
        "ingredient": ["柴胡", "石膏", "党参", "黄芩"],
        "pair": [
            "和解少阳 / 往来寒热",
            "清气泄热 / 壮热大渴",
            "辛凉解表 / 温病初起",
        ],
    },
    "acupuncture": {
        "title": ["内关", "曲池", "太冲", "神门"],
        "meridian": ["手厥阴心包经", "手阳明大肠经", "足厥阴肝经", "手少阴心经"],
        "indication": ["胸闷心痛", "发热咽痛", "胁痛眩晕", "心悸失眠"],
        "pair": [
            "手厥阴心包经 / 直刺0.5-1寸",
            "手阳明大肠经 / 直刺1-1.5寸",
            "足厥阴肝经 / 直刺0.3-0.5寸",
        ],
    },
    "warm_disease": {
        "title": ["卫分证", "气分热盛证", "营分证", "血分证"],
        "stage": ["卫分", "气分", "营分", "血分"],
        "treatment": ["辛凉解表", "清气泄热", "清营透热", "凉血散血"],
        "formula": ["银翘散", "白虎汤", "清营汤", "犀角地黄汤"],
        "pair": [
            "卫分 / 辛凉解表",
            "气分 / 清气泄热",
            "营分 / 清营透热",
        ],
    },
}


class QuizGenerator:
    """Service for generating subject-aware quiz questions and practice papers."""

    def __init__(self, db: Session):
        self.db = db

    def generate_quizzes(
        self, collection_id: int, count: int = 5, difficulty: str = "medium"
    ) -> list[Quiz]:
        """Generate non-repeating quiz questions for a collection."""
        collection, subject, entries = self._load_collection_context(collection_id)
        self._validate_difficulty(difficulty)

        existing_questions = {
            question
            for question, in self.db.query(Quiz.question)
            .filter(Quiz.collection_id == collection.id, Quiz.difficulty == difficulty)
            .all()
        }

        candidate_payloads = self._build_candidates(subject.key, entries, difficulty)
        fresh_payloads = [
            payload
            for payload in candidate_payloads
            if payload and payload["question"] not in existing_questions
        ]
        selected_payloads = self._select_payloads(fresh_payloads, count)
        if not selected_payloads:
            raise ValueError("No new quizzes available for this collection and difficulty")

        return self._persist_payloads(
            collection_id=collection.id,
            difficulty=difficulty,
            payloads=selected_payloads,
        )

    def generate_paper(
        self,
        collection_id: int,
        mode: str = "final_mock",
        difficulty: str = "medium",
        template: str | None = None,
    ) -> dict[str, Any]:
        """Generate a structured practice paper for a collection."""
        collection, subject, entries = self._load_collection_context(collection_id)
        self._validate_difficulty(difficulty)
        self._validate_mode(mode)

        sections = self._build_paper_sections(subject, entries, difficulty, mode)
        if not sections:
            raise ValueError("No paper sections could be generated for this collection")

        response_sections = []
        total_score = 0
        for section in sections:
            persisted_quizzes = self._persist_payloads(
                collection_id=collection.id,
                difficulty=difficulty,
                payloads=section["questions"],
                skip_existing=False,
            )
            questions = []
            for quiz, payload in zip(persisted_quizzes, section["questions"], strict=False):
                questions.append(
                    {
                        "id": quiz.id,
                        "type": payload["type"],
                        "question": payload["question"],
                        "options": payload.get("options"),
                        "score": payload["score"],
                        "answer": payload.get("answer"),
                        "explanation": payload.get("explanation"),
                        "rubric": payload.get("rubric", []),
                        "answer_template": payload.get("answer_template"),
                    }
                )

            section_total_score = sum(question["score"] for question in questions)
            total_score += section_total_score
            response_sections.append(
                {
                    "title": section["title"],
                    "instructions": section["instructions"],
                    "question_count": len(questions),
                    "total_score": section_total_score,
                    "questions": questions,
                }
            )

        title_suffix = {
            "quick_practice": "速练卷",
            "chapter_drill": "章节训练卷",
            "final_mock": "期末模拟卷",
        }[mode]
        if template:
            title_suffix = f"{title_suffix} · {template}"

        return {
            "paper_title": f"广州中医药大学《{subject.display_name}》{title_suffix}",
            "subject_key": subject.key,
            "subject_display_name": subject.display_name,
            "mode": mode,
            "total_score": total_score,
            "exam_notice": self._paper_notice(subject.key),
            "sections": response_sections,
        }

    def get_quizzes_by_collection(
        self, collection_id: int, limit: int = 10
    ) -> list[Quiz]:
        """Get quizzes for a collection."""
        return (
            self.db.query(Quiz)
            .filter(Quiz.collection_id == collection_id)
            .order_by(Quiz.created_at.desc())
            .limit(limit)
            .all()
        )

    def _load_collection_context(
        self,
        collection_id: int,
    ) -> tuple[StudyCollection, SubjectDefinition, list[dict[str, Any]]]:
        """Load collection, subject definition, and card entries."""
        collection = self.db.get(StudyCollection, collection_id)
        if not collection:
            raise ValueError(f"Collection {collection_id} not found")

        entries = self._load_card_entries(collection_id)
        if not entries:
            raise ValueError("No cards available in collection")

        return collection, get_subject_definition(collection.subject), entries

    def _validate_difficulty(self, difficulty: str) -> None:
        """Validate supported difficulty values."""
        if difficulty not in {"easy", "medium", "hard"}:
            raise ValueError("Difficulty must be easy, medium, or hard")

    def _validate_mode(self, mode: str) -> None:
        """Validate supported practice-paper modes."""
        if mode not in PAPER_MODES:
            raise ValueError(
                "Mode must be quick_practice, chapter_drill, or final_mock"
            )

    def _persist_payloads(
        self,
        collection_id: int,
        difficulty: str,
        payloads: list[dict[str, Any]],
        *,
        skip_existing: bool = True,
    ) -> list[Quiz]:
        """Persist a batch of quiz payloads and return quiz rows."""
        existing_questions = set()
        if skip_existing:
            existing_questions = {
                question
                for question, in self.db.query(Quiz.question)
                .filter(Quiz.collection_id == collection_id, Quiz.difficulty == difficulty)
                .all()
            }

        quizzes = []
        seen_questions = set()
        for payload in payloads:
            question = payload["question"]
            if question in seen_questions:
                continue
            if skip_existing and question in existing_questions:
                continue

            quiz = Quiz(
                collection_id=collection_id,
                type=payload.get("type", "choice"),
                question=question,
                options_json=self._serialize_options(payload.get("options")),
                answer=payload.get("answer") or "",
                explanation=payload.get("explanation"),
                difficulty=difficulty,
            )
            self.db.add(quiz)
            quizzes.append(quiz)
            seen_questions.add(question)

        if not quizzes:
            return []

        self.db.commit()
        for quiz in quizzes:
            self.db.refresh(quiz)
        return quizzes

    def _serialize_options(self, options: list[dict[str, str]] | None) -> str | None:
        """Serialize quiz options for persistence."""
        if not options:
            return None
        return json.dumps(options, ensure_ascii=False)

    def _load_card_entries(self, collection_id: int) -> list[dict[str, Any]]:
        """Load cards and parsed normalized content."""
        cards = (
            self.db.query(KnowledgeCard)
            .filter(KnowledgeCard.collection_id == collection_id)
            .order_by(KnowledgeCard.id.asc())
            .all()
        )

        entries = []
        for card in cards:
            content = {}
            if card.normalized_content_json:
                try:
                    content = json.loads(card.normalized_content_json)
                except json.JSONDecodeError:
                    content = {}

            entries.append(
                {
                    "id": card.id,
                    "title": card.title,
                    "content": content,
                    "card": card,
                }
            )

        return entries

    def _build_candidates(
        self,
        subject_key: str,
        entries: list[dict[str, Any]],
        difficulty: str,
    ) -> list[dict[str, Any]]:
        """Build ordered quiz candidates for a subject and difficulty."""
        candidates = []
        for entry in entries:
            candidates.extend(
                getattr(self, f"_build_{subject_key}_{difficulty}_candidates")(entry, entries)
            )
        return [candidate for candidate in candidates if candidate]

    def _choice_payload(
        self,
        question: str,
        correct_value: str,
        distractor_values: list[str],
        fallback_values: list[str],
        explanation: str,
    ) -> dict[str, Any] | None:
        """Create a stable four-option multiple-choice payload."""
        options_pool = []
        for value in distractor_values + fallback_values:
            if value and value != correct_value and value not in options_pool:
                options_pool.append(value)

        if len(options_pool) < 3:
            return None

        distractors = options_pool[:3]
        correct_index = sum(ord(char) for char in question) % 4
        values = distractors.copy()
        values.insert(correct_index, correct_value)

        options = [
            {"key": key, "value": value}
            for key, value in zip(OPTION_KEYS, values, strict=False)
        ]
        return {
            "type": "choice",
            "question": question,
            "options": options,
            "answer": OPTION_KEYS[correct_index],
            "explanation": explanation,
        }

    def _true_false_payload(
        self,
        question: str,
        is_true: bool,
        explanation: str,
        score: int = 2,
    ) -> dict[str, Any]:
        """Create a true/false question payload."""
        answer = "A" if is_true else "B"
        return {
            "type": "true_false",
            "question": question,
            "options": [
                {"key": "A", "value": "正确"},
                {"key": "B", "value": "错误"},
            ],
            "answer": answer,
            "explanation": explanation,
            "score": score,
        }

    def _subjective_payload(
        self,
        *,
        question_type: str,
        question: str,
        answer: str,
        explanation: str,
        score: int,
        rubric: list[str],
        answer_template: str,
    ) -> dict[str, Any]:
        """Create a subjective question payload."""
        return {
            "type": question_type,
            "question": question,
            "answer": answer,
            "explanation": explanation,
            "score": score,
            "rubric": rubric,
            "answer_template": answer_template,
        }

    def _select_payloads(
        self,
        payloads: list[dict[str, Any]],
        count: int,
        *,
        score: int | None = None,
        forced_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Take a stable deduplicated subset of payloads."""
        selected = []
        seen_questions = set()
        for payload in payloads:
            if not payload:
                continue

            question = payload["question"]
            if question in seen_questions:
                continue

            cloned = self._clone_payload(payload)
            if score is not None:
                cloned["score"] = score
            if forced_type:
                cloned["type"] = forced_type
            cloned.setdefault("rubric", [])
            selected.append(cloned)
            seen_questions.add(question)
            if len(selected) >= count:
                break

        return selected

    def _clone_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Create a shallow-safe copy of a question payload."""
        cloned = dict(payload)
        if payload.get("options"):
            cloned["options"] = [dict(option) for option in payload["options"]]
        if payload.get("rubric"):
            cloned["rubric"] = list(payload["rubric"])
        return cloned

    def _paper_notice(self, subject_key: str) -> str:
        """Return the notice line shown on the simulated exam paper."""
        if subject_key == "acupuncture":
            return "请考生用黑色笔作答，先写取穴结论，再补充经络依据、手法与配穴原则。"
        if subject_key == "warm_disease":
            return "请考生用黑色笔作答，主观题按病因、病机、辨证、治则、方药顺序作答。"
        return "请考生用黑色笔作答，先写辨证结论，再补充病机、治法与方药要点。"

    def _paper_choice_questions(
        self,
        subject_key: str,
        entries: list[dict[str, Any]],
        difficulty: str,
        count: int,
        score: int,
    ) -> list[dict[str, Any]]:
        """Build objective-choice questions for paper sections."""
        payloads = self._build_candidates(subject_key, entries, difficulty)
        return self._select_payloads(
            payloads,
            count,
            score=score,
            forced_type="single_choice",
        )

    def _build_paper_sections(
        self,
        subject: SubjectDefinition,
        entries: list[dict[str, Any]],
        difficulty: str,
        mode: str,
    ) -> list[dict[str, Any]]:
        """Build paper sections for a given subject and mode."""
        builder = getattr(self, f"_build_{subject.key}_paper_sections")
        return builder(entries, difficulty, mode)

    def _section(
        self,
        title: str,
        instructions: str,
        questions: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        """Create a paper section if it has questions."""
        if not questions:
            return None
        return {
            "title": title,
            "instructions": instructions,
            "questions": questions,
        }

    def _build_formula_paper_sections(
        self,
        entries: list[dict[str, Any]],
        difficulty: str,
        mode: str,
    ) -> list[dict[str, Any]]:
        """Build paper sections for formula collections."""
        choice_count = {"quick_practice": 5, "chapter_drill": 4, "final_mock": 6}[mode]
        sections = [
            self._section(
                "一、单项选择题",
                "下列各题只有一个最佳答案，请选择最符合方义与主治的选项。",
                self._paper_choice_questions("formula", entries, difficulty, choice_count, 2),
            ),
        ]

        if mode == "quick_practice":
            return [section for section in sections if section]

        term_questions = self._select_payloads(
            self._build_formula_term_questions(entries),
            2 if mode == "chapter_drill" else 3,
        )
        short_questions = self._select_payloads(
            self._build_formula_short_answer_questions(entries),
            1 if mode == "chapter_drill" else 2,
        )
        sections.append(
            self._section(
                "二、名词解释",
                "概述方剂组成、功效与主治要点，重点突出辨证定位。",
                term_questions,
            )
        )
        sections.append(
            self._section(
                "三、简答题",
                "围绕病机、治法和方义作答，避免只罗列药物名称。",
                short_questions,
            )
        )

        if mode == "final_mock":
            case_questions = self._select_payloads(
                self._build_formula_case_questions(entries),
                1,
            )
            sections.append(
                self._section(
                    "四、病例分析题",
                    "先写辨证与选方，再展开病机分析和加减思路。",
                    case_questions,
                )
            )

        return [section for section in sections if section]

    def _build_acupuncture_paper_sections(
        self,
        entries: list[dict[str, Any]],
        difficulty: str,
        mode: str,
    ) -> list[dict[str, Any]]:
        """Build paper sections for acupuncture collections."""
        sections = [
            self._section(
                "一、单项选择题",
                "根据经络归属、定位、主治与刺灸法选择最佳答案。",
                self._paper_choice_questions(
                    "acupuncture",
                    entries,
                    difficulty,
                    4 if mode == "quick_practice" else 5 if mode == "chapter_drill" else 6,
                    2,
                ),
            )
        ]

        if mode != "quick_practice":
            sections.append(
                self._section(
                    "二、判断题",
                    "判断下列说法是否正确，并留意常见的经络归属与操作混淆点。",
                    self._select_payloads(
                        self._build_acupuncture_true_false_questions(entries),
                        3 if mode == "chapter_drill" else 4,
                    ),
                )
            )
            sections.append(
                self._section(
                    "三、名词解释",
                    "以穴位为核心，交代归经、定位与主治，不宜只写单一属性。",
                    self._select_payloads(
                        self._build_acupuncture_term_questions(entries),
                        2 if mode == "chapter_drill" else 3,
                    ),
                )
            )
            sections.append(
                self._section(
                    "四、简答题",
                    "说明临床取穴思路、穴位主治与刺法要点。",
                    self._select_payloads(
                        self._build_acupuncture_short_answer_questions(entries),
                        2,
                    ),
                )
            )

        if mode == "final_mock":
            sections.append(
                self._section(
                    "五、论述 / 病例分析题",
                    "按辨病、辨经、取穴、手法、加减原则完整作答。",
                    self._select_payloads(
                        self._build_acupuncture_case_questions(entries),
                        1,
                    ),
                )
            )

        return [section for section in sections if section]

    def _build_warm_disease_paper_sections(
        self,
        entries: list[dict[str, Any]],
        difficulty: str,
        mode: str,
    ) -> list[dict[str, Any]]:
        """Build paper sections for warm-disease collections."""
        sections = [
            self._section(
                "一、选择题",
                "围绕卫气营血辨证、三焦辨证、病机要点与代表方剂作答。",
                self._paper_choice_questions(
                    "warm_disease",
                    entries,
                    difficulty,
                    5 if mode == "quick_practice" else 4 if mode == "chapter_drill" else 6,
                    2,
                ),
            )
        ]

        if mode == "quick_practice":
            return [section for section in sections if section]

        sections.append(
            self._section(
                "二、名词解释",
                "交代证候定位、临床表现、治法与代表方，不要只写一句定义。",
                self._select_payloads(
                    self._build_warm_disease_term_questions(entries),
                    2 if mode == "chapter_drill" else 3,
                ),
            )
        )
        sections.append(
            self._section(
                "三、简答题",
                "按病机分析、辨证要点、治法与方药展开作答。",
                self._select_payloads(
                    self._build_warm_disease_short_answer_questions(entries),
                    1 if mode == "chapter_drill" else 2,
                ),
            )
        )

        if mode == "final_mock":
            sections.append(
                self._section(
                    "四、论述 / 病例分析题",
                    "先给出辨证结论，再完整写出病机、治则、方药与辨证依据。",
                    self._select_payloads(
                        self._build_warm_disease_case_questions(entries),
                        1,
                    ),
                )
            )

        return [section for section in sections if section]

    def _other_field_values(
        self,
        entries: list[dict[str, Any]],
        current_id: int,
        field_name: str,
    ) -> list[str]:
        """Collect field values from other cards in the same collection."""
        values = []
        for entry in entries:
            if entry["id"] == current_id:
                continue
            value = entry["content"].get(field_name)
            if value and value not in values:
                values.append(value)
        return values

    def _other_titles(self, entries: list[dict[str, Any]], current_id: int) -> list[str]:
        """Collect titles from other cards in the same collection."""
        return [
            entry["title"]
            for entry in entries
            if entry["id"] != current_id and entry["title"]
        ]

    def _split_items(self, text: str | None) -> list[str]:
        """Split a structured list-like string into stable item tokens."""
        if not text:
            return []

        normalized = text.replace("、", ",").replace("，", ",").replace("；", ",")
        return [item.strip() for item in normalized.split(",") if item.strip()]

    def _formula_fallback(self, field_name: str) -> list[str]:
        """Get fallback distractors for formula quizzes."""
        return FALLBACK_DISTRACTORS["formula"].get(field_name, [])

    def _acupuncture_fallback(self, field_name: str) -> list[str]:
        """Get fallback distractors for acupuncture quizzes."""
        return FALLBACK_DISTRACTORS["acupuncture"].get(field_name, [])

    def _warm_disease_fallback(self, field_name: str) -> list[str]:
        """Get fallback distractors for warm-disease quizzes."""
        return FALLBACK_DISTRACTORS["warm_disease"].get(field_name, [])

    def _build_formula_term_questions(
        self,
        entries: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Build formula term-explanation questions."""
        questions = []
        for entry in entries:
            content = entry["content"]
            composition = content.get("composition")
            effect = content.get("effect")
            indication = content.get("indication")
            if not (composition and effect and indication):
                continue

            questions.append(
                self._subjective_payload(
                    question_type="term_explanation",
                    question=f"名词解释：{entry['title']}。请写出其组成、功效与主治要点。",
                    answer=(
                        f"{entry['title']}组成：{composition}；功效：{effect}；主治：{indication}。"
                    ),
                    explanation=f"{entry['title']}的复习重点在于方义、功效与主治之间的对应关系。",
                    score=4,
                    rubric=[
                        f"写出组成：{composition}",
                        f"写出功效：{effect}",
                        f"写出主治：{indication}",
                    ],
                    answer_template="组成 -> 功效 -> 主治",
                )
            )
        return questions

    def _build_formula_short_answer_questions(
        self,
        entries: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Build formula short-answer questions."""
        questions = []
        for entry in entries:
            content = entry["content"]
            pathogenesis = content.get("pathogenesis")
            effect = content.get("effect")
            usage_notes = content.get("usage_notes")
            if not (pathogenesis and effect):
                continue

            answer = f"病机：{pathogenesis}；治法与功效：{effect}。"
            if usage_notes:
                answer += f" 用法要点：{usage_notes}。"

            questions.append(
                self._subjective_payload(
                    question_type="short_answer",
                    question=f"简答：试述{entry['title']}的病机、治法与方义要点。",
                    answer=answer,
                    explanation=f"{entry['title']}答题时要把病机与功效对应起来，而不是孤立背药物。",
                    score=8,
                    rubric=[
                        f"答出病机：{pathogenesis}",
                        f"答出治法/功效：{effect}",
                        "能说明方义或配伍特点",
                    ],
                    answer_template="病机 -> 治法 -> 方义",
                )
            )
        return questions

    def _build_formula_case_questions(
        self,
        entries: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Build formula case-analysis questions."""
        questions = []
        for entry in entries:
            content = entry["content"]
            indication = content.get("indication")
            pathogenesis = content.get("pathogenesis")
            effect = content.get("effect")
            if not (indication and pathogenesis and effect):
                continue

            questions.append(
                self._subjective_payload(
                    question_type="case_analysis",
                    question=(
                        f"病例分析：患者表现为“{indication}”。请辨证分析病机，"
                        f"并说明为何选用{entry['title']}。"
                    ),
                    answer=(
                        f"辨证可归于{indication}所对应证型；病机为{pathogenesis}；"
                        f"治法应把握{effect}，故选{entry['title']}。"
                    ),
                    explanation=f"{entry['title']}病例题建议按辨证、病机、治法、选方理由四步作答。",
                    score=12,
                    rubric=[
                        f"辨证扣住：{indication}",
                        f"病机写出：{pathogenesis}",
                        f"治法/功效写出：{effect}",
                        f"明确选方：{entry['title']}",
                    ],
                    answer_template="辨证 -> 病机 -> 治法 -> 选方理由",
                )
            )
        return questions

    def _build_acupuncture_true_false_questions(
        self,
        entries: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Build acupuncture true/false questions."""
        questions = []
        for index, entry in enumerate(entries):
            content = entry["content"]
            meridian = content.get("meridian")
            location = content.get("location")
            if not meridian:
                continue

            if index % 2 == 0:
                questions.append(
                    self._true_false_payload(
                        question=f"判断：{entry['title']}归属{meridian}。",
                        is_true=True,
                        explanation=f"{entry['title']}的确归属{meridian}。",
                    )
                )
                continue

            distractor_meridians = self._other_field_values(entries, entry["id"], "meridian")
            false_meridian = distractor_meridians[0] if distractor_meridians else None
            if false_meridian:
                questions.append(
                    self._true_false_payload(
                        question=f"判断：{entry['title']}归属{false_meridian}。",
                        is_true=False,
                        explanation=f"{entry['title']}实际归属{meridian}。",
                    )
                )
            elif location:
                questions.append(
                    self._true_false_payload(
                        question=f"判断：{entry['title']}定位在“{location}”。",
                        is_true=True,
                        explanation=f"{entry['title']}定位要点就是{location}。",
                    )
                )
        return questions

    def _build_acupuncture_term_questions(
        self,
        entries: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Build acupuncture term-explanation questions."""
        questions = []
        for entry in entries:
            content = entry["content"]
            meridian = content.get("meridian")
            location = content.get("location")
            indication = content.get("indication")
            if not (meridian and location and indication):
                continue

            questions.append(
                self._subjective_payload(
                    question_type="term_explanation",
                    question=f"名词解释：{entry['title']}。请写出归经、定位与主治要点。",
                    answer=(
                        f"{entry['title']}归{meridian}；定位：{location}；主治：{indication}。"
                    ),
                    explanation=f"{entry['title']}作答时应完整覆盖归经、定位与主治三项。",
                    score=4,
                    rubric=[
                        f"归经：{meridian}",
                        f"定位：{location}",
                        f"主治：{indication}",
                    ],
                    answer_template="归经 -> 定位 -> 主治",
                )
            )
        return questions

    def _build_acupuncture_short_answer_questions(
        self,
        entries: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Build acupuncture short-answer questions."""
        questions = []
        for entry in entries:
            content = entry["content"]
            indication = content.get("indication")
            technique = content.get("technique")
            caution = content.get("caution")
            if not (indication and technique):
                continue

            answer = f"主治：{indication}；刺灸法：{technique}。"
            if caution:
                answer += f" 注意事项：{caution}。"

            questions.append(
                self._subjective_payload(
                    question_type="short_answer",
                    question=f"简答：试述{entry['title']}的主治特点、操作要点及临床注意事项。",
                    answer=answer,
                    explanation=f"{entry['title']}的简答题一般要求把主治、操作和注意事项一起写全。",
                    score=8,
                    rubric=[
                        f"写出主治：{indication}",
                        f"写出操作：{technique}",
                        "补充注意事项或适用场景",
                    ],
                    answer_template="主治 -> 刺灸法 -> 注意事项",
                )
            )
        return questions

    def _build_acupuncture_case_questions(
        self,
        entries: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Build acupuncture case-analysis questions."""
        questions = []
        for entry in entries:
            content = entry["content"]
            meridian = content.get("meridian")
            indication = content.get("indication")
            technique = content.get("technique")
            if not (meridian and indication and technique):
                continue

            questions.append(
                self._subjective_payload(
                    question_type="case_analysis",
                    question=(
                        f"病例分析：患者以“{indication}”为主诉。请从辨病辨经、取穴依据、"
                        f"针刺手法三个方面说明为何优先选用{entry['title']}。"
                    ),
                    answer=(
                        f"{entry['title']}归{meridian}，其主治涵盖{indication}；"
                        f"操作上可采用{technique}，并结合病位与经络循行加减配穴。"
                    ),
                    explanation="针灸病例题应先写取穴结论，再说明经络依据和手法。",
                    score=12,
                    rubric=[
                        f"辨经依据：{meridian}",
                        f"主治对应：{indication}",
                        f"手法写出：{technique}",
                        "补充配穴或加减思路",
                    ],
                    answer_template="辨病/辨经 -> 取穴 -> 手法 -> 配穴原则",
                )
            )
        return questions

    def _build_warm_disease_term_questions(
        self,
        entries: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Build warm-disease term-explanation questions."""
        questions = []
        for entry in entries:
            content = entry["content"]
            stage = content.get("stage")
            syndrome = content.get("syndrome")
            treatment = content.get("treatment")
            formula = content.get("formula")
            if not (stage and syndrome and treatment):
                continue

            answer = f"{entry['title']}属{stage}阶段；临床表现为{syndrome}；治法为{treatment}。"
            if formula:
                answer += f" 常用方药为{formula}。"

            rubric = [
                f"所属阶段：{stage}",
                f"临床表现：{syndrome}",
                f"治法：{treatment}",
            ]
            if formula:
                rubric.append(f"代表方：{formula}")

            questions.append(
                self._subjective_payload(
                    question_type="term_explanation",
                    question=f"名词解释：{entry['title']}。请概述其临床表现及治法。",
                    answer=answer,
                    explanation=f"{entry['title']}名词解释题要把‘阶段+表现+治法+方药’写完整。",
                    score=4,
                    rubric=rubric,
                    answer_template="阶段 -> 临床表现 -> 治法 -> 方药",
                )
            )
        return questions

    def _build_warm_disease_short_answer_questions(
        self,
        entries: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Build warm-disease short-answer questions."""
        questions = []
        for entry in entries:
            content = entry["content"]
            differentiation = content.get("differentiation")
            treatment = content.get("treatment")
            formula = content.get("formula")
            syndrome = content.get("syndrome")
            if not (differentiation and treatment and syndrome):
                continue

            answer = f"病机与辨证要点：{differentiation}；治法：{treatment}。"
            if formula:
                answer += f" 代表方：{formula}。"

            rubric = [
                f"病机/辨证要点：{differentiation}",
                f"治法：{treatment}",
                f"症状依据：{syndrome}",
            ]
            if formula:
                rubric.append(f"方药：{formula}")

            questions.append(
                self._subjective_payload(
                    question_type="short_answer",
                    question=f"简答：试述{entry['title']}的病机特点、辨证要点及治疗原则。",
                    answer=answer,
                    explanation="温病学简答题要避免只背方名，核心是把辨证依据与治法连起来。",
                    score=8,
                    rubric=rubric,
                    answer_template="病机 -> 辨证要点 -> 治法 -> 方药",
                )
            )
        return questions

    def _build_warm_disease_case_questions(
        self,
        entries: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Build warm-disease case-analysis questions."""
        questions = []
        for entry in entries:
            content = entry["content"]
            syndrome = content.get("syndrome")
            treatment = content.get("treatment")
            formula = content.get("formula")
            differentiation = content.get("differentiation")
            if not (syndrome and treatment and differentiation):
                continue

            answer = (
                f"辨证：{entry['title']}；病机特点：{differentiation}；治法：{treatment}。"
            )
            if formula:
                answer += f" 方药宜选{formula}。"

            rubric = [
                f"辨证结论：{entry['title']}",
                f"病机特点：{differentiation}",
                f"治法：{treatment}",
                f"症状依据：{syndrome}",
            ]
            if formula:
                rubric.append(f"代表方：{formula}")

            questions.append(
                self._subjective_payload(
                    question_type="case_analysis",
                    question=(
                        f"病例分析：患者见“{syndrome}”。请完成辨证，并写出病机、"
                        "治则与代表方药。"
                    ),
                    answer=answer,
                    explanation="温病病例题建议固定按辨证、病机、治法、方药顺序作答。",
                    score=12,
                    rubric=rubric,
                    answer_template="辨证 -> 病机 -> 治法 -> 方药",
                )
            )
        return questions

    def _build_formula_easy_candidates(
        self,
        entry: dict[str, Any],
        entries: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Build easy formula quizzes."""
        content = entry["content"]
        candidates = []

        effect = content.get("effect")
        if effect:
            candidates.append(
                self._choice_payload(
                    question=f"下列哪项是{entry['title']}的功效？",
                    correct_value=effect,
                    distractor_values=self._other_field_values(entries, entry["id"], "effect"),
                    fallback_values=self._formula_fallback("effect"),
                    explanation=f"{entry['title']}的核心功效是{effect}。",
                )
            )

        indication = content.get("indication")
        if indication:
            candidates.append(
                self._choice_payload(
                    question=f"{entry['title']}更常用于哪类主治？",
                    correct_value=indication,
                    distractor_values=self._other_field_values(entries, entry["id"], "indication"),
                    fallback_values=self._formula_fallback("indication"),
                    explanation=f"{entry['title']}常见主治为{indication}。",
                )
            )

        ingredients = self._split_items(content.get("composition"))
        if ingredients:
            candidates.append(
                self._choice_payload(
                    question=f"以下哪味药属于{entry['title']}的组成？",
                    correct_value=ingredients[0],
                    distractor_values=[
                        ingredient
                        for other in entries
                        if other["id"] != entry["id"]
                        for ingredient in self._split_items(other["content"].get("composition"))
                    ],
                    fallback_values=self._formula_fallback("ingredient"),
                    explanation=f"{entry['title']}的组成包含{ingredients[0]}。",
                )
            )

        return candidates

    def _build_formula_medium_candidates(
        self,
        entry: dict[str, Any],
        entries: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Build medium formula quizzes."""
        content = entry["content"]
        candidates = []

        effect = content.get("effect")
        if effect:
            candidates.append(
                self._choice_payload(
                    question=f"已知功效“{effect}”，最可能对应哪首方剂？",
                    correct_value=entry["title"],
                    distractor_values=self._other_titles(entries, entry["id"]),
                    fallback_values=self._formula_fallback("title"),
                    explanation=f"功效“{effect}”对应的方剂是{entry['title']}。",
                )
            )

        indication = content.get("indication")
        if effect and indication:
            pair = f"{effect} / {indication}"
            distractor_pairs = []
            for other in entries:
                if other["id"] == entry["id"]:
                    continue
                other_effect = other["content"].get("effect")
                other_indication = other["content"].get("indication")
                if other_effect and other_indication:
                    distractor_pairs.append(f"{other_effect} / {other_indication}")

            candidates.append(
                self._choice_payload(
                    question=f"下列哪个“功效 / 主治”组合最符合{entry['title']}？",
                    correct_value=pair,
                    distractor_values=distractor_pairs,
                    fallback_values=self._formula_fallback("pair"),
                    explanation=f"{entry['title']}对应“{pair}”。",
                )
            )

        return candidates

    def _build_formula_hard_candidates(
        self,
        entry: dict[str, Any],
        entries: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Build hard formula quizzes."""
        content = entry["content"]
        candidates = []

        indication = content.get("indication")
        pathogenesis = content.get("pathogenesis")
        if indication and pathogenesis:
            candidates.append(
                self._choice_payload(
                    question=f"若见“{indication}”，并判断病机偏向“{pathogenesis}”，较合适的方剂是？",
                    correct_value=entry["title"],
                    distractor_values=self._other_titles(entries, entry["id"]),
                    fallback_values=self._formula_fallback("title"),
                    explanation=f"结合主治和病机，更贴近的方剂是{entry['title']}。",
                )
            )

        effect = content.get("effect")
        usage_notes = content.get("usage_notes")
        if effect and usage_notes:
            candidates.append(
                self._choice_payload(
                    question=f"若需要同时把握“{effect}”与“{usage_notes}”，应优先联想到哪首方剂？",
                    correct_value=entry["title"],
                    distractor_values=self._other_titles(entries, entry["id"]),
                    fallback_values=self._formula_fallback("title"),
                    explanation=f"{entry['title']}既强调“{effect}”，又有“{usage_notes}”这个用法要点。",
                )
            )

        return candidates

    def _build_acupuncture_easy_candidates(
        self,
        entry: dict[str, Any],
        entries: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Build easy acupuncture quizzes."""
        content = entry["content"]
        candidates = []

        meridian = content.get("meridian")
        if meridian:
            candidates.append(
                self._choice_payload(
                    question=f"{entry['title']}所属哪条经脉？",
                    correct_value=meridian,
                    distractor_values=self._other_field_values(entries, entry["id"], "meridian"),
                    fallback_values=self._acupuncture_fallback("meridian"),
                    explanation=f"{entry['title']}归属{meridian}。",
                )
            )

        indication = content.get("indication")
        if indication:
            candidates.append(
                self._choice_payload(
                    question=f"{entry['title']}更常见于哪类主治？",
                    correct_value=indication,
                    distractor_values=self._other_field_values(entries, entry["id"], "indication"),
                    fallback_values=self._acupuncture_fallback("indication"),
                    explanation=f"{entry['title']}常见主治包括{indication}。",
                )
            )

        return candidates

    def _build_acupuncture_medium_candidates(
        self,
        entry: dict[str, Any],
        entries: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Build medium acupuncture quizzes."""
        content = entry["content"]
        candidates = []

        location = content.get("location")
        if location:
            candidates.append(
                self._choice_payload(
                    question=f"定位为“{location}”的穴位最可能是？",
                    correct_value=entry["title"],
                    distractor_values=self._other_titles(entries, entry["id"]),
                    fallback_values=self._acupuncture_fallback("title"),
                    explanation=f"这个定位对应的穴位是{entry['title']}。",
                )
            )

        meridian = content.get("meridian")
        indication = content.get("indication")
        if meridian and indication:
            candidates.append(
                self._choice_payload(
                    question=f"下列哪个穴位最符合“{meridian} + {indication}”这个组合？",
                    correct_value=entry["title"],
                    distractor_values=self._other_titles(entries, entry["id"]),
                    fallback_values=self._acupuncture_fallback("title"),
                    explanation=f"同时符合经脉和主治特点的穴位是{entry['title']}。",
                )
            )

        return candidates

    def _build_acupuncture_hard_candidates(
        self,
        entry: dict[str, Any],
        entries: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Build hard acupuncture quizzes."""
        content = entry["content"]
        candidates = []

        indication = content.get("indication")
        location = content.get("location")
        if indication and location:
            candidates.append(
                self._choice_payload(
                    question=f"若需要处理“{indication}”，且取穴位于“{location}”，优先想到哪一穴？",
                    correct_value=entry["title"],
                    distractor_values=self._other_titles(entries, entry["id"]),
                    fallback_values=self._acupuncture_fallback("title"),
                    explanation=f"结合主治和定位，应优先想到{entry['title']}。",
                )
            )

        meridian = content.get("meridian")
        technique = content.get("technique")
        if meridian and technique:
            pair = f"{meridian} / {technique}"
            distractor_pairs = []
            for other in entries:
                if other["id"] == entry["id"]:
                    continue
                other_meridian = other["content"].get("meridian")
                other_technique = other["content"].get("technique")
                if other_meridian and other_technique:
                    distractor_pairs.append(f"{other_meridian} / {other_technique}")

            candidates.append(
                self._choice_payload(
                    question=f"下列哪个“经脉 / 刺灸法”组合最贴近{entry['title']}？",
                    correct_value=pair,
                    distractor_values=distractor_pairs,
                    fallback_values=self._acupuncture_fallback("pair"),
                    explanation=f"{entry['title']}对应“{pair}”。",
                )
            )

        return candidates

    def _build_warm_disease_easy_candidates(
        self,
        entry: dict[str, Any],
        entries: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Build easy warm-disease quizzes."""
        content = entry["content"]
        candidates = []

        stage = content.get("stage")
        if stage:
            candidates.append(
                self._choice_payload(
                    question=f"{entry['title']}属于温病哪一阶段？",
                    correct_value=stage,
                    distractor_values=self._other_field_values(entries, entry["id"], "stage"),
                    fallback_values=self._warm_disease_fallback("stage"),
                    explanation=f"{entry['title']}归属{stage}阶段。",
                )
            )

        treatment = content.get("treatment")
        if treatment:
            candidates.append(
                self._choice_payload(
                    question=f"{entry['title']}常用哪种治法？",
                    correct_value=treatment,
                    distractor_values=self._other_field_values(entries, entry["id"], "treatment"),
                    fallback_values=self._warm_disease_fallback("treatment"),
                    explanation=f"{entry['title']}的常见治法是{treatment}。",
                )
            )

        return candidates

    def _build_warm_disease_medium_candidates(
        self,
        entry: dict[str, Any],
        entries: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Build medium warm-disease quizzes."""
        content = entry["content"]
        candidates = []

        syndrome = content.get("syndrome")
        if syndrome:
            candidates.append(
                self._choice_payload(
                    question=f"见“{syndrome}”，最可能辨为哪一证候？",
                    correct_value=entry["title"],
                    distractor_values=self._other_titles(entries, entry["id"]),
                    fallback_values=self._warm_disease_fallback("title"),
                    explanation=f"结合症状描述，更贴近的证候是{entry['title']}。",
                )
            )

        formula = content.get("formula")
        if formula:
            candidates.append(
                self._choice_payload(
                    question=f"下列哪项最符合{entry['title']}的代表方药？",
                    correct_value=formula,
                    distractor_values=self._other_field_values(entries, entry["id"], "formula"),
                    fallback_values=self._warm_disease_fallback("formula"),
                    explanation=f"{entry['title']}的代表方药是{formula}。",
                )
            )

        return candidates

    def _build_warm_disease_hard_candidates(
        self,
        entry: dict[str, Any],
        entries: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Build hard warm-disease quizzes."""
        content = entry["content"]
        candidates = []

        syndrome = content.get("syndrome")
        treatment = content.get("treatment")
        if syndrome and treatment:
            candidates.append(
                self._choice_payload(
                    question=f"若见“{syndrome}”，并拟采用“{treatment}”，最符合哪一证候？",
                    correct_value=entry["title"],
                    distractor_values=self._other_titles(entries, entry["id"]),
                    fallback_values=self._warm_disease_fallback("title"),
                    explanation=f"该症状与治法组合最匹配的证候是{entry['title']}。",
                )
            )

        stage = content.get("stage")
        if stage and treatment:
            pair = f"{stage} / {treatment}"
            distractor_pairs = []
            for other in entries:
                if other["id"] == entry["id"]:
                    continue
                other_stage = other["content"].get("stage")
                other_treatment = other["content"].get("treatment")
                if other_stage and other_treatment:
                    distractor_pairs.append(f"{other_stage} / {other_treatment}")

            candidates.append(
                self._choice_payload(
                    question=f"下列哪个“阶段 / 治法”组合最贴近{entry['title']}？",
                    correct_value=pair,
                    distractor_values=distractor_pairs,
                    fallback_values=self._warm_disease_fallback("pair"),
                    explanation=f"{entry['title']}对应“{pair}”。",
                )
            )

        return candidates


def create_quiz_generator(db: Session) -> QuizGenerator:
    """Factory function to create QuizGenerator."""
    return QuizGenerator(db)
