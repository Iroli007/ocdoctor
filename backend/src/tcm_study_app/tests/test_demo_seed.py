"""Tests for default demo data seeding."""
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from tcm_study_app.db.session import Base
from tcm_study_app.models import KnowledgeCard, Quiz, StudyCollection, User
from tcm_study_app.services.demo_seed import seed_demo_content


def test_seed_demo_content_populates_empty_database():
    """Seeding should create ready-to-use collections, cards, and quizzes."""
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
        assert seeded_count == 3
        assert db.query(StudyCollection).count() == 3
        assert db.query(KnowledgeCard).count() == 12
        assert db.query(Quiz).count() == 3

        seeded_again = seed_demo_content(db)
        assert seeded_again == 0
        assert db.query(StudyCollection).count() == 3
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_seed_demo_content_updates_existing_demo_collection_cards():
    """Existing demo collections should receive newly added example cards."""
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
                title="方剂学·速测样例",
                subject="方剂学",
                description="旧版演示集合",
            )
        )
        db.commit()

        seeded_count = seed_demo_content(db)
        assert seeded_count == 2
        formula_collection = (
            db.query(StudyCollection)
            .filter(StudyCollection.title == "方剂学·速测样例")
            .first()
        )
        assert formula_collection is not None
        assert (
            db.query(KnowledgeCard)
            .filter(KnowledgeCard.collection_id == formula_collection.id)
            .count()
            == 4
        )
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
                subject="方剂学",
                description="用户手动创建的数据",
            )
        )
        db.commit()

        seeded_count = seed_demo_content(db)
        assert seeded_count == 3
        titles = {item.title for item in db.query(StudyCollection).all()}
        assert "我自己的集合" in titles
        assert "方剂学·速测样例" in titles
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_seed_demo_content_cleans_up_duplicate_demo_collections():
    """Repeated startup seeds should collapse duplicate demo collections back to one copy."""
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
        seed_demo_content(db)
        duplicate = StudyCollection(
            user_id=1,
            title="方剂学·速测样例",
            subject="方剂学",
            description="重复的演示集合",
        )
        db.add(duplicate)
        db.commit()

        seeded_count = seed_demo_content(db)
        assert seeded_count == 0
        matching = (
            db.query(StudyCollection)
            .filter(StudyCollection.title == "方剂学·速测样例")
            .all()
        )
        assert len(matching) == 1
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
