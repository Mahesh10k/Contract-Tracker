"""Extraction: one call, 5 fields with prompt v2, each quote checked against its clause.

US-00-002 and, since TASK-008, US-00-010 (ADR-0015): v2 asks for the 5 fields of
REQ-045, and a reply still invalid after the retry holds all 5 for review (REQ-046).
"""

import json
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest
from pydantic import SecretStr
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.repositories.llm_calls import LlmCallLedger
from app.db.tables import extractions, llm_calls
from app.extraction.cli import run as run_cli
from app.extraction.service import extract_contract
from app.ingestion.service import ingest_file
from app.llm.cache import ReplyCache
from app.llm.gateway import BudgetReachedError, CallRecord, Gateway, GatewayFailedError
from evals.contracts.truth import load_truth
from tests.llm.fakes import chat_reply

pytestmark = pytest.mark.integration

DATA = Path(__file__).parents[2] / "data" / "contracts"
FIELDS = ("parties", "effective_date", "term", "auto_renewal", "notice_period")


def perfect_reply(contract_id: str) -> dict[str, object]:
    """The reply a perfect model would give: the answer key's value, quote and clause."""
    truth = load_truth(DATA / f"{contract_id}.truth.json")
    return {
        "status": "ok",
        "reason": None,
        "injection_suspected": False,
        "fields": {
            name: {"value": f["value"], "quote": f["quote"], "clause_id": f["clause"]}
            for name, f in truth["fields"].items()
            if name in FIELDS
        },
    }


def with_field(reply: dict[str, object], name: str, **change: object) -> dict[str, object]:
    fields = dict(reply["fields"])  # type: ignore[call-overload]  # test data built above
    fields[name] = {**fields[name], **change}
    return {**reply, "fields": fields}


class Transport:
    def __init__(self, *replies: httpx.Response | Exception) -> None:
        self.queue = list(replies)
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        reply = self.queue.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


def ok(content: dict[str, object]) -> httpx.Response:
    return httpx.Response(200, json=chat_reply(content, cost=0.0135))


def make_gateway(session: AsyncSession, transport: Transport, cache_dir: Path) -> Gateway:
    return Gateway(
        client=httpx.AsyncClient(transport=httpx.MockTransport(transport)),
        cache=ReplyCache(cache_dir),
        ledger=LlmCallLedger(session),
        model="anthropic/claude-haiku-4.5",
        api_key=SecretStr("sk-test"),
        budget_stop_usd=Decimal("9"),
        run_id=uuid4(),
    )


async def lease_01(session: AsyncSession) -> UUID:
    return (await ingest_file(session, DATA / "lease-01.pdf")).contract_id


async def rows(session: AsyncSession, contract_id: UUID) -> dict[str, tuple[object, ...]]:
    result = await session.execute(
        select(
            extractions.c.field_name,
            extractions.c.status,
            extractions.c.review_reason,
            extractions.c.cited_clause_number,
            extractions.c.clause_id,
            extractions.c.value_text,
        ).where(extractions.c.contract_id == contract_id)
    )
    return {r.field_name: tuple(r)[1:] for r in result}


async def calls(session: AsyncSession) -> int:
    return await session.scalar(select(func.count()).select_from(llm_calls)) or 0


async def test_tc0035_one_call_stores_five_accepted_fields(
    session: AsyncSession, tmp_path: Path
) -> None:
    contract = await lease_01(session)
    transport = Transport(ok(perfect_reply("lease-01")))

    result = await extract_contract(session, make_gateway(session, transport, tmp_path), contract)

    stored = await rows(session, contract)
    assert sorted(stored) == sorted(FIELDS)
    assert {s[0] for s in stored.values()} == {"accepted"}
    assert len(transport.requests) == 1
    assert (result.accepted, result.needs_review) == (5, 0)


async def test_the_request_sends_the_contract_inside_its_delimiters(
    session: AsyncSession, tmp_path: Path
) -> None:
    contract = await lease_01(session)
    transport = Transport(ok(perfect_reply("lease-01")))

    await extract_contract(session, make_gateway(session, transport, tmp_path), contract)

    sent = json.loads(transport.requests[0].content)
    text = " ".join(m["content"] for m in sent["messages"])
    assert "<contract>\n1 Parties\n" in text
    assert "<contract_title>\nLease Agreement 01\n</contract_title>" in text


async def test_tc0037_a_field_the_model_marks_absent_is_held_as_value_missing(
    session: AsyncSession, tmp_path: Path
) -> None:
    contract = await lease_01(session)
    reply = with_field(
        perfect_reply("lease-01"), "auto_renewal", value=None, quote=None, clause_id=None
    )

    await extract_contract(session, make_gateway(session, Transport(ok(reply)), tmp_path), contract)

    assert (await rows(session, contract))["auto_renewal"][:2] == (
        "needs_review",
        "value_missing",
    )


async def test_tc0038_a_field_holds_value_quote_cited_number_and_its_clause(
    session: AsyncSession, tmp_path: Path
) -> None:
    contract = await lease_01(session)

    await extract_contract(
        session, make_gateway(session, Transport(ok(perfect_reply("lease-01"))), tmp_path), contract
    )

    status, reason, cited, clause_id, value = (await rows(session, contract))["term"]
    assert (status, reason, cited) == ("accepted", None, "2.2")
    assert clause_id is not None
    assert value == load_truth(DATA / "lease-01.truth.json")["fields"]["term"]["value"]


async def test_tc0039_a_cited_clause_that_does_not_exist_is_held(
    session: AsyncSession, tmp_path: Path
) -> None:
    contract = await lease_01(session)
    reply = with_field(perfect_reply("lease-01"), "parties", clause_id="99.1")

    await extract_contract(session, make_gateway(session, Transport(ok(reply)), tmp_path), contract)

    status, reason, cited, clause_id, _ = (await rows(session, contract))["parties"]
    assert (status, reason, cited, clause_id) == ("needs_review", "clause_not_found", "99.1", None)


async def test_tc0043_a_quote_with_a_pdf_line_break_is_accepted(
    session: AsyncSession, tmp_path: Path
) -> None:
    contract = await lease_01(session)
    truth = load_truth(DATA / "lease-01.truth.json")
    broken = truth["fields"]["notice_period"]["quote"].replace(" written ", " written\n", 1)
    reply = with_field(perfect_reply("lease-01"), "notice_period", quote=broken)

    await extract_contract(session, make_gateway(session, Transport(ok(reply)), tmp_path), contract)

    assert (await rows(session, contract))["notice_period"][0] == "accepted"


async def test_tc0044_a_made_up_quote_is_held_as_quote_not_found(
    session: AsyncSession, tmp_path: Path
) -> None:
    contract = await lease_01(session)
    reply = with_field(
        perfect_reply("lease-01"), "effective_date", quote="The term commences at will."
    )

    await extract_contract(session, make_gateway(session, Transport(ok(reply)), tmp_path), contract)

    assert (await rows(session, contract))["effective_date"][:2] == (
        "needs_review",
        "quote_not_found",
    )


async def test_tc0045_a_real_quote_cited_to_the_wrong_clause_is_held(
    session: AsyncSession, tmp_path: Path
) -> None:
    contract = await lease_01(session)
    reply = with_field(perfect_reply("lease-01"), "term", clause_id="4")

    await extract_contract(session, make_gateway(session, Transport(ok(reply)), tmp_path), contract)

    assert (await rows(session, contract))["term"][:2] == ("needs_review", "quote_not_found")


async def test_tc0046_a_second_run_replays_the_cache_and_keeps_five_rows(
    session: AsyncSession, tmp_path: Path
) -> None:
    contract = await lease_01(session)
    await extract_contract(
        session, make_gateway(session, Transport(ok(perfect_reply("lease-01"))), tmp_path), contract
    )
    offline = Transport()

    await extract_contract(session, make_gateway(session, offline, tmp_path), contract)

    assert offline.requests == []
    assert len(await rows(session, contract)) == 5


async def test_a_corrected_field_survives_re_extraction(
    session: AsyncSession, tmp_path: Path
) -> None:
    # TASK-002 review finding 4: Q-018, the owner's correction always wins.
    contract = await lease_01(session)
    gateway = make_gateway(session, Transport(ok(perfect_reply("lease-01"))), tmp_path)
    await extract_contract(session, gateway, contract)
    await session.execute(
        update(extractions)
        .where(extractions.c.contract_id == contract, extractions.c.field_name == "term")
        .values(status="corrected", corrected_value="five years", corrected_at=func.now())
    )
    before = (
        await session.execute(
            select(extractions).where(
                extractions.c.field_name == "term", extractions.c.contract_id == contract
            )
        )
    ).one()

    await extract_contract(session, make_gateway(session, Transport(), tmp_path), contract)

    after = (
        await session.execute(
            select(extractions).where(
                extractions.c.field_name == "term", extractions.c.contract_id == contract
            )
        )
    ).one()
    assert after == before


@pytest.mark.parametrize(
    ("replies", "message"),
    [
        (
            (httpx.ReadTimeout("slow"), httpx.ReadTimeout("slow")),
            "Extraction failed: model timed out",
        ),  # TC-0052
        (
            (httpx.Response(503), httpx.Response(503)),
            "Extraction failed: model unavailable (503)",
        ),  # TC-0053
    ],
)
async def test_two_failed_attempts_store_no_fields(
    session: AsyncSession,
    tmp_path: Path,
    replies: tuple[httpx.Response | Exception, ...],
    message: str,
) -> None:
    contract = await lease_01(session)

    with pytest.raises(GatewayFailedError) as raised:
        await extract_contract(
            session, make_gateway(session, Transport(*replies), tmp_path), contract
        )

    assert raised.value.message == message
    assert await rows(session, contract) == {}
    assert await calls(session) == 2


async def test_tc0084_two_schema_failures_hold_all_five_fields_and_both_are_paid(
    session: AsyncSession, tmp_path: Path
) -> None:
    # TASK-008, REQ-046: replaces TC-0055's "store nothing" for prompt v2.
    contract = await lease_01(session)
    bad = httpx.Response(200, json=chat_reply({"fields": "oops"}, cost=0.0135))

    result = await extract_contract(
        session, make_gateway(session, Transport(bad, bad), tmp_path), contract
    )

    stored = await rows(session, contract)
    assert sorted(stored) == sorted(FIELDS)
    assert {s[:2] for s in stored.values()} == {("needs_review", "invalid_reply")}
    assert (result.accepted, result.needs_review) == (0, 5)
    spent = await session.scalar(select(func.sum(llm_calls.c.cost_usd)))
    assert spent == Decimal("0.027000")


async def test_tc0056_a_storage_failure_leaves_no_extraction_rows(
    session: AsyncSession, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    contract = await lease_01(session)

    async def fail(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("storage failed on row 7")

    monkeypatch.setattr("app.extraction.service.repo.upsert_extractions", fail)

    with pytest.raises(RuntimeError):
        await extract_contract(
            session,
            make_gateway(session, Transport(ok(perfect_reply("lease-01"))), tmp_path),
            contract,
        )

    assert await rows(session, contract) == {}


@pytest.fixture
async def factory(session: AsyncSession) -> async_sessionmaker[AsyncSession]:
    connection = await session.connection()
    return async_sessionmaker(bind=connection, join_transaction_mode="create_savepoint")


async def test_an_unreadable_reply_is_held_and_its_spend_kept_in_the_command(
    session: AsyncSession,
    factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    await lease_01(session)
    bad = httpx.Response(200, json=chat_reply({"fields": "oops"}, cost=0.0135))
    transport = Transport(bad, bad)

    def gateway_for(ledger_session: AsyncSession) -> Gateway:
        return make_gateway(ledger_session, transport, tmp_path)

    code = await run_cli(["lease-01"], factory, gateway_for)

    assert code == 0
    assert "lease-01.pdf: 0 accepted, 5 need review" in capsys.readouterr().out
    assert await calls(session) == 2


async def test_the_command_stops_at_the_budget(
    session: AsyncSession,
    factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    await lease_01(session)
    await LlmCallLedger(session).record(
        CallRecord(
            uuid4(),
            "extract_fields",
            "v1",
            "anthropic/claude-haiku-4.5",
            "e" * 64,
            False,
            1,
            1,
            Decimal("9"),
        )
    )
    transport = Transport()

    def gateway_for(ledger_session: AsyncSession) -> Gateway:
        return make_gateway(ledger_session, transport, tmp_path)

    code = await run_cli(["lease-01"], factory, gateway_for)

    assert code == 1
    assert "LLM budget reached" in capsys.readouterr().err
    assert transport.requests == []
    assert BudgetReachedError.code == "llm_budget_reached"
