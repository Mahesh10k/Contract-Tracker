"""Send the reminders that are due: claim, send, record; give the reminder back if mail fails.

The order is what makes a reminder go out at most once and never get lost (AC-US-00-006-3 and 6):
1. claim it (pending to sending) so a second run cannot pick it up;
2. send the email;
3. only after the mail server accepted it, mark it sent; if sending fails, set it back to pending
   so the next run tries again, and stop with an error naming MailHog.
A crash between 2 and 3 leaves a reminder in `sending`, which is never re-sent: the accepted
trade-off is a lost email, never a doubled one (docs/design/data-model.md).
"""

import uuid
from dataclasses import dataclass
from datetime import date
from email.message import EmailMessage
from typing import Protocol

import structlog

from app.core.errors import DomainError
from app.reminders.plan import DueReminder, choose, render_email

log = structlog.get_logger()


class ReminderDeliveryError(DomainError):
    """The mail server did not accept the email; the reminder stays pending."""

    status_code = 502
    code = "reminder_delivery_failed"


class ReminderStore(Protocol):
    """Where reminders and their statuses live (Postgres in the app, a dict in tests)."""

    async def due(self, today: date) -> list[DueReminder]: ...
    async def claim(self, reminder_id: uuid.UUID, recipient: str) -> bool: ...
    async def mark_sent(self, reminder_id: uuid.UUID) -> None: ...
    async def revert(self, reminder_id: uuid.UUID) -> None: ...
    async def mark_skipped(self, reminder_ids: list[uuid.UUID]) -> None: ...


class Mailer(Protocol):
    """Sends one email or raises ReminderDeliveryError."""

    async def send(self, message: EmailMessage) -> None: ...


@dataclass(frozen=True)
class SendResult:
    """What a run did."""

    sent: int
    skipped: int


async def send_due(
    store: ReminderStore, mailer: Mailer, today: date, recipient: str, sender: str
) -> SendResult:
    """Email every reminder that is due as of `today`; see the module note for the order."""
    choice = choose(await store.due(today), today)
    if choice.skip:
        await store.mark_skipped([r.id for r in choice.skip])
    sent = 0
    for reminder in choice.send:
        if not await store.claim(reminder.id, recipient):
            continue
        try:
            await mailer.send(render_email(reminder, today, recipient, sender))
        except ReminderDeliveryError:
            await store.revert(reminder.id)
            log.warning("reminder_not_sent", reminder_id=str(reminder.id))
            raise
        await store.mark_sent(reminder.id)
        sent += 1
    log.info("reminders_sent", sent=sent, skipped=len(choice.skip), today=today.isoformat())
    return SendResult(sent=sent, skipped=len(choice.skip))
