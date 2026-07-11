"""Application settings, loaded from environment variables (and a local .env file).

All secrets live in the environment — never in code. See .env.example for
documentation of every variable.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["development", "test", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # Required — the app refuses to start without a database URL.
    database_url: str

    # Keepa API key. Optional so the app boots without it; the Keepa
    # collection command fails loudly if it is missing. NEVER hard-code a
    # key — it lives only in this environment variable.
    keepa_api_key: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
