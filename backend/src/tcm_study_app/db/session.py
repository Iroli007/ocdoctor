"""Database base and session management."""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from tcm_study_app.config import settings

_is_sqlite = settings.database_url.startswith("sqlite")


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    pool_pre_ping=not _is_sqlite,
    pool_recycle=300 if not _is_sqlite else -1,
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
        AcupunctureCard,
        WarmDiseaseCard,
        ComparisonItem,
        Quiz,
        ReviewRecord,
    )
    Base.metadata.create_all(bind=engine)
