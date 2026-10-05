"""The llm_calls ledger behind the gateway's budget stop (Q-007, TC-0049, TC-0051)."""

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from pydantic import BaseModel, ConfigDict, SecretStr
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.llm_calls import LlmCallLedger
from app.db.tables import llm_calls
from app.llm.cache import ReplyCache
from app.llm.gateway import BudgetReachedError, CallRecord, Gateway, LLMRequest
from tests.llm.fakes import chat_reply

pytestmark = pytest.mark.integration


class Answer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answer: str


def request(contract: str) -> LLMRequest:
    return LLMRequest(
        feature="extraction",
        prompt_name="extract_fields",
        prompt_version="v1",
        system="Extract fields.",
        user=contract,
        max_tokens=2000,
    )


def earlier_spend(usd: str) -> CallRecord:
    return CallRecord(
        run_id=uuid4(),
        prompt_name="extract_fields",
        prompt_version="v1",
        model_id="anthropic/claude-haiku-4.5",
        cache_key="e" * 64,
        cache_hit=False,
        input_tokens=1,
        output_tokens=1,
        cost_usd=Decimal(usd),
    )


def gateway(ledger: LlmCallLedger, tmp_path: Path, sent: list[httpx.Request]) -> Gateway:
    def reply(req: httpx.Request) -> httpx.Response:
        sent.append(req)
        return httpx.Response(200, json=chat_reply({"answer": "Delaware"}, cost=0.0135))

    return Gateway(
        client=httpx.AsyncClient(transport=httpx.MockTransport(reply)),
        cache=ReplyCache(tmp_path),
        ledger=ledger,
        model="anthropic/claude-haiku-4.5",
        api_key=SecretStr("sk-test"),
        budget_stop_usd=Decimal("9"),
        run_id=uuid4(),
    )


async def test_recorded_calls_add_up_to_the_spend(session: AsyncSession) -> None:
    ledger = LlmCallLedger(session)
    await ledger.record(earlier_spend("1.250000"))
    await ledger.record(earlier_spend("0.013500"))

    assert await ledger.spent_usd() == Decimal("1.263500")


async def test_tc0049_spend_at_nine_dollars_stops_the_call(
    session: AsyncSession, tmp_path: Path
) -> None:
    ledger = LlmCallLedger(session)
    await ledger.record(earlier_spend("9.000000"))
    sent: list[httpx.Request] = []

    with pytest.raises(BudgetReachedError):
        await gateway(ledger, tmp_path, sent).parse(request("contract A"), Answer)

    assert sent == []
    assert await session.scalar(select(func.count()).select_from(llm_calls)) == 1


async def test_tc0051_the_call_that_crosses_nine_is_recorded_and_the_next_is_refused(
    session: AsyncSession, tmp_path: Path
) -> None:
    ledger = LlmCallLedger(session)
    await ledger.record(earlier_spend("8.995000"))
    sent: list[httpx.Request] = []
    gw = gateway(ledger, tmp_path, sent)

    await gw.parse(request("contract A"), Answer)
    with pytest.raises(BudgetReachedError):
        await gw.parse(request("contract B"), Answer)

    assert await ledger.spent_usd() == Decimal("9.008500")
    assert len(sent) == 1


async def test_tc0090_spend_before_the_budget_window_does_not_count(session: AsyncSession) -> None:
    # TASK-008, ADR-0014: USD 2 for the day, counted from LLM_BUDGET_SINCE.
    await LlmCallLedger(session).record(earlier_spend("5.00"))
    await session.execute(
        llm_calls.update()
        .where(llm_calls.c.cost_usd == Decimal("5.00"))
        .values(created_at=datetime(2026, 10, 4, 12, tzinfo=UTC))
    )
    await LlmCallLedger(session).record(earlier_spend("0.10"))

    spent = await LlmCallLedger(session, since=date(2026, 10, 5)).spent_usd()

    assert spent == Decimal("0.10")
