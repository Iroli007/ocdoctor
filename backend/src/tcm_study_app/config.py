"""Application configuration."""
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    database_url: str = "sqlite:///./tcm_study.db"

    # API Keys (optional for MVP)
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None


settings = Settings()
