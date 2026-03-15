"""Application configuration."""
import os
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_database_url() -> str:
    """Provide a local-development-safe database default."""
    return "sqlite:///./tcm_study.db"


def _default_seed_demo_content() -> bool:
    """Seed demo content automatically on hosted environments by default."""
    env_value = os.getenv("SEED_DEMO_CONTENT")
    if env_value is not None:
        return env_value.lower() in {"1", "true", "yes", "on"}

    return bool(os.getenv("VERCEL"))


def normalize_database_url(database_url: str) -> str:
    """Normalize database URLs for SQLAlchemy and hosted Postgres providers."""
    url = database_url.strip()
    if not url:
        return _default_database_url()

    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)

    parsed = urlparse(url)
    if not parsed.scheme.startswith("postgresql+psycopg"):
        return url

    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    hostname = parsed.hostname or ""
    is_remote = hostname not in {"", "localhost", "127.0.0.1"}
    if is_remote:
        query.setdefault("sslmode", "require")

    return urlunparse(parsed._replace(query=urlencode(query)))


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # App
    app_name: str = "TCM Study App"
    debug: bool = True

    # Database
    database_url: str = _default_database_url()
    seed_demo_content: bool = _default_seed_demo_content()

    # API Keys - 支持系统环境变量或 .env 文件
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    anthropic_auth_token: str | None = None  # 系统代理使用
    anthropic_base_url: str = "https://api.anthropic.com"


settings = Settings()
settings.database_url = normalize_database_url(settings.database_url)
