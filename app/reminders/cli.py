"""`make remind`: send the reminders that are due, as of today or a date you give."""

import argparse
import asyncio
import sys
from datetime import UTC, date, datetime

from app.core.config import get_settings
from app.core.errors import DomainError
from app.db.session import make_engine, make_session_factory
from app.reminders.plan import resolve_today
from app.ui.service import UiService


async def _run(explicit: date | None) -> int:
    settings = get_settings()
    today = resolve_today(explicit, settings.pretend_today, datetime.now(UTC).date())
    engine = make_engine(settings)
    try:
        message = await UiService(settings, make_session_factory(engine)).send_due_reminders(today)
    except DomainError as exc:
        sys.stderr.write(f"{exc.message}\n")
        return 1
    finally:
        await engine.dispose()
    sys.stdout.write(f"{message} (today is {today.isoformat()})\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    """`python -m app.reminders.cli [--today YYYY-MM-DD]`."""
    parser = argparse.ArgumentParser(description="Send due reminders to MailHog.")
    parser.add_argument(
        "--today", type=date.fromisoformat, default=None, help="treat this as today"
    )
    return asyncio.run(_run(parser.parse_args(argv).today))


if __name__ == "__main__":
    sys.exit(main())
