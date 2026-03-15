"""Seed demo content for empty databases."""
import json

from sqlalchemy.orm import Session

from tcm_study_app.config import settings
from tcm_study_app.db import SessionLocal
from tcm_study_app.models import (
    AcupunctureCard,
    ComparisonItem,
    FormulaCard,
    KnowledgeCard,
    Quiz,
    SourceDocument,
    StudyCollection,
    User,
    WarmDiseaseCard,
)

DEMO_USER_ID = 1

DEMO_COLLECTIONS = [
    {
        "title": "方剂学·速测样例",
        "subject": "方剂学",
        "description": "直接用于体验导入后的卡片、比较题和小测。",
        "cards": [
            {
                "title": "桂枝汤",
                "excerpt": "组成：桂枝、芍药、生姜、大枣、甘草。功效：解肌发表，调和营卫。主治：外感风寒表虚证。",
                "normalized_content": {
                    "formula_name": "桂枝汤",
                    "composition": "桂枝、芍药、生姜、大枣、甘草",
                    "effect": "解肌发表，调和营卫",
                    "indication": "外感风寒表虚证",
                    "pathogenesis": "风寒外袭，营卫不和",
                    "usage_notes": "服药后啜热粥以助药力",
                    "memory_tip": "桂枝芍药配伍，重在调和营卫",
                },
            },
            {
                "title": "麻黄汤",
                "excerpt": "组成：麻黄、桂枝、杏仁、甘草。功效：发汗解表，宣肺平喘。主治：外感风寒表实证。",
                "normalized_content": {
                    "formula_name": "麻黄汤",
                    "composition": "麻黄、桂枝、杏仁、甘草",
                    "effect": "发汗解表，宣肺平喘",
                    "indication": "外感风寒表实证",
                    "pathogenesis": "风寒束表，肺气失宣",
                    "usage_notes": "麻黄宜先煎去上沫",
                    "memory_tip": "麻黄汤偏表实，桂枝汤偏表虚",
                },
            },
        ],
        "quizzes": [
            {
                "type": "choice",
                "difficulty": "easy",
                "question": "桂枝汤更常用于哪类表证？",
                "options": [
                    {"key": "A", "value": "风寒表虚证"},
                    {"key": "B", "value": "风寒表实证"},
                    {"key": "C", "value": "湿热内蕴证"},
                    {"key": "D", "value": "血瘀证"},
                ],
                "answer": "A",
                "explanation": "桂枝汤主治外感风寒表虚证，重在调和营卫。",
            }
        ],
        "comparisons": [
            {
                "left_entity": "桂枝汤",
                "right_entity": "麻黄汤",
                "comparison_points": [
                    {"dimension": "表证类型", "left": "表虚", "right": "表实"},
                    {"dimension": "核心治法", "left": "调和营卫", "right": "发汗解表"},
                ],
                "question_text": "请比较桂枝汤与麻黄汤的主治异同。",
                "answer_text": "桂枝汤偏表虚，麻黄汤偏表实，二者都可治风寒表证。",
            }
        ],
    },
    {
        "title": "针灸学·穴位样例",
        "subject": "针灸学",
        "description": "直接体验针灸学知识卡片与测验。",
        "cards": [
            {
                "title": "合谷穴",
                "excerpt": "经络：手阳明大肠经。定位：手背第一、二掌骨间。主治：头痛、牙痛。刺灸法：直刺0.5-1寸。",
                "normalized_content": {
                    "acupoint_name": "合谷穴",
                    "meridian": "手阳明大肠经",
                    "location": "手背第一、二掌骨间，当第二掌骨桡侧中点处",
                    "indication": "头痛、牙痛、面口病证",
                    "technique": "直刺0.5-1寸",
                    "caution": "孕妇慎用强刺激",
                },
            },
            {
                "title": "足三里",
                "excerpt": "经络：足阳明胃经。定位：犊鼻下3寸。主治：胃痛、呕吐、虚劳。刺灸法：直刺1-2寸。",
                "normalized_content": {
                    "acupoint_name": "足三里",
                    "meridian": "足阳明胃经",
                    "location": "犊鼻下3寸，距胫骨前缘一横指",
                    "indication": "胃痛、呕吐、腹胀、虚劳诸证",
                    "technique": "直刺1-2寸",
                    "caution": "局部皮肤破损时避开操作",
                },
            },
        ],
        "quizzes": [
            {
                "type": "choice",
                "difficulty": "easy",
                "question": "足三里所属哪条经脉？",
                "options": [
                    {"key": "A", "value": "足阳明胃经"},
                    {"key": "B", "value": "足少阳胆经"},
                    {"key": "C", "value": "手阳明大肠经"},
                    {"key": "D", "value": "足太阴脾经"},
                ],
                "answer": "A",
                "explanation": "足三里是足阳明胃经的合穴。",
            }
        ],
        "comparisons": [],
    },
    {
        "title": "温病学·辨证样例",
        "subject": "温病学",
        "description": "直接用于体验温病证候卡片与小测。",
        "cards": [
            {
                "title": "卫分证",
                "excerpt": "阶段：卫分。证候：发热，微恶风寒，咽痛。治法：辛凉解表。方药：银翘散。",
                "normalized_content": {
                    "pattern_name": "卫分证",
                    "stage": "卫分",
                    "syndrome": "发热，微恶风寒，咽痛，口微渴",
                    "treatment": "辛凉解表",
                    "formula": "银翘散",
                    "differentiation": "偏表热，病位较浅",
                },
            },
            {
                "title": "气分热盛证",
                "excerpt": "阶段：气分。证候：壮热，大汗，大渴，脉洪大。治法：清气泄热。方药：白虎汤。",
                "normalized_content": {
                    "pattern_name": "气分热盛证",
                    "stage": "气分",
                    "syndrome": "壮热，大汗，大渴，脉洪大",
                    "treatment": "清气泄热",
                    "formula": "白虎汤",
                    "differentiation": "里热炽盛，津液耗伤更明显",
                },
            },
        ],
        "quizzes": [
            {
                "type": "choice",
                "difficulty": "medium",
                "question": "白虎汤更常对应温病哪一阶段的热盛表现？",
                "options": [
                    {"key": "A", "value": "卫分"},
                    {"key": "B", "value": "气分"},
                    {"key": "C", "value": "营分"},
                    {"key": "D", "value": "血分"},
                ],
                "answer": "B",
                "explanation": "白虎汤常用于气分热盛证，见壮热、大汗、大渴、脉洪大。",
            }
        ],
        "comparisons": [],
    },
]


def seed_demo_content_if_needed() -> int:
    """Seed demo content if enabled and the database is still empty."""
    if not settings.seed_demo_content:
        return 0

    db: Session = SessionLocal()
    try:
        return seed_demo_content(db)
    finally:
        db.close()


def seed_demo_content(db: Session) -> int:
    """Seed demo content into the database without duplicating demo sets."""
    user = db.get(User, DEMO_USER_ID)
    if not user:
        user = User(
            id=DEMO_USER_ID,
            email="demo@example.com",
            name="Demo User",
        )
        db.add(user)
        db.flush()

    seeded_collections = 0
    for collection_data in DEMO_COLLECTIONS:
        existing_matches = (
            db.query(StudyCollection)
            .filter(
                StudyCollection.user_id == user.id,
                StudyCollection.title == collection_data["title"],
            )
            .order_by(StudyCollection.id.asc())
            .all()
        )
        if len(existing_matches) > 1:
            for duplicate in existing_matches[1:]:
                db.delete(duplicate)
            db.flush()

        existing = (
            db.query(StudyCollection)
            .filter(
                StudyCollection.user_id == user.id,
                StudyCollection.title == collection_data["title"],
            )
            .first()
        )
        if existing:
            continue

        collection = StudyCollection(
            user_id=user.id,
            title=collection_data["title"],
            subject=collection_data["subject"],
            description=collection_data["description"],
        )
        db.add(collection)
        db.flush()

        for card_data in collection_data["cards"]:
            document = SourceDocument(
                collection_id=collection.id,
                type="text",
                raw_text=card_data["excerpt"],
                status="processed",
            )
            db.add(document)
            db.flush()

            card = KnowledgeCard(
                collection_id=collection.id,
                source_document_id=document.id,
                title=card_data["title"],
                category="formula" if collection.subject == "方剂学" else (
                    "acupuncture" if collection.subject == "针灸学" else "warm_disease"
                ),
                raw_excerpt=card_data["excerpt"],
                normalized_content_json=json.dumps(
                    card_data["normalized_content"], ensure_ascii=False
                ),
            )
            db.add(card)
            db.flush()

            if collection.subject == "方剂学":
                db.add(
                    FormulaCard(
                        knowledge_card_id=card.id,
                        **card_data["normalized_content"],
                    )
                )
            elif collection.subject == "针灸学":
                db.add(
                    AcupunctureCard(
                        knowledge_card_id=card.id,
                        **card_data["normalized_content"],
                    )
                )
            else:
                db.add(
                    WarmDiseaseCard(
                        knowledge_card_id=card.id,
                        **card_data["normalized_content"],
                    )
                )

        for quiz_data in collection_data["quizzes"]:
            db.add(
                Quiz(
                    collection_id=collection.id,
                    type=quiz_data["type"],
                    question=quiz_data["question"],
                    options_json=json.dumps(quiz_data["options"], ensure_ascii=False),
                    answer=quiz_data["answer"],
                    explanation=quiz_data["explanation"],
                    difficulty=quiz_data["difficulty"],
                )
            )

        for comparison_data in collection_data["comparisons"]:
            db.add(
                ComparisonItem(
                    collection_id=collection.id,
                    left_entity=comparison_data["left_entity"],
                    right_entity=comparison_data["right_entity"],
                    comparison_points_json=json.dumps(
                        comparison_data["comparison_points"],
                        ensure_ascii=False,
                    ),
                    question_text=comparison_data["question_text"],
                    answer_text=comparison_data["answer_text"],
                )
            )

        seeded_collections += 1

    db.commit()
    return seeded_collections
