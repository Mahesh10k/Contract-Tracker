"""The llm_calls ledger: one row per gateway attempt; its sum is the budget stop's spend."""

from datetime import UTC, date, datetime, time
from decimal import Decimal

from sqlalchemy import func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.tables import llm_calls
from app.llm.gateway import CallRecord


class LlmCallLedger:
    """The gateway's Ledger on Postgres. The caller owns the transaction."""

    def __init__(self, session: AsyncSession, since: date | None = None) -> None:
        self.session = session
        self.since = since

    async def spent_usd(self) -> Decimal:
        """Recorded spend since `since` (every run when None), for the budget stop (ADR-0014)."""
        query = select(func.coalesce(func.sum(llm_calls.c.cost_usd), 0))
        if self.since is not None:
            start = datetime.combine(self.since, time.min, tzinfo=UTC)
            query = query.where(llm_calls.c.created_at >= start)
        total = await self.session.scalar(query)
        return Decimal(total or 0)

    async def record(self, call: CallRecord) -> None:
        """Store one attempt."""
        await self.session.execute(
            insert(llm_calls).values(
                run_id=call.run_id,
                prompt_name=call.prompt_name,
                prompt_version=call.prompt_version,
                model_id=call.model_id,
                cache_key=call.cache_key,
                cache_hit=call.cache_hit,
                input_tokens=call.input_tokens,
                output_tokens=call.output_tokens,
                cost_usd=call.cost_usd,
            )
        )
