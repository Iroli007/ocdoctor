"""Database configuration tests."""
from sqlalchemy.pool import NullPool

from tcm_study_app.config import normalize_database_url
from tcm_study_app.db.session import create_db_engine


def test_normalize_neon_database_url():
    """Hosted Postgres URLs should use psycopg and require SSL."""
    url = normalize_database_url(
        "postgres://user:pass@ep-cool-darkness-123456.us-east-2.aws.neon.tech/neondb"
    )
    assert url.startswith("postgresql+psycopg://")
    assert "sslmode=require" in url


def test_normalize_local_postgres_url_without_forced_ssl():
    """Local Postgres URLs should keep psycopg without injecting SSL."""
    url = normalize_database_url("postgresql://user:pass@localhost:5432/ocdoctor")
    assert url == "postgresql+psycopg://user:pass@localhost:5432/ocdoctor"


def test_neon_engine_uses_null_pool():
    """Neon/pooler URLs should avoid long-lived local pooling on serverless runtimes."""
    engine = create_db_engine(
        "postgresql+psycopg://user:pass@ep-cool-darkness-123456-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require"
    )
    try:
        assert isinstance(engine.pool, NullPool)
    finally:
        engine.dispose()
