"""Turn accepted fields into stored obligations and their planned reminders.

Dates come from compute_obligations (never the model). Obligations are recomputed from the
contract's accepted or corrected fields every time: a changed date replaces the old obligation,
an unchanged one keeps its reminders, and a field that has gone back to review removes its date.
"""

import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories import contracts as contract_repo
from app.db.repositories import reminders as repo
from app.obligations.compute import FieldText, compute_obligations
from app.reminders.plan import diff_obligations, plan_reminders

SOURCES = ("effective_date", "term", "notice_period")
# The field each obligation is traced back to (obligations.source_extraction_id).
SOURCE_OF = {"expiry": "term", "notice_deadline": "notice_period"}


async def sync_obligations(session: AsyncSession, contract_id: uuid.UUID) -> None:
    """Make the contract's obligations and reminders match its accepted fields."""
    sources = await repo.usable_sources(session, contract_id, SOURCES)
    texts = {name: FieldText(src.value, src.clause) for name, src in sources.items()}
    computed = compute_obligations(texts).obligations
    desired: set[tuple[str, date]] = {(o.kind, o.due) for o in computed}
    existing = await repo.existing_obligations(session, contract_id)
    to_delete, to_insert = diff_obligations(set(existing), desired)
    await repo.delete_obligations(session, [existing[key] for key in to_delete])
    for kind, due_on in to_insert:
        source = sources[SOURCE_OF[kind]]
        existing[(kind, due_on)] = await repo.insert_obligation(
            session, contract_id, source.extraction_id, kind, due_on
        )
    for key in desired:
        await repo.plan_for(session, existing[key], plan_reminders(key[1]))


async def sync_all(session: AsyncSession) -> int:
    """Sync every loaded contract; returns how many were looked at."""
    ids = await contract_repo.all_contract_ids(session)
    for contract_id in ids:
        await sync_obligations(session, contract_id)
    return len(ids)
