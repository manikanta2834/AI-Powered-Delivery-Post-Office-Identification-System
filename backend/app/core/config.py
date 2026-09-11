from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    app_name: str = "AI Postal Intelligence API"
    environment: str = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    allowed_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    database_url: str = (
        "postgresql+asyncpg://postal:postal@localhost:5432/postal_intelligence"
    )
    redis_url: str = "redis://localhost:6379/0"
    auto_create_schema: bool = False
    jwt_secret: str = "change-this-development-secret"
    access_token_minutes: int = 30
    refresh_token_days: int = 14

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
