"""Application configuration.

Settings come from the environment only. Nothing here carries a real
credential default, and the application refuses to start in a non-local
environment without an explicit DATABASE_URL
(docs/09_AWS_DEPLOYMENT.md section 7).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

AppEnv = Literal["local", "preview", "staging", "production-beta"]

LOCAL_DATABASE_URL = "postgresql+asyncpg://insurance:insurance@localhost:5432/insurance_local"


class Settings(BaseSettings):
    """Runtime settings for the API and worker."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: AppEnv = "local"
    log_level: str = "INFO"

    database_url: str = LOCAL_DATABASE_URL

    api_host: str = "0.0.0.0"  # noqa: S104 — containers bind all interfaces
    api_port: int = 8000

    cors_allowed_origins: str = "http://localhost:3000"

    #: Requests slower than this are logged at WARNING so latency stays visible.
    slow_request_threshold_ms: int = Field(default=1000, ge=1)

    @field_validator("log_level")
    @classmethod
    def _normalize_log_level(cls, value: str) -> str:
        normalized = value.upper()
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if normalized not in allowed:
            raise ValueError(f"log_level must be one of {sorted(allowed)}")
        return normalized

    @property
    def is_local(self) -> bool:
        return self.app_env == "local"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]

    def validate_for_environment(self) -> None:
        """Fail loudly rather than silently running a deployed env on local defaults."""
        if not self.is_local and self.database_url == LOCAL_DATABASE_URL:
            raise RuntimeError(
                f"DATABASE_URL must be set explicitly when APP_ENV={self.app_env}; "
                "the local development default is not usable outside APP_ENV=local."
            )


@lru_cache
def get_settings() -> Settings:
    """Return process-wide settings (cached)."""
    settings = Settings()
    settings.validate_for_environment()
    return settings
