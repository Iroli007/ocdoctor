"""Seed demo content for the knowledge-library workflow."""
from sqlalchemy.orm import Session

from tcm_study_app.config import settings
from tcm_study_app.db import SessionLocal
from tcm_study_app.models import KnowledgeCard, SourceDocument, StudyCollection, User
from tcm_study_app.services.card_generator import CardGenerator
from tcm_study_app.services.document_library import DocumentLibrary

DEMO_USER_ID = 1
LEGACY_DEMO_TITLES = {
    "方剂学·速测样例",
    "针灸学·穴位样例",
    "温病学·辨证样例",
}

DEMO_COLLECTIONS = [
    {
        "title": "温病学·教材样例",
        "subject": "温病学",
        "description": "演示 PDF / 文档解析、证候辨治卡与原文引用。",
        "document_name": "温病学-卫气营血讲义.pdf",
        "template_key": "pattern_treatment",
        "text": """
卫分证
阶段：卫分
证候：发热，微恶风寒，咽痛，口微渴
治法：辛凉解表
方药：银翘散
辨证要点：病位较浅，以表热为主

气分热盛证
阶段：气分
证候：壮热，大汗，大渴，脉洪大
治法：清气泄热
方药：白虎汤
辨证要点：里热炽盛，津液已伤

营分证
阶段：营分
证候：身热夜甚，心烦不寐，时有谵语，舌绛
治法：清营透热
方药：清营汤
辨证要点：热入营分，夜热更著
""".strip(),
    },
    {
        "title": "针灸学·教材样例",
        "subject": "针灸学",
        "description": "演示穴位基础卡、引用页码与导出。",
        "document_name": "针灸学-常用穴讲义.pdf",
        "template_key": "acupoint_foundation",
        "text": """
合谷穴
经络：手阳明大肠经
定位：手背第一、二掌骨间，当第二掌骨桡侧中点处
主治：头痛、牙痛、面口病证
刺灸法：直刺0.5-1寸
注意：孕妇慎用强刺激

足三里
经络：足阳明胃经
定位：犊鼻下3寸，距胫骨前缘一横指
主治：胃痛、呕吐、腹胀、虚劳诸证
刺灸法：直刺1-2寸
注意：局部皮肤破损时避开操作

内关
经络：手厥阴心包经
定位：腕横纹上2寸，掌长肌腱与桡侧腕屈肌腱之间
主治：胸闷心痛、恶心呕吐、失眠
刺灸法：直刺0.5-1寸
注意：避开明显静脉走行处
""".strip(),
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
    library = DocumentLibrary(db)
    generator = CardGenerator(db)
    _remove_legacy_demo_collections(db, user.id)

    for collection_data in DEMO_COLLECTIONS:
        collection, created = _get_or_create_demo_collection(db, user.id, collection_data)
        if created:
            created_collections += 1

        _reset_collection_content(db, collection.id)
        document = library.import_text_document(collection.id, collection_data["text"])
        document.type = "pdf"
        document.image_url = collection_data["document_name"]
        generator.generate_cards_from_document(document.id, collection_data["template_key"])

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


def _reset_collection_content(db: Session, collection_id: int) -> None:
    """Remove old demo documents/cards before rebuilding the collection."""
    cards = db.query(KnowledgeCard).filter(KnowledgeCard.collection_id == collection_id).all()
    for card in cards:
        db.delete(card)

    documents = (
        db.query(SourceDocument)
        .filter(SourceDocument.collection_id == collection_id)
        .all()
    )
    for document in documents:
        db.delete(document)
    db.flush()


def _remove_legacy_demo_collections(db: Session, user_id: int) -> None:
    """Remove obsolete demo collections from earlier product iterations."""
    current_titles = {item["title"] for item in DEMO_COLLECTIONS}
    legacy_titles = LEGACY_DEMO_TITLES - current_titles
    matches = (
        db.query(StudyCollection)
        .filter(
            StudyCollection.user_id == user_id,
            StudyCollection.title.in_(legacy_titles),
        )
        .all()
    )
    for collection in matches:
        db.delete(collection)
    db.flush()
