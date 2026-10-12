"""Login and session checks (ADR-0017): who may sign in, and who a session belongs to."""

import secrets
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Protocol

from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth.passwords import dummy_hash, verify_password
from app.auth.tokens import issue_token, read_token
from app.core.config import Settings
from app.core.errors import InvalidCredentialsError
from app.db.repositories import users as user_repo
from app.db.repositories.users import UserRecord


class AuthApi(Protocol):
    """What the routes need; tests replace it with a fake."""

    async def login(self, email: str, password: str) -> tuple[UserRecord, str]: ...

    async def user_for_token(self, token: str) -> UserRecord | None: ...


class AuthService:
    """Checks passwords, locks accounts after repeated failures and issues session tokens."""

    def __init__(
        self,
        settings: Settings,
        factory: async_sessionmaker[AsyncSession],
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.settings = settings
        self.factory = factory
        self.clock = clock
        configured = settings.session_secret
        # Development and tests only: production settings refuse to start without a secret.
        self._secret = configured.get_secret_value() if configured else secrets.token_urlsafe(32)

    @property
    def ttl(self) -> timedelta:
        """How long a session lasts."""
        return timedelta(hours=self.settings.session_ttl_hours)

    async def login(self, email: str, password: str) -> tuple[UserRecord, str]:
        """The account and a session token for a correct email and password.

        Every refusal raises the same error: unknown email, wrong password, locked and disabled
        accounts look alike, and an unknown email still pays for one hash check.
        """
        now = self.clock()
        accepted: UserRecord | None = None
        async with self.factory() as session, session.begin():
            user = await user_repo.by_email(session, email)
            stored = user.password_hash if user else dummy_hash()
            matches = await run_in_threadpool(verify_password, password, stored)
            if user is not None:
                locked = user.locked_until is not None and user.locked_until > now
                usable = user.disabled_at is None and not locked
                if usable and matches:
                    await user_repo.clear_failures(session, user.id)
                    accepted = user
                elif usable:
                    await user_repo.record_failure(
                        session,
                        user.id,
                        now,
                        self.settings.login_max_attempts,
                        timedelta(minutes=self.settings.login_lock_minutes),
                    )
        if accepted is None:
            msg = "Wrong email or password, or the account is locked for a few minutes."
            raise InvalidCredentialsError(msg)
        return accepted, issue_token(accepted.id, self._secret, now, self.ttl)

    async def user_for_token(self, token: str) -> UserRecord | None:
        """The active account a token belongs to; None for a bad, expired or disabled one."""
        user_id: uuid.UUID | None = read_token(token, self._secret, self.clock())
        if user_id is None:
            return None
        async with self.factory() as session:
            user = await user_repo.by_id(session, user_id)
        return user if user is not None and user.disabled_at is None else None
