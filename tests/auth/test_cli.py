"""The `make user` command: what it refuses and what it stores (ADR-0017, TC-0202)."""

import uuid
from collections.abc import Callable, Iterator
from typing import cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth.cli import run
from app.auth.passwords import verify_password
from app.core.errors import ConflictError
from app.db.repositories import users as user_repo
from tests.auth.test_service import FakeSession

FACTORY = cast("async_sessionmaker[AsyncSession]", lambda: FakeSession())
GOOD = "a-good-passphrase-1"


def typed(*answers: str) -> Callable[[str], str]:
    queue: Iterator[str] = iter(answers)
    return lambda _prompt: next(queue)


@pytest.fixture
def created(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    saved: dict[str, str] = {}

    async def create(_: object, email: str, password_hash: str) -> uuid.UUID:
        if email in saved:
            msg = "exists"
            raise ConflictError(msg)
        saved[email] = password_hash
        return uuid.uuid4()

    monkeypatch.setattr(user_repo, "create", create)
    return saved


# TC-0202
async def test_tc0202_create_stores_a_hash_never_the_password(created: dict[str, str]) -> None:
    line = await run("create", " Owner@Example.com ", FACTORY, typed(GOOD, GOOD))

    assert line == "Created owner@example.com."
    assert verify_password(GOOD, created["owner@example.com"])
    assert GOOD not in created["owner@example.com"]


@pytest.mark.parametrize(
    ("answers", "reason"),
    [
        (("short", "short"), "at least 10"),
        ((GOOD, "a-different-passphrase"), "not the same"),
        (("owner-secret-1234", "owner-secret-1234"), "email"),
    ],
)
async def test_tc0202_a_weak_or_mismatched_password_is_refused(
    created: dict[str, str], answers: tuple[str, str], reason: str
) -> None:
    with pytest.raises(ValueError, match=reason):
        await run("create", "owner@example.com", FACTORY, typed(*answers))

    assert created == {}


async def test_tc0202_a_second_user_with_the_same_email_is_a_conflict(
    created: dict[str, str],
) -> None:
    await run("create", "owner@example.com", FACTORY, typed(GOOD, GOOD))

    with pytest.raises(ConflictError):
        await run("create", "owner@example.com", FACTORY, typed(GOOD, GOOD))
