"""Obligations and reminders on Postgres with a fake mailer (US-00-006, TC-0171, 0174)."""

from datetime import date
from email.message import EmailMessage
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.repositories import contracts as contract_repo
from app.db.repositories import extractions as field_repo
from app.db.repositories.reminders import PgReminderStore
from app.domain.contracts import FieldRow
from app.ingestion.service import ingest_file
from app.reminders.mailer import SmtpMailer
from app.reminders.service import ReminderDeliveryError, send_due
from app.reminders.sync import sync_all

pytestmark = pytest.mark.integration

DATA = Path(__file__).parents[2] / "data" / "contracts"


class RecordingMailer:
    def __init__(self) -> None:
        self.sent: list[EmailMessage] = []

    async def send(self, message: EmailMessage) -> None:
        self.sent.append(message)


@pytest.fixture
async def factory(session: AsyncSession) -> async_sessionmaker[AsyncSession]:
    connection = await session.connection()
    return async_sessionmaker(bind=connection, join_transaction_mode="create_savepoint")


async def extracted_lease_01(session: AsyncSession) -> None:
    """lease-01 with its three date fields accepted, as the golden answer key gives them."""
    contract = (await ingest_file(session, DATA / "lease-01.pdf")).contract_id
    clauses = {c.number: c for c in await contract_repo.clauses_of(session, contract)}
    rows = [
        FieldRow(
            "effective_date",
            "1 January 2025",
            "The term commences on 1 January 2025.",
            "2.1",
            clauses["2.1"].id,
            "accepted",
            None,
        ),
        FieldRow(
            "term",
            "two (2) years",
            "The term is two (2) years from the commencement date.",
            "2.2",
            clauses["2.2"].id,
            "accepted",
            None,
        ),
        FieldRow(
            "notice_period",
            "not less than thirty days",
            "Either party may end this Lease at expiry by giving not less than thirty days "
            "written notice before the end of the term.",
            "7",
            clauses["7"].id,
            "accepted",
            None,
        ),
    ]
    await field_repo.upsert_extractions(session, contract, rows, prompt_version="v2", model_id="m")


async def statuses(session: AsyncSession) -> dict[str, int]:
    result = await session.execute(text("SELECT status::text, count(*) FROM reminders GROUP BY 1"))
    return {row[0]: row[1] for row in result}


# TC-0171
async def test_tc0171_accepted_fields_become_obligations_and_reminders_sent_once(
    session: AsyncSession, factory: async_sessionmaker[AsyncSession]
) -> None:
    await extracted_lease_01(session)
    await sync_all(session)
    await sync_all(session)  # a second sync must not duplicate anything
    store, mailer = PgReminderStore(factory), RecordingMailer()

    first = await send_due(store, mailer, date(2026, 10, 31), "owner@x.test", "r@x.test")
    second = await send_due(store, mailer, date(2026, 10, 31), "owner@x.test", "r@x.test")

    assert await session.scalar(text("SELECT count(*) FROM obligations")) == 2
    assert await session.scalar(text("SELECT count(*) FROM reminders")) == 6
    # TC-0104: each obligation has its date and points at the field it was computed from.
    dates = await session.execute(
        text(
            "SELECT o.kind::text, o.due_on, e.field_name::text FROM obligations o "
            "JOIN extractions e ON e.id = o.source_extraction_id ORDER BY o.due_on"
        )
    )
    assert [tuple(r) for r in dates] == [
        ("notice_deadline", date(2026, 12, 1), "notice_period"),
        ("expiry", date(2026, 12, 31), "term"),
    ]
    assert (first.sent, second.sent) == (1, 0)
    assert "2026-12-01" in mailer.sent[0].get_content()
    assert "clause 7" in mailer.sent[0].get_content()
    assert await statuses(session) == {"sent": 1, "pending": 5}
    assert (
        await session.scalar(
            text("SELECT count(*) FROM reminders WHERE status = 'sent' AND sent_at IS NULL")
        )
        == 0
    )


async def test_a_run_after_the_deadline_skips_instead_of_emailing(
    session: AsyncSession, factory: async_sessionmaker[AsyncSession]
) -> None:
    await extracted_lease_01(session)
    await sync_all(session)
    mailer = RecordingMailer()

    result = await send_due(
        PgReminderStore(factory), mailer, date(2027, 1, 15), "o@x.test", "r@x.test"
    )

    assert (result.sent, mailer.sent) == (0, [])
    assert await statuses(session) == {"skipped": 6}


# TC-0174
async def test_tc0174_an_unreachable_mail_server_leaves_every_reminder_pending(
    session: AsyncSession, factory: async_sessionmaker[AsyncSession]
) -> None:
    await extracted_lease_01(session)
    await sync_all(session)

    with pytest.raises(ReminderDeliveryError, match="MailHog"):
        await send_due(
            PgReminderStore(factory),
            SmtpMailer("localhost", 1),
            date(2026, 10, 31),
            "o@x.test",
            "r@x.test",
        )

    assert await statuses(session) == {"pending": 6}
    assert (
        await session.scalar(text("SELECT count(*) FROM reminders WHERE sent_at IS NOT NULL")) == 0
    )


async def test_a_corrected_date_replaces_the_obligation_and_keeps_the_unchanged_one(
    session: AsyncSession,
) -> None:
    await extracted_lease_01(session)
    await sync_all(session)
    before = await session.scalar(text("SELECT id FROM obligations WHERE kind = 'notice_deadline'"))
    await session.execute(
        text(
            "UPDATE extractions SET status = 'corrected', corrected_value = 'five (5) years', "
            "corrected_at = now() WHERE field_name = 'term'"
        )
    )

    await sync_all(session)

    assert await session.scalar(
        text("SELECT due_on FROM obligations WHERE kind = 'expiry'")
    ) == date(2029, 12, 31)
    assert (
        await session.scalar(text("SELECT id FROM obligations WHERE kind = 'notice_deadline'"))
        == before
    )


# TC-0183
async def test_tc0183_sync_all_holds_the_advisory_lock_and_two_syncs_leave_one_set(
    session: AsyncSession,
) -> None:
    # Review 6: the lock makes a second concurrent sync wait and then find the work done.
    from app.reminders.sync import SYNC_LOCK_KEY

    await extracted_lease_01(session)

    await sync_all(session)
    await sync_all(session)

    held = await session.scalar(
        text(
            "SELECT count(*) FROM pg_locks WHERE locktype = 'advisory' AND granted "
            "AND pid = pg_backend_pid() AND objid = :key"
        ),
        {"key": SYNC_LOCK_KEY},
    )
    assert held == 1
    assert await session.scalar(text("SELECT count(*) FROM obligations")) == 2
    assert await session.scalar(text("SELECT count(*) FROM reminders")) == 6
