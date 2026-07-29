"""Application settings, sourced from environment variables.

Never hardcode secrets here. `api_key` has no default on purpose: the
app refuses to boot without NUIT_BLANCHE_API_KEY set, so an empty key
can never accidentally be "valid" in production.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="NUIT_BLANCHE_", env_file=".env", extra="ignore")

    api_key: str = Field(..., description="Shared secret expected in the X-API-Key header")
    max_payload_bytes: int = Field(default=2_000_000, description="Max size of an incoming JSON body")
    generation_timeout_seconds: int = Field(default=60, description="Hard timeout for one carousel generation")
    generated_dir: Path = Field(default=Path("generated"), description="Root directory for local storage output")
    slide_width: int = Field(default=1080)
    slide_height: int = Field(default=1350)
    chromium_executable_path: str | None = Field(
        default=None,
        description="Override path to a system Chromium binary. Leave unset to use Playwright's bundled browser.",
    )
    log_level: str = Field(default="INFO")
    app_version: str = Field(default="0.1.0")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
