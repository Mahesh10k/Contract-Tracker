"""Login rules without a database: the repository is replaced by an in-memory one (ADR-0017)."""

import uuid
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from types import TracebackType
from typing import Self, cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth.passwords import hash_password
from app.auth.service import AuthService
from app.auth.tokens import read_token
from app.core.config import Settings
from app.core.errors import InvalidCredentialsError
from app.db.repositories import users as user_repo
from app.db.repositories.users import UserRecord

NOW = datetime(2026, 10, 12, 9, 0, tzinfo=UTC)
SECRET = "k" * 40
RIGHT_ONE = "right-password-1"


class Context:
    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        kind: type[BaseException] | None,
        error: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None


class FakeSession(Context):
    def begin(self) -> Context:
        return Context()


class Clock:
    def __init__(self) -> None:
        self.now = NOW

    def __call__(self) -> datetime:
        return self.now


class Store:
    """The users table, in memory, with the same behaviour as the SQL."""

    def __init__(self) -> None:
        self.rows: dict[uuid.UUID, UserRecord] = {}

    def add(
        self,
        email: str,
        failed_attempts: int = 0,
        locked_until: datetime | None = None,
        disabled_at: datetime | None = None,
    ) -> UserRecord:
        user = UserRecord(
            uuid.uuid4(),
            email,
            hash_password(RIGHT_ONE),
            failed_attempts,
            locked_until,
            disabled_at,
        )
        self.rows[user.id] = user
        return user

    async def by_email(self, _: object, email: str) -> UserRecord | None:
        return next((u for u in self.rows.values() if u.email == email), None)

    async def by_id(self, _: object, user_id: uuid.UUID) -> UserRecord | None:
        return self.rows.get(user_id)

    async def clear_failures(self, _: object, user_id: uuid.UUID) -> None:
        self.rows[user_id] = replace(self.rows[user_id], failed_attempts=0, locked_until=None)

    async def record_failure(
        self, _: object, user_id: uuid.UUID, now: datetime, limit: int, lock_for: timedelta
    ) -> None:
        user = self.rows[user_id]
        hit = user.failed_attempts + 1 >= limit
        self.rows[user_id] = replace(
            user,
            failed_attempts=0 if hit else user.failed_attempts + 1,
            locked_until=now + lock_for if hit else user.locked_until,
        )


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def store(monkeypatch: pytest.MonkeyPatch) -> Store:
    fake = Store()
    for name in ("by_email", "by_id", "clear_failures", "record_failure"):
        monkeypatch.setattr(user_repo, name, getattr(fake, name))
    return fake


@pytest.fixture
def auth(store: Store, clock: Clock) -> AuthService:
    settings = Settings.model_validate(
        {
            "database_url": "postgresql+asyncpg://u:p@h/db",
            "session_secret": SECRET,
            "login_max_attempts": 3,
            "login_lock_minutes": 15,
        }
    )
    factory = cast("async_sessionmaker[AsyncSession]", lambda: FakeSession())
    return AuthService(settings, factory, clock)


# TC-0194
async def test_tc0194_a_correct_login_returns_the_user_a_token_and_clears_old_failures(
    auth: AuthService, store: Store, clock: Clock
) -> None:
    user = store.add("owner@example.com", failed_attempts=2)

    found, token = await auth.login("owner@example.com", RIGHT_ONE)

    assert found.id == user.id
    assert read_token(token, SECRET, clock.now) == user.id
    assert store.rows[user.id].failed_attempts == 0
    assert (await auth.user_for_token(token)) is not None


# TC-0195
async def test_tc0195_every_refusal_looks_the_same(
    auth: AuthService, store: Store, clock: Clock
) -> None:
    store.add("owner@example.com")
    store.add("locked@example.com", locked_until=clock.now + timedelta(minutes=5))
    store.add("gone@example.com", disabled_at=clock.now - timedelta(days=1))
    attempts = [
        ("owner@example.com", "wrong-password"),
        ("nobody@example.com", RIGHT_ONE),
        ("locked@example.com", RIGHT_ONE),
        ("gone@example.com", RIGHT_ONE),
    ]

    messages = set()
    for email, password in attempts:
        with pytest.raises(InvalidCredentialsError) as caught:
            await auth.login(email, password)
        messages.add(caught.value.message)

    assert len(messages) == 1


# TC-0196
async def test_tc0196_the_account_locks_after_the_allowed_failures_and_unlocks_later(
    auth: AuthService, store: Store, clock: Clock
) -> None:
    user = store.add("owner@example.com")

    for _ in range(3):
        with pytest.raises(InvalidCredentialsError):
            await auth.login("owner@example.com", "wrong-password")
    with pytest.raises(InvalidCredentialsError):
        await auth.login("owner@example.com", RIGHT_ONE)
    assert store.rows[user.id].locked_until == clock.now + timedelta(minutes=15)

    clock.now += timedelta(minutes=16)
    found, _ = await auth.login("owner@example.com", RIGHT_ONE)
    assert found.id == user.id


async def test_a_session_for_a_disabled_or_unknown_user_is_no_session(
    auth: AuthService, store: Store, clock: Clock
) -> None:
    user = store.add("owner@example.com")
    _, token = await auth.login("owner@example.com", RIGHT_ONE)

    store.rows[user.id] = replace(user, disabled_at=clock.now)

    assert await auth.user_for_token(token) is None
    assert await auth.user_for_token("garbage") is None
