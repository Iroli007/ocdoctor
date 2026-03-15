"""Quiz generator service."""
import json

from sqlalchemy.orm import Session

from tcm_study_app.core import get_subject_definition
from tcm_study_app.models import KnowledgeCard, Quiz, StudyCollection

OPTION_KEYS = ["A", "B", "C", "D"]

FALLBACK_DISTRACTORS = {
    "formula": {
        "title": ["银翘散", "小柴胡汤", "白虎汤", "四君子汤"],
        "effect": ["辛凉透表，清热解毒", "和解少阳", "清气分热", "益气健脾"],
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
    """Service for generating subject-aware quiz questions."""

    def __init__(self, db: Session):
        self.db = db

    def generate_quizzes(
        self, collection_id: int, count: int = 5, difficulty: str = "medium"
    ) -> list[Quiz]:
        """Generate non-repeating quiz questions for a collection."""
        collection = self.db.get(StudyCollection, collection_id)
        if not collection:
            raise ValueError(f"Collection {collection_id} not found")

        if difficulty not in {"easy", "medium", "hard"}:
            raise ValueError("Difficulty must be easy, medium, or hard")

        subject = get_subject_definition(collection.subject)
        entries = self._load_card_entries(collection_id)
        if not entries:
            raise ValueError("No cards available in collection")

        existing_questions = {
            question
            for question, in self.db.query(Quiz.question)
            .filter(Quiz.collection_id == collection_id, Quiz.difficulty == difficulty)
            .all()
        }

        candidate_payloads = self._build_candidates(subject.key, entries, difficulty)

        quizzes = []
        for payload in candidate_payloads:
            if payload["question"] in existing_questions:
                continue

            quiz = Quiz(
                collection_id=collection_id,
                type=payload.get("type", "choice"),
                question=payload["question"],
                options_json=json.dumps(payload["options"], ensure_ascii=False),
                answer=payload["answer"],
                explanation=payload.get("explanation"),
                difficulty=difficulty,
            )
            self.db.add(quiz)
            quizzes.append(quiz)
            existing_questions.add(payload["question"])

            if len(quizzes) >= count:
                break

        if not quizzes:
            raise ValueError("No new quizzes available for this collection and difficulty")

        self.db.commit()
        for quiz in quizzes:
            self.db.refresh(quiz)

        return quizzes

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

    def _load_card_entries(self, collection_id: int) -> list[dict]:
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
        entries: list[dict],
        difficulty: str,
    ) -> list[dict]:
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
    ) -> dict | None:
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

    def _other_field_values(
        self,
        entries: list[dict],
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

    def _other_titles(self, entries: list[dict], current_id: int) -> list[str]:
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

    def _build_formula_easy_candidates(self, entry: dict, entries: list[dict]) -> list[dict]:
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

    def _build_formula_medium_candidates(self, entry: dict, entries: list[dict]) -> list[dict]:
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

    def _build_formula_hard_candidates(self, entry: dict, entries: list[dict]) -> list[dict]:
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

    def _build_acupuncture_easy_candidates(self, entry: dict, entries: list[dict]) -> list[dict]:
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

    def _build_acupuncture_medium_candidates(self, entry: dict, entries: list[dict]) -> list[dict]:
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

    def _build_acupuncture_hard_candidates(self, entry: dict, entries: list[dict]) -> list[dict]:
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

    def _build_warm_disease_easy_candidates(self, entry: dict, entries: list[dict]) -> list[dict]:
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

    def _build_warm_disease_medium_candidates(self, entry: dict, entries: list[dict]) -> list[dict]:
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

    def _build_warm_disease_hard_candidates(self, entry: dict, entries: list[dict]) -> list[dict]:
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
