"""Settings fail fast and name the problem."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings

DB = "postgresql+asyncpg://postgres:postgres@localhost:5432/test"


def test_defaults() -> None:
    settings = Settings(_env_file=None, database_url=DB)

    assert settings.env == "development"
    assert settings.port == 8080
    assert settings.log_level == "info"
    assert settings.log_format == "json"


def test_environment_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "debug")
    monkeypatch.setenv("PORT", "9000")

    settings = Settings(_env_file=None, database_url=DB)

    assert settings.log_level == "debug"
    assert settings.port == 9000


@pytest.mark.parametrize(
    ("variable", "value"),
    [
        ("LOG_LEVEL", "loud"),
        ("ENV", "staging"),
        ("PORT", "eighty"),
    ],
)
def test_invalid_values_are_rejected(
    monkeypatch: pytest.MonkeyPatch, variable: str, value: str
) -> None:
    monkeypatch.setenv(variable, value)

    with pytest.raises(ValidationError, match=variable.lower()):
        Settings(_env_file=None, database_url=DB)


def test_an_empty_openrouter_key_counts_as_no_key(monkeypatch: pytest.MonkeyPatch) -> None:
    # TASK-002: .env.example ships OPENROUTER_API_KEY= empty; that must not start a live call.
    monkeypatch.setenv("OPENROUTER_API_KEY", "")

    settings = Settings(_env_file=None, database_url=DB)

    assert settings.openrouter_api_key is None


def test_sync_driver_is_rejected() -> None:
    with pytest.raises(ValidationError, match="postgresql\\+asyncpg"):
        Settings(_env_file=None, database_url="postgresql://postgres:postgres@localhost/test")


# TC-0201
def test_tc0201_production_refuses_to_start_without_a_strong_session_secret() -> None:
    base = {"env": "production", "database_url": "postgresql+asyncpg://u:p@h/db"}

    with pytest.raises(ValidationError, match="SESSION_SECRET"):
        Settings.model_validate(base)
    with pytest.raises(ValidationError, match="SESSION_SECRET"):
        Settings.model_validate({**base, "session_secret": "short"})
    assert Settings.model_validate({**base, "session_secret": "s" * 32}).session_secret


def test_tc0201_development_needs_no_secret_and_a_blank_one_means_none() -> None:
    settings = Settings.model_validate(
        {"database_url": "postgresql+asyncpg://u:p@h/db", "session_secret": ""}
    )

    assert settings.session_secret is None
