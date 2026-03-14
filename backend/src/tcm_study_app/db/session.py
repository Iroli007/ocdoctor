"""Database base and session management."""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from tcm_study_app.config import settings


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    echo=settings.debug,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initialize database tables."""
    from tcm_study_app.models import (
        User,
        StudyCollection,
        SourceDocument,
        KnowledgeCard,
        FormulaCard,
        ComparisonItem,
        Quiz,
        ReviewRecord,
    )
    Base.metadata.create_all(bind=engine)
