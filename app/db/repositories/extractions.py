"""SQL for extracted fields. The service owns the transaction around these calls."""

import uuid

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.tables import extractions
from app.domain.contracts import FieldRow


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
