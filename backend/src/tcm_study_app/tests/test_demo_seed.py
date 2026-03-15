"""Tests for default demo data seeding."""
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from tcm_study_app.db.session import Base
from tcm_study_app.models import CardCitation, DocumentChunk, KnowledgeCard, StudyCollection, User
from tcm_study_app.services.demo_seed import seed_demo_content


def test_seed_demo_content_populates_empty_database():
    """Seeding should create ready-to-use collections, documents, chunks, and cards."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
        class_=Session,
    )
    Base.metadata.create_all(bind=engine)

    db = testing_session_local()
    try:
        seeded_count = seed_demo_content(db)
        assert seeded_count == 2
        assert db.query(StudyCollection).count() == 2
        assert db.query(KnowledgeCard).count() >= 4
        assert db.query(DocumentChunk).count() >= 4
        assert db.query(CardCitation).count() >= 4

        seeded_again = seed_demo_content(db)
        assert seeded_again == 0
        assert db.query(StudyCollection).count() == 2
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_seed_demo_content_preserves_existing_user_data():
    """User-created collections should not block demo content from being added."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
        class_=Session,
    )
    Base.metadata.create_all(bind=engine)

    db = testing_session_local()
    try:
        user = User(id=1, email="demo@example.com", name="Demo User")
        db.add(user)
        db.flush()
        db.add(
            StudyCollection(
                user_id=user.id,
                title="我自己的集合",
                subject="温病学",
                description="用户手动创建的数据",
            )
        )
        db.commit()

        seeded_count = seed_demo_content(db)
        assert seeded_count == 2
        titles = {item.title for item in db.query(StudyCollection).all()}
        assert "我自己的集合" in titles
        assert "温病学·教材样例" in titles
        assert "针灸学·教材样例" in titles
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
