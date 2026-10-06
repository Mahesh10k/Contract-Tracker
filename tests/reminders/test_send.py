"""Sending due reminders: claim, send, record, and what happens when mail fails (US-00-006)."""

import uuid
from datetime import date
from email.message import EmailMessage

import pytest

from app.reminders.plan import DueReminder
from app.reminders.service import ReminderDeliveryError, send_due

TODAY = date(2026, 10, 31)


class InMemoryStore:
    """Holds reminders and their statuses; `claim_wins` False plays a run that lost the race."""

    def __init__(self, reminders: list[DueReminder], *, claim_wins: bool = True) -> None:
        self.status = {r.id: "pending" for r in reminders}
        self.reminders = reminders
        self.claim_wins = claim_wins
        self.recipients: dict[uuid.UUID, str] = {}

    async def due(self, today: date) -> list[DueReminder]:
        return [r for r in self.reminders if self.status[r.id] == "pending"]

    async def claim(self, reminder_id: uuid.UUID, recipient: str) -> bool:
        if not self.claim_wins or self.status[reminder_id] != "pending":
            return False
        self.status[reminder_id] = "sending"
        self.recipients[reminder_id] = recipient
        return True

    async def mark_sent(self, reminder_id: uuid.UUID) -> None:
        self.status[reminder_id] = "sent"

    async def revert(self, reminder_id: uuid.UUID) -> None:
        self.status[reminder_id] = "pending"

    async def mark_skipped(self, reminder_ids: list[uuid.UUID]) -> None:
        for rid in reminder_ids:
            self.status[rid] = "skipped"


class RecordingMailer:
    def __init__(self, fail: bool = False) -> None:
        self.sent: list[EmailMessage] = []
        self.fail = fail

    async def send(self, message: EmailMessage) -> None:
        if self.fail:
            raise ReminderDeliveryError("Could not reach MailHog at localhost:1025")
        self.sent.append(message)


def reminder(lead: int, due_on: date, obligation: uuid.UUID | None = None) -> DueReminder:
    return DueReminder(
        uuid.uuid4(),
        obligation or uuid.uuid4(),
        lead,
        due_on,
        "notice_deadline",
        "Lease Agreement 01",
        "7",
    )


async def run(
    store: InMemoryStore, mailer: RecordingMailer, today: date = TODAY
) -> tuple[int, int]:
    result = await send_due(store, mailer, today, "owner@x.test", "reminders@x.test")
    return result.sent, result.skipped


# TC-0165
async def test_tc0165_a_due_reminder_is_emailed_once_and_a_second_run_sends_nothing() -> None:
    store = InMemoryStore([reminder(30, date(2026, 11, 30))])
    mailer = RecordingMailer()

    first = await run(store, mailer)
    second = await run(store, mailer)

    assert (first, second) == ((1, 0), (0, 0))
    assert len(mailer.sent) == 1
    assert set(store.status.values()) == {"sent"}


# TC-0166
async def test_tc0166_after_a_gap_the_missed_thirty_day_reminder_goes_out_once() -> None:
    thirty = reminder(30, date(2028, 11, 30))
    seven = reminder(7, date(2028, 11, 30))
    store = InMemoryStore([thirty])  # the 60-day one was sent earlier; the 7-day is not yet due
    mailer = RecordingMailer()

    await run(store, mailer, date(2028, 11, 5))

    assert len(mailer.sent) == 1
    assert "25 days" in mailer.sent[0].get_content()
    assert store.status[thirty.id] == "sent"
    assert seven.id not in store.status


async def test_the_older_reminders_of_one_deadline_are_skipped_when_a_newer_one_is_sent() -> None:
    obligation = uuid.uuid4()
    rs = [reminder(lead, date(2026, 11, 3), obligation) for lead in (60, 30, 7)]
    store = InMemoryStore(rs)
    mailer = RecordingMailer()

    sent, skipped = await run(store, mailer)

    assert (sent, skipped) == (1, 2)
    assert [store.status[r.id] for r in rs] == ["skipped", "skipped", "sent"]


async def test_an_expired_deadline_is_skipped_and_nothing_is_emailed() -> None:
    store = InMemoryStore([reminder(7, date(2026, 10, 1))])
    mailer = RecordingMailer()

    sent, skipped = await run(store, mailer)

    assert (sent, skipped) == (0, 1)
    assert mailer.sent == []


# TC-0167
async def test_tc0167_unreachable_mail_returns_the_reminder_to_pending_and_names_mailhog() -> None:
    r = reminder(30, date(2026, 11, 30))
    store = InMemoryStore([r])

    with pytest.raises(ReminderDeliveryError, match="MailHog"):
        await run(store, RecordingMailer(fail=True))

    assert store.status[r.id] == "pending"


async def test_after_a_failure_the_next_run_sends_the_same_reminder() -> None:
    r = reminder(30, date(2026, 11, 30))
    store = InMemoryStore([r])
    with pytest.raises(ReminderDeliveryError):
        await run(store, RecordingMailer(fail=True))
    mailer = RecordingMailer()

    await run(store, mailer)

    assert len(mailer.sent) == 1
    assert store.status[r.id] == "sent"


# TC-0168
async def test_tc0168_a_reminder_claimed_by_another_run_is_not_emailed_again() -> None:
    store = InMemoryStore([reminder(30, date(2026, 11, 30))], claim_wins=False)
    mailer = RecordingMailer()

    sent, _ = await run(store, mailer)

    assert sent == 0
    assert mailer.sent == []


async def test_the_recipient_is_recorded_when_a_reminder_is_claimed() -> None:
    r = reminder(30, date(2026, 11, 30))
    store = InMemoryStore([r])

    await run(store, RecordingMailer())

    assert store.recipients[r.id] == "owner@x.test"


# TC-0177
async def test_a_preview_emails_what_is_due_but_records_nothing() -> None:
    # Review 3: a "today" ahead of the real clock must not retire or mark real reminders.
    due_soon = reminder(7, date(2026, 11, 3))
    older = reminder(30, date(2026, 11, 3), due_soon.obligation_id)
    expired = reminder(7, date(2026, 10, 1))
    store = InMemoryStore([due_soon, older, expired])
    mailer = RecordingMailer()

    result = await send_due(store, mailer, TODAY, "owner@x.test", "r@x.test", record=False)

    assert (result.sent, result.skipped) == (1, 2)
    assert len(mailer.sent) == 1
    assert set(store.status.values()) == {"pending"}
    assert store.recipients == {}


async def test_a_preview_sends_again_on_the_next_press_because_nothing_was_recorded() -> None:
    store = InMemoryStore([reminder(7, date(2026, 11, 3))])
    mailer = RecordingMailer()

    await send_due(store, mailer, TODAY, "o@x.test", "r@x.test", record=False)
    await send_due(store, mailer, TODAY, "o@x.test", "r@x.test", record=False)

    assert len(mailer.sent) == 2


async def test_a_preview_still_reports_a_delivery_failure() -> None:
    store = InMemoryStore([reminder(7, date(2026, 11, 3))])

    with pytest.raises(ReminderDeliveryError, match="MailHog"):
        await send_due(
            store, RecordingMailer(fail=True), TODAY, "o@x.test", "r@x.test", record=False
        )
