"""Environment-based configuration for the Intelligence Engine.

`get_settings` is the single entry point for reading configuration. It is
cached so the environment is parsed once per process, and a fresh
`Settings()` can always be built directly in tests to exercise specific
environment combinations.

Token rules (IE-002):
 - production: `INTERNAL_API_TOKEN` must be non-empty, otherwise construction
   fails with `ConfigError` (no insecure fallback in production) — this stops
   the service from booting with a broken security posture.
 - development/test: an empty token is allowed (no insecure bypass flag is
   offered), but `app.core.security.require_internal_token` rejects every
   request when no token is configured, since there is nothing valid to
   compare against. This keeps "no token configured" and "open access" from
   ever being the same state.
"""

from functools import lru_cache
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.constants import SERVICE_NAME, SERVICE_VERSION
from app.core.errors import ConfigError

AppEnv = Literal["development", "production", "test"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: AppEnv = "development"
    service_name: str = SERVICE_NAME
    service_version: str = SERVICE_VERSION
    log_level: str = "INFO"
    internal_api_token: str = ""

    @field_validator("internal_api_token", mode="before")
    @classmethod
    def _strip_token(cls, value: str | None) -> str:
        return (value or "").strip()

    @model_validator(mode="after")
    def _require_token_in_production(self) -> "Settings":
        if self.app_env == "production" and self.internal_api_token == "":
            raise ConfigError(
                "INTERNAL_API_TOKEN is required and must not be empty in production.",
                details={"variable": "INTERNAL_API_TOKEN"},
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
