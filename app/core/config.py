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

# Below this top-1 cosine similarity a question is refused with no LLM call (ADR-0013). Set by the
# spike over the golden questions on 2026-10-06 (evals/qa/floor-spike.md, Q-017): answerable
# questions scored 0.763 to 0.868, unanswerable ones 0.598 to 0.635; 0.70 sits in the gap.
QA_SIMILARITY_FLOOR = 0.70

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
    # Embeddings run locally on CPU (ADR-0004); `make setup` fetches the model into this folder.
    embedding_model_dir: Path = Path("models")
    qa_similarity_floor: float = QA_SIMILARITY_FLOOR
    # Reminder email goes to MailHog only (ADR-0010); one recipient, no login (Q-002).
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    reminder_to: str = "owner@contracttracker.test"
    reminder_from: str = "reminders@contracttracker.test"
    # Treat this date as today for reminders and `make remind` (REQ-042); empty means the real date.
    pretend_today: date | None = None

    @field_validator("pretend_today", mode="before")
    @classmethod
    def _blank_pretend_is_none(cls, value: object) -> object:
        """`PRETEND_TODAY=` left empty means the real date."""
        return None if value == "" else value

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
