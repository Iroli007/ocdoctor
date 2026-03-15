"""Tests for the refactored quiz generator."""
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from tcm_study_app.db.session import Base
from tcm_study_app.models import StudyCollection
from tcm_study_app.services.demo_seed import seed_demo_content
from tcm_study_app.services.quiz_generator import QuizGenerator


def test_formula_quizzes_are_unique_within_one_generation():
    """Generating multiple quizzes should produce distinct question texts."""
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
        collection = (
            db.query(StudyCollection)
            .filter(StudyCollection.title == "方剂学·速测样例")
            .first()
        )
        generator = QuizGenerator(db)
        quizzes = generator.generate_quizzes(collection.id, count=4, difficulty="easy")

        questions = [quiz.question for quiz in quizzes]
        assert len(questions) == 4
        assert len(set(questions)) == 4
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_formula_quizzes_avoid_reusing_existing_questions():
    """A second generation run should skip already-saved questions and produce new ones."""
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
        collection = (
            db.query(StudyCollection)
            .filter(StudyCollection.title == "方剂学·速测样例")
            .first()
        )
        generator = QuizGenerator(db)
        first_batch = generator.generate_quizzes(collection.id, count=2, difficulty="medium")
        second_batch = generator.generate_quizzes(collection.id, count=2, difficulty="medium")

        first_questions = {quiz.question for quiz in first_batch}
        second_questions = {quiz.question for quiz in second_batch}
        assert first_questions.isdisjoint(second_questions)
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_warm_disease_hard_quiz_uses_subject_specific_content():
    """Warm-disease hard quizzes should be based on syndrome/treatment patterns."""
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
        collection = (
            db.query(StudyCollection)
            .filter(StudyCollection.title == "温病学·辨证样例")
            .first()
        )
        generator = QuizGenerator(db)
        quizzes = generator.generate_quizzes(collection.id, count=2, difficulty="hard")

        assert quizzes
        assert all("证候" in quiz.question or "阶段" in quiz.question for quiz in quizzes)
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
