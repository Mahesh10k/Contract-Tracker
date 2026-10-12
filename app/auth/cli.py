"""Create and manage users from the command line (`make user`); there is no sign-up page.

    python -m app.auth.cli create you@example.com
    python -m app.auth.cli set-password you@example.com
    python -m app.auth.cli disable you@example.com

The password is asked for twice with no echo and is never printed or logged.
"""

import argparse
import asyncio
import getpass
import sys
from collections.abc import Callable, Sequence
from datetime import UTC, datetime

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth.passwords import hash_password
from app.auth.validation import normalise_email, password_problems
from app.core.config import get_settings
from app.core.errors import ConflictError
from app.db.repositories import users as user_repo
from app.db.session import make_engine, make_session_factory

Prompt = Callable[[str], str]


def _ask_password(email: str, prompt: Prompt) -> str:
    password = prompt("Password: ")
    problems = password_problems(password, email)
    if problems:
        raise ValueError(" ".join(problems))
    if prompt("Repeat the password: ") != password:
        msg = "The two passwords are not the same."
        raise ValueError(msg)
    return password


async def run(
    command: str,
    raw_email: str,
    factory: async_sessionmaker[AsyncSession],
    prompt: Prompt = getpass.getpass,
) -> str:
    """Do one command and return the line to print."""
    email = normalise_email(raw_email)
    async with factory() as session, session.begin():
        if command == "create":
            password = _ask_password(email, prompt)
            await user_repo.create(session, email, hash_password(password))
            return f"Created {email}."
        if command == "set-password":
            password = _ask_password(email, prompt)
            changed = await user_repo.set_password(session, email, hash_password(password))
            return f"Password changed for {email}." if changed else f"No user {email}."
        changed = await user_repo.disable(session, email, datetime.now(UTC))
        return f"Disabled {email}." if changed else f"No user {email}."


def main(argv: Sequence[str] | None = None) -> int:
    """The `make user` entry point."""
    parser = argparse.ArgumentParser(prog="app.auth.cli", description=__doc__)
    parser.add_argument("command", choices=["create", "set-password", "disable"])
    parser.add_argument("email")
    args = parser.parse_args(argv)
    engine = make_engine(get_settings())

    async def go() -> str:
        try:
            return await run(args.command, args.email, make_session_factory(engine))
        finally:
            await engine.dispose()

    try:
        sys.stdout.write(asyncio.run(go()) + "\n")
    except (ValueError, ConflictError) as error:
        sys.stderr.write(f"{error}\n")
        return 1
    except SQLAlchemyError as error:
        # Usually the database is unreachable or migration 0004 has not been applied yet.
        sys.stderr.write(
            f"Database error ({type(error).__name__}). Check DATABASE_URL, and run make migrate "
            "so the users table exists, then try again.\n"
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
