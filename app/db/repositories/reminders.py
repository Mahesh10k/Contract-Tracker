"""SQL for obligations and reminders. Services own the transactions; the store opens its own.

`PgReminderStore` gives every step of a send its own short transaction on purpose: the claim must
be committed before the email goes out, or a second run could not see it (AC-US-00-006-3).
"""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.tables import contracts, extractions, obligations, reminders
from app.reminders.plan import DueReminder, PlannedReminder

DUE_LIMIT = 1000


@dataclass(frozen=True)
class SourceField:
    """An accepted or corrected field a date can be computed from, with its row id."""

    extraction_id: uuid.UUID
    value: str
    clause: str | None


async def usable_sources(
    session: AsyncSession, contract_id: uuid.UUID, names: Sequence[str]
) -> dict[str, SourceField]:
    """The contract's accepted or corrected fields among `names`, by field name."""
    result = await session.execute(
        select(
            extractions.c.id,
            extractions.c.field_name,
            func.coalesce(extractions.c.corrected_value, extractions.c.value_text).label("value"),
            extractions.c.cited_clause_number,
        ).where(
            extractions.c.contract_id == contract_id,
            extractions.c.status.in_(("accepted", "corrected")),
            extractions.c.field_name.in_(names),
        )
    )
    return {
        r.field_name: SourceField(r.id, r.value, r.cited_clause_number)
        for r in result
        if r.value is not None
    }


async def existing_obligations(
    session: AsyncSession, contract_id: uuid.UUID
) -> dict[tuple[str, date], uuid.UUID]:
    """The contract's obligations keyed by (kind, due date)."""
    result = await session.execute(
        select(obligations.c.id, obligations.c.kind, obligations.c.due_on).where(
            obligations.c.contract_id == contract_id
        )
    )
    return {(r.kind, r.due_on): r.id for r in result}


async def delete_obligations(session: AsyncSession, ids: Sequence[uuid.UUID]) -> None:
    """Remove obligations; their reminders go with them (ON DELETE CASCADE)."""
    if ids:
        await session.execute(delete(obligations).where(obligations.c.id.in_(ids)))


async def insert_obligation(
    session: AsyncSession,
    contract_id: uuid.UUID,
    source_extraction_id: uuid.UUID,
    kind: str,
    due_on: date,
) -> uuid.UUID:
    """Store one obligation and return its id."""
    result = await session.execute(
        insert(obligations)
        .values(
            contract_id=contract_id,
            source_extraction_id=source_extraction_id,
            kind=kind,
            due_on=due_on,
        )
        .returning(obligations.c.id)
    )
    inserted: uuid.UUID = result.scalar_one()
    return inserted


async def plan_for(
    session: AsyncSession, obligation_id: uuid.UUID, plans: Sequence[PlannedReminder]
) -> None:
    """Create the reminders of one obligation; ones that already exist are left as they are."""
    await session.execute(
        pg_insert(reminders)
        .values(
            [
                {"obligation_id": obligation_id, "lead_days": p.lead_days, "send_on": p.send_on}
                for p in plans
            ]
        )
        .on_conflict_do_nothing(index_elements=["obligation_id", "lead_days"])
    )


class PgReminderStore:
    """The ReminderStore on Postgres; each call is its own committed transaction."""

    def __init__(self, factory: async_sessionmaker[AsyncSession]) -> None:
        self.factory = factory

    async def due(self, today: date) -> list[DueReminder]:
        """Pending reminders whose send date has come, soonest deadline first (bounded)."""
        async with self.factory() as session:
            result = await session.execute(
                select(
                    reminders.c.id,
                    reminders.c.obligation_id,
                    reminders.c.lead_days,
                    obligations.c.due_on,
                    obligations.c.kind,
                    contracts.c.title,
                    extractions.c.cited_clause_number,
                )
                .join(obligations, obligations.c.id == reminders.c.obligation_id)
                .join(contracts, contracts.c.id == obligations.c.contract_id)
                .join(extractions, extractions.c.id == obligations.c.source_extraction_id)
                .where(reminders.c.status == "pending", reminders.c.send_on <= today)
                .order_by(obligations.c.due_on, contracts.c.title, reminders.c.lead_days)
                .limit(DUE_LIMIT)
            )
            return [
                DueReminder(
                    r.id,
                    r.obligation_id,
                    r.lead_days,
                    r.due_on,
                    r.kind,
                    r.title,
                    r.cited_clause_number,
                )
                for r in result
            ]

    async def claim(self, reminder_id: uuid.UUID, recipient: str) -> bool:
        """pending to sending, only if nobody else did it first."""
        async with self.factory() as session, session.begin():
            result = await session.execute(
                update(reminders)
                .where(reminders.c.id == reminder_id, reminders.c.status == "pending")
                .values(status="sending", recipient=recipient, updated_at=func.now())
                .returning(reminders.c.id)
            )
            return result.first() is not None

    async def mark_sent(self, reminder_id: uuid.UUID) -> None:
        """sending to sent, once the mail server accepted the email."""
        async with self.factory() as session, session.begin():
            await session.execute(
                update(reminders)
                .where(reminders.c.id == reminder_id)
                .values(status="sent", sent_at=func.now(), updated_at=func.now())
            )

    async def revert(self, reminder_id: uuid.UUID) -> None:
        """sending back to pending after a failed send, so the next run tries again."""
        async with self.factory() as session, session.begin():
            await session.execute(
                update(reminders)
                .where(reminders.c.id == reminder_id, reminders.c.status == "sending")
                .values(status="pending", updated_at=func.now())
            )

    async def mark_skipped(self, reminder_ids: list[uuid.UUID]) -> None:
        """Retire reminders that will never be emailed (older leads, expired deadlines)."""
        async with self.factory() as session, session.begin():
            await session.execute(
                update(reminders)
                .where(reminders.c.id.in_(reminder_ids), reminders.c.status == "pending")
                .values(status="skipped", updated_at=func.now())
            )
