"""The gateway: one door for model calls (TASK-002 gateway design, approved 2026-10-05)."""

import json
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from pydantic import BaseModel, ConfigDict, SecretStr
from structlog.testing import capture_logs

from app.llm.cache import ReplyCache
from app.llm.gateway import (
    BudgetReachedError,
    FeatureDisabledError,
    Gateway,
    GatewayFailedError,
    InvalidReplyError,
    LLMRequest,
    MissingApiKeyError,
)
from tests.llm.fakes import InMemoryLedger, chat_reply

GOOD = {"answer": "Delaware"}
REQ = LLMRequest(
    feature="extraction",
    prompt_name="extract_fields",
    prompt_version="v1",
    system="Extract fields.",
    user="1 Governing Law\nThis Lease is governed by the laws of the State of Delaware.",
    max_tokens=2000,
)


class Answer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answer: str


class Replies:
    """A transport that returns the queued replies in order and counts requests."""

    def __init__(self, *replies: httpx.Response | Exception) -> None:
        self.queue = list(replies)
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        reply = self.queue.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


def ok(body: dict[str, object]) -> httpx.Response:
    return httpx.Response(200, json=body)


def make(
    replies: Replies,
    tmp_path: Path,
    ledger: InMemoryLedger | None = None,
    api_key: str | None = "sk-test",
) -> tuple[Gateway, InMemoryLedger]:
    led = ledger or InMemoryLedger()
    gateway = Gateway(
        client=httpx.AsyncClient(transport=httpx.MockTransport(replies)),
        cache=ReplyCache(tmp_path / "cache"),
        ledger=led,
        model="anthropic/claude-haiku-4.5",
        api_key=SecretStr(api_key) if api_key else None,
        budget_stop_usd=Decimal("9"),
        run_id=uuid4(),
    )
    return gateway, led


async def test_a_valid_reply_is_parsed_and_its_cost_recorded(tmp_path: Path) -> None:
    replies = Replies(ok(chat_reply(GOOD, cost=0.0135)))
    gateway, ledger = make(replies, tmp_path)

    result = await gateway.parse(REQ, Answer)

    assert result.value == Answer(answer="Delaware")
    assert len(replies.requests) == 1
    assert [(r.cache_hit, r.cost_usd) for r in ledger.records] == [(False, Decimal("0.0135"))]


async def test_the_request_asks_for_strict_json_schema_output_with_usage(tmp_path: Path) -> None:
    replies = Replies(ok(chat_reply(GOOD)))
    gateway, _ = make(replies, tmp_path)

    await gateway.parse(REQ, Answer)

    sent = json.loads(replies.requests[0].content)
    assert sent["model"] == "anthropic/claude-haiku-4.5"
    assert sent["response_format"]["type"] == "json_schema"
    assert sent["response_format"]["json_schema"]["strict"] is True
    assert sent["usage"] == {"include": True}
    assert replies.requests[0].headers["authorization"] == "Bearer sk-test"


async def test_tc0046_a_cached_reply_makes_no_request_and_costs_nothing(tmp_path: Path) -> None:
    first = Replies(ok(chat_reply(GOOD)))
    gateway, _ = make(first, tmp_path)
    await gateway.parse(REQ, Answer)
    again = Replies()
    gateway2, ledger2 = make(again, tmp_path)

    result = await gateway2.parse(REQ, Answer)

    assert result.value == Answer(answer="Delaware")
    assert again.requests == []
    assert [(r.cache_hit, r.cost_usd) for r in ledger2.records] == [(True, Decimal(0))]


async def test_tc0054_a_timeout_then_a_good_reply_succeeds_and_both_are_recorded(
    tmp_path: Path,
) -> None:
    replies = Replies(httpx.ReadTimeout("slow"), ok(chat_reply(GOOD)))
    gateway, ledger = make(replies, tmp_path)

    result = await gateway.parse(REQ, Answer)

    assert result.value == Answer(answer="Delaware")
    assert len(ledger.records) == 2
    assert ledger.records[0].cost_usd > 0


async def test_tc0052_two_timeouts_fail_with_a_reason(tmp_path: Path) -> None:
    replies = Replies(httpx.ReadTimeout("slow"), httpx.ReadTimeout("slow"))
    gateway, ledger = make(replies, tmp_path)

    with pytest.raises(GatewayFailedError) as raised:
        await gateway.parse(REQ, Answer)

    assert raised.value.message == "Extraction failed: model timed out"
    assert len(ledger.records) == 2


async def test_an_unreachable_model_is_retried_then_fails_with_a_reason(tmp_path: Path) -> None:
    replies = Replies(httpx.ConnectError("refused"), httpx.ConnectError("refused"))
    gateway, ledger = make(replies, tmp_path)

    with pytest.raises(GatewayFailedError) as raised:
        await gateway.parse(REQ, Answer)

    assert raised.value.message == "Extraction failed: model unreachable"
    assert [r.cost_usd > 0 for r in ledger.records] == [True, True]


async def test_tc0053_two_503_replies_fail_with_the_status(tmp_path: Path) -> None:
    replies = Replies(httpx.Response(503), httpx.Response(503))
    gateway, _ = make(replies, tmp_path)

    with pytest.raises(GatewayFailedError) as raised:
        await gateway.parse(REQ, Answer)

    assert raised.value.message == "Extraction failed: model unavailable (503)"


async def test_tc0055_two_replies_that_fail_the_schema_fail_and_both_are_paid(
    tmp_path: Path,
) -> None:
    replies = Replies(ok(chat_reply({"oops": 1})), ok(chat_reply({"oops": 1})))
    gateway, ledger = make(replies, tmp_path)

    with pytest.raises(GatewayFailedError) as raised:
        await gateway.parse(REQ, Answer)

    assert raised.value.message == "Extraction failed: reply did not match the schema"
    assert sum(r.cost_usd for r in ledger.records) == Decimal("0.0270")


async def test_tc0036_a_reply_that_fails_the_schema_is_retried_once(tmp_path: Path) -> None:
    # REQ-038: retry once on a reply that fails validation.
    replies = Replies(ok(chat_reply({"oops": 1})), ok(chat_reply(GOOD)))
    gateway, ledger = make(replies, tmp_path)

    result = await gateway.parse(REQ, Answer)

    assert result.value == Answer(answer="Delaware")
    assert len(ledger.records) == 2


async def test_a_reply_cut_off_at_max_tokens_counts_as_invalid(tmp_path: Path) -> None:
    replies = Replies(
        ok(chat_reply('{"answer": "Dela', finish_reason="length")),
        ok(chat_reply(GOOD)),
    )
    gateway, _ = make(replies, tmp_path)

    result = await gateway.parse(REQ, Answer)

    assert result.value == Answer(answer="Delaware")
    assert len(replies.requests) == 2


async def test_a_400_is_not_retried(tmp_path: Path) -> None:
    replies = Replies(httpx.Response(400, json={"error": {"message": "bad"}}))
    gateway, _ = make(replies, tmp_path)

    with pytest.raises(GatewayFailedError) as raised:
        await gateway.parse(REQ, Answer)

    assert raised.value.message == "Extraction failed: model request rejected (400)"
    assert len(replies.requests) == 1


async def test_tc0049_spend_at_the_stop_refuses_before_any_request(tmp_path: Path) -> None:
    replies = Replies()
    gateway, ledger = make(replies, tmp_path, ledger=InMemoryLedger(spent="9.000000"))

    with pytest.raises(BudgetReachedError) as raised:
        await gateway.parse(REQ, Answer)

    assert raised.value.message == "LLM budget reached"
    assert replies.requests == []
    assert ledger.records == []


async def test_tc0050_spend_just_under_the_stop_allows_the_call(tmp_path: Path) -> None:
    replies = Replies(ok(chat_reply(GOOD)))
    gateway, _ = make(replies, tmp_path, ledger=InMemoryLedger(spent="8.999999"))

    result = await gateway.parse(REQ, Answer)

    assert result.value == Answer(answer="Delaware")


async def test_the_kill_switch_refuses_before_any_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LLM_KILL_EXTRACTION", "1")
    replies = Replies()
    gateway, _ = make(replies, tmp_path)

    with pytest.raises(FeatureDisabledError):
        await gateway.parse(REQ, Answer)

    assert replies.requests == []


async def test_a_missing_key_refuses_a_live_call(tmp_path: Path) -> None:
    replies = Replies()
    gateway, _ = make(replies, tmp_path, api_key=None)

    with pytest.raises(MissingApiKeyError):
        await gateway.parse(REQ, Answer)

    assert replies.requests == []


async def test_cost_comes_from_tokens_when_openrouter_omits_it(tmp_path: Path) -> None:
    replies = Replies(ok(chat_reply(GOOD, cost=None, prompt_tokens=6000, completion_tokens=1500)))
    gateway, ledger = make(replies, tmp_path)

    await gateway.parse(REQ, Answer)

    # 6,000 x USD 1 / 1M + 1,500 x USD 5 / 1M (anthropic/claude-haiku-4.5, ADR-0002)
    assert ledger.records[0].cost_usd == Decimal("0.013500")


async def test_logs_never_carry_the_prompt_or_the_reply(tmp_path: Path) -> None:
    replies = Replies(ok(chat_reply(GOOD)))
    gateway, _ = make(replies, tmp_path)

    with capture_logs() as logs:
        await gateway.parse(REQ, Answer)

    assert "Delaware" not in json.dumps(logs, default=str)
    assert [e["event"] for e in logs] == ["llm_call"]


async def test_a_reply_with_no_usage_is_recorded_at_the_estimate_not_zero(tmp_path: Path) -> None:
    # TASK-002 review finding 2: cost 0 broke chk_llm_calls_live_call_costed.
    body = chat_reply(GOOD)
    del body["usage"]
    gateway, ledger = make(Replies(ok(body)), tmp_path)

    await gateway.parse(REQ, Answer)

    assert ledger.records[0].cost_usd > 0


@pytest.mark.parametrize(
    "reply",
    [
        httpx.Response(200, text="<html>bad gateway</html>"),
        httpx.Response(200, json={"id": "gen-test", "usage": {"cost": 0.001}}),
    ],
    ids=["not-json", "no-choices"],
)
async def test_a_malformed_200_is_retried_and_paid_then_fails_with_a_reason(
    tmp_path: Path, reply: httpx.Response
) -> None:
    # TASK-002 review finding 3: these escaped as JSONDecodeError or KeyError.
    gateway, ledger = make(Replies(reply, reply), tmp_path)

    with pytest.raises(GatewayFailedError) as raised:
        await gateway.parse(REQ, Answer)

    assert raised.value.message == "Extraction failed: reply did not match the schema"
    assert [r.cost_usd > 0 for r in ledger.records] == [True, True]


async def test_the_retry_is_refused_when_the_first_attempt_reaches_the_stop(
    tmp_path: Path,
) -> None:
    # TASK-002 review finding 7: attempt 2 ran after spend had crossed USD 9.
    replies = Replies(ok(chat_reply({"oops": 1}, cost=0.0135)))
    gateway, _ = make(replies, tmp_path, ledger=InMemoryLedger(spent="8.99"))

    with pytest.raises(BudgetReachedError):
        await gateway.parse(REQ, Answer)

    assert len(replies.requests) == 1


async def test_tc0083_two_schema_invalid_replies_raise_invalid_reply(tmp_path: Path) -> None:
    # TASK-008, REQ-046: an unreadable reply after the retry is its own error.
    replies = Replies(ok(chat_reply("not json")), ok(chat_reply("not json")))
    gateway, ledger = make(replies, tmp_path)

    with pytest.raises(InvalidReplyError):
        await gateway.parse(REQ, Answer)

    assert len(ledger.records) == 2
    assert not list((tmp_path / "cache").glob("**/*.json"))


async def test_tc0085_two_timeouts_are_not_an_invalid_reply(tmp_path: Path) -> None:
    replies = Replies(httpx.ReadTimeout("slow"), httpx.ReadTimeout("slow"))
    gateway, _ = make(replies, tmp_path)

    with pytest.raises(GatewayFailedError) as raised:
        await gateway.parse(REQ, Answer)

    assert not isinstance(raised.value, InvalidReplyError)


async def test_tc0086_invalid_then_valid_returns_the_retry_and_caches_it(tmp_path: Path) -> None:
    replies = Replies(ok(chat_reply("not json")), ok(chat_reply(GOOD)))
    gateway, _ = make(replies, tmp_path)

    first = await gateway.parse(REQ, Answer)
    again = await gateway.parse(REQ, Answer)

    assert first.value == Answer(answer="Delaware")
    assert again.cache_hit is True
