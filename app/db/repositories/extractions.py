"""SQL for extracted fields. The service owns the transaction around these calls."""

import uuid
from collections.abc import Sequence

from sqlalchemy import Result, Select, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.tables import contracts, extractions
from app.domain.contracts import FieldRow, StoredField


async def upsert_extractions(
    session: AsyncSession,
    contract_id: uuid.UUID,
    rows: list[FieldRow],
    *,
    prompt_version: str,
    model_id: str,
) -> None:
    """Insert or refresh a contract's fields in one statement.

    A field the owner corrected keeps its row untouched (Q-018): the update
    only applies where the stored status is not `corrected`.
    """
    statement = insert(extractions).values(
        [
            {
                "contract_id": contract_id,
                "field_name": r.field_name,
                "value_text": r.value_text,
                "quote": r.quote,
                "cited_clause_number": r.cited_clause_number,
                "clause_id": r.clause_id,
                "status": r.status,
                "review_reason": r.review_reason,
                "prompt_version": prompt_version,
                "model_id": model_id,
            }
            for r in rows
        ]
    )
    excluded = statement.excluded
    await session.execute(
        statement.on_conflict_do_update(
            index_elements=[extractions.c.contract_id, extractions.c.field_name],
            set_={
                "value_text": excluded.value_text,
                "quote": excluded.quote,
                "cited_clause_number": excluded.cited_clause_number,
                "clause_id": excluded.clause_id,
                "status": excluded.status,
                "review_reason": excluded.review_reason,
                "prompt_version": excluded.prompt_version,
                "model_id": excluded.model_id,
                "updated_at": func.now(),
            },
            where=extractions.c.status != "corrected",
        )
    )


def _field_query() -> Select[tuple[object, ...]]:
    return select(
        extractions.c.contract_id,
        contracts.c.title,
        extractions.c.field_name,
        func.coalesce(extractions.c.corrected_value, extractions.c.value_text).label("value"),
        extractions.c.quote,
        extractions.c.cited_clause_number,
        extractions.c.status,
        extractions.c.review_reason,
    ).join(contracts, contracts.c.id == extractions.c.contract_id)


def _stored(rows: Result[tuple[object, ...]]) -> list[StoredField]:
    return [
        StoredField(
            contract_id=r.contract_id,
            contract_title=r.title,
            field_name=r.field_name,
            value=r.value,
            quote=r.quote,
            clause_number=r.cited_clause_number,
            status=r.status,
            review_reason=r.review_reason,
        )
        for r in rows
    ]


async def fields_of(
    session: AsyncSession, contract_id: uuid.UUID, names: Sequence[str]
) -> list[StoredField]:
    """A contract's stored fields among `names`, in the enum's field order."""
    query = (
        _field_query()
        .where(extractions.c.contract_id == contract_id, extractions.c.field_name.in_(names))
        .order_by(extractions.c.field_name)
    )
    return _stored(await session.execute(query))


async def held_fields(
    session: AsyncSession, names: Sequence[str], limit: int = 500
) -> list[StoredField]:
    """Fields waiting for review, oldest first (idx_extractions_needs_review)."""
    query = (
        _field_query()
        .where(extractions.c.status == "needs_review", extractions.c.field_name.in_(names))
        .order_by(extractions.c.created_at, contracts.c.title, extractions.c.field_name)
        .limit(limit)
    )
    return _stored(await session.execute(query))


async def usable_fields(
    session: AsyncSession, names: Sequence[str], limit: int = 5000
) -> list[StoredField]:
    """Accepted or corrected fields of every contract, the only inputs dates are computed from."""
    query = (
        _field_query()
        .where(
            extractions.c.status.in_(("accepted", "corrected")),
            extractions.c.field_name.in_(names),
        )
        .order_by(contracts.c.title, extractions.c.contract_id, extractions.c.field_name)
        .limit(limit)
    )
    return _stored(await session.execute(query))
