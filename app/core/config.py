"""Process configuration from the environment.

Construction fails fast and names every invalid variable at once. Secrets
have no defaults. `get_settings` is the one module-level singleton.
"""

from datetime import date
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import PostgresDsn, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Env = Literal["development", "test", "production"]
LogLevel = Literal["debug", "info", "warning", "error"]
LogFormat = Literal["json", "console"]


class Settings(BaseSettings):
    """Validated process configuration, read from the environment and .env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ContractTracker"
    env: Env = "development"
    port: int = 8080
    log_level: LogLevel = "info"
    log_format: LogFormat = "json"
    database_url: PostgresDsn
    db_pool_size: int = 5
    db_pool_max_overflow: int = 10
    db_echo: bool = False
    # LLM through OpenRouter (ADR-0001, ADR-0002); no key means replay from the cache only.
    openrouter_api_key: SecretStr | None = None
    llm_model: str = "anthropic/claude-haiku-4.5"
    # USD 2 for the one-day build: stop at 1.80, counting spend since this date (ADR-0014, Q-033).
    llm_budget_stop_usd: Decimal = Decimal("1.80")
    llm_budget_since: date | None = date(2026, 10, 5)
    llm_cache_dir: Path = Path("llm_cache")

    @field_validator("openrouter_api_key", mode="before")
    @classmethod
    def _blank_key_is_no_key(cls, value: object) -> object:
        """`OPENROUTER_API_KEY=` left empty means replay only, never a call with a blank key."""
        return None if value == "" else value

    @field_validator("database_url")
    @classmethod
    def _async_driver(cls, value: PostgresDsn) -> PostgresDsn:
        """The whole stack is async; a sync driver here would block the loop."""
        if value.scheme != "postgresql+asyncpg":
            msg = f"DATABASE_URL must use postgresql+asyncpg://, got {value.scheme}://"
            raise ValueError(msg)
        return value


@lru_cache
def get_settings() -> Settings:
    """Load settings once per process."""
    return Settings()
