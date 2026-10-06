"""Pure reminder logic: when to remind, which reminders to send, what the email says.

No database and no network here, so every rule can be tested with dates alone (REQ-016, Q-019,
Q-029). Reminders go out 60, 30 and 7 days before a deadline. A run sends, per deadline, only the
reminder closest to the deadline that is due, and skips the older ones: the owner who was away for
a month gets one email, not three. A deadline already past gets nothing.
"""

import uuid
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from email.message import EmailMessage

LEADS = (60, 30, 7)
KIND_LABELS = {"expiry": "Contract expires", "notice_deadline": "Notice deadline"}


@dataclass(frozen=True)
class PlannedReminder:
    """One reminder to create: how many days before, and the day it becomes due."""

    lead_days: int
    send_on: date


@dataclass(frozen=True)
class DueReminder:
    """A pending reminder whose send date has come, with what its email needs."""

    id: uuid.UUID
    obligation_id: uuid.UUID
    lead_days: int
    due_on: date
    kind: str
    contract_title: str
    clause: str | None


@dataclass(frozen=True)
class Choice:
    """Reminders to email now and reminders to retire without emailing."""

    send: list[DueReminder]
    skip: list[DueReminder]


def plan_reminders(due_on: date) -> list[PlannedReminder]:
    """The reminders for one deadline, longest lead first."""
    return [PlannedReminder(lead, due_on - timedelta(days=lead)) for lead in LEADS]


def choose(due: Iterable[DueReminder], today: date) -> Choice:
    """Per deadline: send the shortest due lead, skip the rest; skip all once it has passed."""
    by_obligation: dict[uuid.UUID, list[DueReminder]] = defaultdict(list)
    for reminder in due:
        by_obligation[reminder.obligation_id].append(reminder)
    send: list[DueReminder] = []
    skip: list[DueReminder] = []
    for group in by_obligation.values():
        if group[0].due_on < today:
            skip.extend(group)
            continue
        newest = min(group, key=lambda r: r.lead_days)
        send.append(newest)
        skip.extend(r for r in group if r is not newest)
    return Choice(send, skip)


def resolve_today(explicit: date | None, pretend: date | None, real: date) -> date:
    """An explicit date wins, then PRETEND_TODAY, then the real clock (REQ-042)."""
    return explicit or pretend or real


def diff_obligations(
    existing: set[tuple[str, date]], desired: set[tuple[str, date]]
) -> tuple[list[tuple[str, date]], list[tuple[str, date]]]:
    """(to delete, to insert): unchanged obligations, and their reminders, are left alone."""
    return sorted(existing - desired), sorted(desired - existing)


def render_email(reminder: DueReminder, today: date, recipient: str, sender: str) -> EmailMessage:
    """The reminder email: contract, obligation, date and, when known, the clause."""
    label = KIND_LABELS.get(reminder.kind, reminder.kind)
    days = (reminder.due_on - today).days
    away = "today" if days == 0 else f"{days} days away"
    lines = [
        f"Contract: {reminder.contract_title}",
        f"Obligation: {label}",
        f"Date: {reminder.due_on.isoformat()} ({away})",
    ]
    if reminder.clause:
        lines.append(f"Where: clause {reminder.clause} of the contract")
    message = EmailMessage()
    message["Subject"] = f"Reminder: {reminder.contract_title}, {label} on {reminder.due_on}"
    message["From"] = sender
    message["To"] = recipient
    message.set_content("\n".join(lines) + "\n")
    return message
