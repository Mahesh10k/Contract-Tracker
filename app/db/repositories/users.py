"""Users for the login (ADR-0017). Callers own the transaction."""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import case, func, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError
from app.db.tables import users


@dataclass(frozen=True)
class UserRecord:
    """One account as the login needs it."""

    id: uuid.UUID
    email: str
    password_hash: str
    failed_attempts: int
    locked_until: datetime | None
    disabled_at: datetime | None


_COLUMNS = (
    users.c.id,
    users.c.email,
    users.c.password_hash,
    users.c.failed_attempts,
    users.c.locked_until,
    users.c.disabled_at,
)


def _record(row: object) -> UserRecord:
    return UserRecord(*row)  # type: ignore[misc]  # a Row of exactly the columns above


async def by_email(session: AsyncSession, email: str) -> UserRecord | None:
    """The account with this (already lower-cased) email."""
    row = (await session.execute(select(*_COLUMNS).where(users.c.email == email))).first()
    return _record(row) if row else None


async def by_id(session: AsyncSession, user_id: uuid.UUID) -> UserRecord | None:
    """The account with this id."""
    row = (await session.execute(select(*_COLUMNS).where(users.c.id == user_id))).first()
    return _record(row) if row else None


async def create(session: AsyncSession, email: str, password_hash: str) -> uuid.UUID:
    """Add an account; a second one with the same email is a conflict."""
    try:
        async with session.begin_nested():
            created = await session.execute(
                insert(users).values(email=email, password_hash=password_hash).returning(users.c.id)
            )
    except IntegrityError as error:
        msg = f"A user with the email {email} already exists."
        raise ConflictError(msg) from error
    return uuid.UUID(str(created.scalar_one()))


async def record_failure(
    session: AsyncSession, user_id: uuid.UUID, now: datetime, max_attempts: int, lock_for: timedelta
) -> None:
    """Count a wrong password; on the last allowed one, lock the account and restart the count.

    One UPDATE, so two wrong passwords at the same moment cannot both read the old count.
    """
    reaches_limit = users.c.failed_attempts + 1 >= max_attempts
    await session.execute(
        update(users)
        .where(users.c.id == user_id)
        .values(
            failed_attempts=case((reaches_limit, 0), else_=users.c.failed_attempts + 1),
            locked_until=case((reaches_limit, now + lock_for), else_=users.c.locked_until),
            updated_at=func.now(),
        )
    )


async def clear_failures(session: AsyncSession, user_id: uuid.UUID) -> None:
    """A correct password resets the count and any lock."""
    await session.execute(
        update(users)
        .where(users.c.id == user_id)
        .values(failed_attempts=0, locked_until=None, updated_at=func.now())
    )


async def set_password(session: AsyncSession, email: str, password_hash: str) -> bool:
    """Replace the hash and unlock the account; False when the email is unknown."""
    result = await session.execute(
        update(users)
        .where(users.c.email == email)
        .values(
            password_hash=password_hash,
            failed_attempts=0,
            locked_until=None,
            updated_at=func.now(),
        )
    )
    return bool(result.rowcount)  # type: ignore[attr-defined]  # CursorResult from an UPDATE


async def disable(session: AsyncSession, email: str, now: datetime) -> bool:
    """Stop an account from signing in; False when the email is unknown."""
    result = await session.execute(
        update(users).where(users.c.email == email).values(disabled_at=now, updated_at=func.now())
    )
    return bool(result.rowcount)  # type: ignore[attr-defined]  # CursorResult from an UPDATE
