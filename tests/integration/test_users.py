"""The users table on Postgres: duplicates, atomic lockout, constraints (ADR-0017, TC-0203)."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.errors import ConflictError
from app.db.repositories import users as repo
from tests.integration.conftest import rolled_back_session

pytestmark = pytest.mark.integration

NOW = datetime(2026, 10, 12, 9, 0, tzinfo=UTC)
HASH = "scrypt$16384$8$1$AAAA$AAAA"


# TC-0203
async def test_tc0203_a_second_user_with_the_same_email_is_a_conflict(engine: AsyncEngine) -> None:
    async with rolled_back_session(engine) as session:
        await repo.create(session, "owner@example.com", HASH)

        with pytest.raises(ConflictError):
            await repo.create(session, "owner@example.com", HASH)


async def test_tc0203_the_database_refuses_an_email_that_is_not_lower_case(
    engine: AsyncEngine,
) -> None:
    async with rolled_back_session(engine) as session:
        with pytest.raises(ConflictError):
            await repo.create(session, "Owner@Example.com", HASH)


async def test_tc0203_failures_count_then_lock_then_a_correct_login_clears_them(
    engine: AsyncEngine,
) -> None:
    async with rolled_back_session(engine) as session:
        user_id = await repo.create(session, "owner@example.com", HASH)
        lock = timedelta(minutes=15)

        await repo.record_failure(session, user_id, NOW, 3, lock)
        await repo.record_failure(session, user_id, NOW, 3, lock)
        before = await repo.by_id(session, user_id)
        await repo.record_failure(session, user_id, NOW, 3, lock)
        locked = await repo.by_id(session, user_id)
        await repo.clear_failures(session, user_id)
        cleared = await repo.by_id(session, user_id)

    assert before is not None
    assert (before.failed_attempts, before.locked_until) == (2, None)
    assert locked is not None
    assert (locked.failed_attempts, locked.locked_until) == (0, NOW + lock)
    assert cleared is not None
    assert (cleared.failed_attempts, cleared.locked_until) == (0, None)


async def test_tc0203_set_password_unlocks_and_disable_marks_the_account(
    engine: AsyncEngine,
) -> None:
    async with rolled_back_session(engine) as session:
        user_id = await repo.create(session, "owner@example.com", HASH)
        await repo.record_failure(session, user_id, NOW, 1, timedelta(minutes=5))

        changed = await repo.set_password(
            session, "owner@example.com", "scrypt$16384$8$1$BBBB$BBBB"
        )
        missing = await repo.set_password(session, "nobody@example.com", HASH)
        disabled = await repo.disable(session, "owner@example.com", NOW)
        user = await repo.by_email(session, "owner@example.com")

    assert changed is True
    assert missing is False
    assert disabled is True
    assert user is not None
    assert user.locked_until is None
    assert user.disabled_at == NOW
    assert user.password_hash.endswith("BBBB")
