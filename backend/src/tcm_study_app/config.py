"""Application configuration."""
import os

from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_database_url() -> str:
    """Provide a Vercel-safe SQLite default."""
    if os.getenv("VERCEL"):
        return "sqlite:////tmp/tcm_study.db"
    return "sqlite:///./tcm_study.db"


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

    # API Keys - 支持系统环境变量或 .env 文件
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    anthropic_auth_token: str | None = None  # 系统代理使用
    anthropic_base_url: str = "https://api.anthropic.com"


settings = Settings()
