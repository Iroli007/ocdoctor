"""Database base and session management."""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import NullPool

from tcm_study_app.config import settings


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


def _is_sqlite_url(database_url: str) -> bool:
    """Return whether the configured database is SQLite."""
    return database_url.startswith("sqlite")


def create_db_engine(database_url: str, debug: bool = False):
    """Create a SQLAlchemy engine suited for the current database/backend."""
    is_sqlite = _is_sqlite_url(database_url)
    engine_kwargs = {
        "echo": debug,
    }

    if is_sqlite:
        engine_kwargs["connect_args"] = {"check_same_thread": False}
    else:
        engine_kwargs["pool_pre_ping"] = True
        engine_kwargs["pool_recycle"] = 300
        if database_url.startswith("postgresql+psycopg://") and (
            "pooler." in database_url or "neon.tech" in database_url
        ):
            # Serverless Postgres providers behave better without a long-lived local pool.
            engine_kwargs["poolclass"] = NullPool

    return create_engine(database_url, **engine_kwargs)


engine = create_db_engine(settings.database_url, debug=settings.debug)

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
    import tcm_study_app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
