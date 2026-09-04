"""Central, typed application settings.

Every module imports settings from here; nothing reads os.environ directly.
Secrets come from the repo-root .env file and are never hard-coded.
"""
from __future__ import annotations

import secrets
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[2]

DataMode = Literal["live", "demo", "auto"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env", BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---- runtime ----
    airs_env: str = "development"
    airs_log_level: str = "INFO"
    airs_data_mode: DataMode = "live"

    # ---- database ----
    database_url: str = f"sqlite+pysqlite:///{REPO_ROOT / 'data' / 'airs.sqlite3'}"

    # ---- security ----
    airs_secret_key: str = Field(default_factory=lambda: secrets.token_urlsafe(48))
    airs_access_token_minutes: int = 120
    airs_cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # ---- providers ----
    waqi_token: str | None = None
    openweather_api_key: str | None = None
    tomtom_api_key: str | None = None

    # ---- ai ----
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.0-flash"

    # ---- legacy single-city defaults (kept from the original repo) ----
    default_city: str = "delhi"
    default_lat: float = 28.6139
    default_lon: float = 77.2090

    @field_validator("airs_data_mode", mode="before")
    @classmethod
    def _lower(cls, v):
        return str(v).lower().strip() if v is not None else v

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.airs_cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.airs_env.lower() in {"production", "prod"}

    @property
    def has_air_quality_provider(self) -> bool:
        return bool(self.waqi_token)

    @property
    def has_weather_provider(self) -> bool:
        return bool(self.openweather_api_key)

    @property
    def has_ai(self) -> bool:
        return bool(self.gemini_api_key)

    def capability_report(self) -> dict[str, bool | str]:
        """Surfaced by /api/v1/system/status so the UI can be honest about
        what is actually available at runtime."""
        return {
            "data_mode": self.airs_data_mode,
            "air_quality_provider": self.has_air_quality_provider,
            "weather_provider": self.has_weather_provider,
            "traffic_provider": bool(self.tomtom_api_key),
            "ai_copilot": self.has_ai,
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
