"""Database base and session management."""
from sqlalchemy import create_engine, inspect, text
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
    _apply_lightweight_migrations()


def _apply_lightweight_migrations() -> None:
    """Add critical columns for legacy databases without requiring Alembic.

    Existing hosted databases may have been created before recent schema
    changes. `create_all()` does not alter existing tables, so we backfill the
    small set of required columns that the app now depends on at startup.
    """
    inspector = inspect(engine)
    migrations = {
        "source_documents": {
            "source_book_key": "VARCHAR(50)",
            "book_section": "VARCHAR(40)",
            "section_confidence": "VARCHAR(20)",
            "parser_version": "VARCHAR(40)",
            "ocr_engine": "VARCHAR(50)",
            "has_layout_blocks": "BOOLEAN NOT NULL DEFAULT FALSE",
        },
        "card_citations": {
            "parsed_document_unit_id": "INTEGER",
        },
    }

    with engine.begin() as connection:
        for table_name, columns in migrations.items():
            if not inspector.has_table(table_name):
                continue
            existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
            for column_name, ddl in columns.items():
                if column_name in existing_columns:
                    continue
                connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl}"))
