"""Seed demo content for ready-to-test collections."""
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
        "description": "直接用于体验导入后的卡片、比较题和多难度小测。",
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
            {
                "title": "银翘散",
                "excerpt": "组成：银花、连翘、桔梗、薄荷、牛蒡子、竹叶等。功效：辛凉透表，清热解毒。主治：温病初起。",
                "normalized_content": {
                    "formula_name": "银翘散",
                    "composition": "银花、连翘、桔梗、薄荷、牛蒡子、竹叶、荆芥穗、淡豆豉、甘草",
                    "effect": "辛凉透表，清热解毒",
                    "indication": "温病初起，风热犯表证",
                    "pathogenesis": "风热袭表，热毒初起",
                    "usage_notes": "香气大出，即取服，勿过煎",
                    "memory_tip": "银花连翘为君，重在清热解毒",
                },
            },
            {
                "title": "白虎汤",
                "excerpt": "组成：石膏、知母、甘草、粳米。功效：清热生津。主治：气分热盛证。",
                "normalized_content": {
                    "formula_name": "白虎汤",
                    "composition": "石膏、知母、甘草、粳米",
                    "effect": "清热生津",
                    "indication": "气分热盛证，见壮热、大汗、大渴、脉洪大",
                    "pathogenesis": "阳明气分热盛，津液受损",
                    "usage_notes": "石膏宜先煎，热盛津伤者尤宜",
                    "memory_tip": "白虎汤抓大热、大渴、大汗、脉洪",
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
        "description": "直接体验针灸学知识卡片与多难度小测。",
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
            {
                "title": "内关",
                "excerpt": "经络：手厥阴心包经。定位：腕横纹上2寸。主治：胸闷、心痛、恶心呕吐。刺灸法：直刺0.5-1寸。",
                "normalized_content": {
                    "acupoint_name": "内关",
                    "meridian": "手厥阴心包经",
                    "location": "腕横纹上2寸，掌长肌腱与桡侧腕屈肌腱之间",
                    "indication": "胸闷心痛、恶心呕吐、失眠",
                    "technique": "直刺0.5-1寸",
                    "caution": "避开明显静脉走行处",
                },
            },
            {
                "title": "曲池",
                "excerpt": "经络：手阳明大肠经。定位：屈肘成直角，当肘横纹外端。主治：发热、咽痛、上肢痹痛。刺灸法：直刺1-1.5寸。",
                "normalized_content": {
                    "acupoint_name": "曲池",
                    "meridian": "手阳明大肠经",
                    "location": "屈肘成直角，当肘横纹外端凹陷处",
                    "indication": "发热、咽痛、上肢痹痛、瘾疹",
                    "technique": "直刺1-1.5寸",
                    "caution": "局部红肿感染时不宜针刺",
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
        "description": "直接用于体验温病证候卡片与多难度小测。",
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
            {
                "title": "营分证",
                "excerpt": "阶段：营分。证候：身热夜甚，心烦不寐，舌绛。治法：清营透热。方药：清营汤。",
                "normalized_content": {
                    "pattern_name": "营分证",
                    "stage": "营分",
                    "syndrome": "身热夜甚，心烦不寐，时有谵语，舌绛",
                    "treatment": "清营透热",
                    "formula": "清营汤",
                    "differentiation": "热入营分，夜热较著，舌质偏绛",
                },
            },
            {
                "title": "血分证",
                "excerpt": "阶段：血分。证候：身热，斑疹，吐衄，舌深绛。治法：凉血散血。方药：犀角地黄汤。",
                "normalized_content": {
                    "pattern_name": "血分证",
                    "stage": "血分",
                    "syndrome": "身热，斑疹，吐衄，甚则神昏，舌深绛",
                    "treatment": "凉血散血",
                    "formula": "犀角地黄汤",
                    "differentiation": "热入血分，动血耗血表现更明显",
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
    """Seed or sync demo content if enabled."""
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

    created_collections = 0
    for collection_data in DEMO_COLLECTIONS:
        collection, created = _get_or_create_demo_collection(db, user.id, collection_data)
        if created:
            created_collections += 1

        _sync_demo_cards(db, collection, collection_data["cards"])
        _sync_demo_quizzes(db, collection, collection_data["quizzes"])
        _sync_demo_comparisons(db, collection, collection_data["comparisons"])

    db.commit()
    return created_collections


def _get_or_create_demo_collection(
    db: Session,
    user_id: int,
    collection_data: dict,
) -> tuple[StudyCollection, bool]:
    """Fetch a demo collection by title, clean duplicates, or create it."""
    matches = (
        db.query(StudyCollection)
        .filter(
            StudyCollection.user_id == user_id,
            StudyCollection.title == collection_data["title"],
        )
        .order_by(StudyCollection.id.asc())
        .all()
    )

    if len(matches) > 1:
        for duplicate in matches[1:]:
            db.delete(duplicate)
        db.flush()

    if matches:
        collection = matches[0]
        collection.subject = collection_data["subject"]
        collection.description = collection_data["description"]
        return collection, False

    collection = StudyCollection(
        user_id=user_id,
        title=collection_data["title"],
        subject=collection_data["subject"],
        description=collection_data["description"],
    )
    db.add(collection)
    db.flush()
    return collection, True


def _sync_demo_cards(db: Session, collection: StudyCollection, cards: list[dict]) -> None:
    """Create or update demo cards inside an existing demo collection."""
    for card_data in cards:
        matches = (
            db.query(KnowledgeCard)
            .filter(
                KnowledgeCard.collection_id == collection.id,
                KnowledgeCard.title == card_data["title"],
            )
            .order_by(KnowledgeCard.id.asc())
            .all()
        )
        if len(matches) > 1:
            for duplicate in matches[1:]:
                db.delete(duplicate)
            db.flush()

        if matches:
            card = matches[0]
            document = card.source_document
            if not document:
                document = SourceDocument(
                    collection_id=collection.id,
                    type="text",
                    status="processed",
                )
                db.add(document)
                db.flush()
                card.source_document_id = document.id
        else:
            document = SourceDocument(
                collection_id=collection.id,
                type="text",
                status="processed",
            )
            db.add(document)
            db.flush()

            card = KnowledgeCard(
                collection_id=collection.id,
                source_document_id=document.id,
                title=card_data["title"],
            )
            db.add(card)
            db.flush()

        document.raw_text = card_data["excerpt"]
        document.status = "processed"
        card.raw_excerpt = card_data["excerpt"]
        card.category = _subject_category(collection.subject)
        card.normalized_content_json = json.dumps(
            card_data["normalized_content"],
            ensure_ascii=False,
        )

        _upsert_subject_record(collection.subject, card, card_data["normalized_content"])


def _sync_demo_quizzes(db: Session, collection: StudyCollection, quizzes: list[dict]) -> None:
    """Create demo quizzes if they are missing from the collection."""
    for quiz_data in quizzes:
        existing = (
            db.query(Quiz)
            .filter(
                Quiz.collection_id == collection.id,
                Quiz.question == quiz_data["question"],
            )
            .first()
        )
        if existing:
            continue

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


def _sync_demo_comparisons(
    db: Session,
    collection: StudyCollection,
    comparisons: list[dict],
) -> None:
    """Create demo comparisons if they are missing from the collection."""
    for comparison_data in comparisons:
        existing = (
            db.query(ComparisonItem)
            .filter(
                ComparisonItem.collection_id == collection.id,
                ComparisonItem.left_entity == comparison_data["left_entity"],
                ComparisonItem.right_entity == comparison_data["right_entity"],
            )
            .first()
        )
        if existing:
            continue

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


def _subject_category(subject: str) -> str:
    """Map a collection subject label to the shared knowledge-card category."""
    if subject == "针灸学":
        return "acupuncture"
    if subject == "温病学":
        return "warm_disease"
    return "formula"


def _upsert_subject_record(subject: str, card: KnowledgeCard, payload: dict) -> None:
    """Create or update the subject-specific structured record for a demo card."""
    if subject == "方剂学":
        if not card.formula_card:
            card.formula_card = FormulaCard(knowledge_card_id=card.id)
        for field, value in payload.items():
            setattr(card.formula_card, field, value)
        return

    if subject == "针灸学":
        if not card.acupuncture_card:
            card.acupuncture_card = AcupunctureCard(knowledge_card_id=card.id)
        for field, value in payload.items():
            setattr(card.acupuncture_card, field, value)
        return

    if not card.warm_disease_card:
        card.warm_disease_card = WarmDiseaseCard(knowledge_card_id=card.id)
    for field, value in payload.items():
        setattr(card.warm_disease_card, field, value)
