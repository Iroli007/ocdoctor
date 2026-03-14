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

    # API Keys - 支持系统环境变量或 .env 文件
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    anthropic_auth_token: str | None = None  # 系统代理使用
    anthropic_base_url: str = "https://api.anthropic.com"


settings = Settings()
