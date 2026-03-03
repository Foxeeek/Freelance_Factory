from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str = Field(default="", alias="TELEGRAM_CHAT_ID")
    enabled_platforms: List[str] = Field(default_factory=lambda: ["freelancehunt"], alias="ENABLED_PLATFORMS")
    poll_interval_minutes: int = Field(default=10, alias="POLL_INTERVAL_MINUTES")
    hourly_rate_eur: int = Field(default=15, alias="HOURLY_RATE_EUR")
    default_language: str = Field(default="en", alias="DEFAULT_LANGUAGE")
    database_url: str = Field(default="sqlite:///./freelance_ai.db", alias="DATABASE_URL")

    @field_validator("enabled_platforms", mode="before")
    @classmethod
    def split_platforms(cls, value: object) -> List[str]:
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return ["freelancehunt"]

    @field_validator("default_language")
    @classmethod
    def validate_language(cls, value: str) -> str:
        allowed = {"en", "ua"}
        lang = value.lower().strip()
        if lang not in allowed:
            return "en"
        return lang


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
