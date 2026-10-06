"""Extraction eval graders and gate (US-02-001, TC-0105 to TC-0112, TC-0114)."""

import copy
import json
import re
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from pydantic import SecretStr

from app.domain.contracts import StoredClause
from app.extraction.schema import FieldReply
from evals.contracts.golden import ANSWER_FIELDS, AnswerKey, load_answer_key
from evals.contracts.truth import load_truth
from evals.extraction.graders import (
    Thresholds,
    gate,
    grade_field,
    quote_grounded,
    score,
)
from evals.extraction.run import run
from tests.llm.fakes import chat_reply

KEY = load_answer_key(Path("data/answer_key.json"))
ALLOW_ONE = Thresholds(allowed_misses=dict.fromkeys(ANSWER_FIELDS, 1), grounding_min=0.95)


def replies_from(key: AnswerKey) -> dict[str, dict[str, FieldReply]]:
    return {
        cid: {
            name: FieldReply(value=f["value"], quote=f["quote"], clause_id=f["clause"])
            for name, f in entry["fields"].items()
        }
        for cid, entry in key["contracts"].items()
    }


def all_null() -> dict[str, dict[str, FieldReply]]:
    empty = FieldReply(value=None, quote=None, clause_id=None)
    return {cid: dict.fromkeys(ANSWER_FIELDS, empty) for cid in KEY["contracts"]}


# TC-0105
def test_tc0105_the_key_graded_against_itself_scores_full() -> None:
    result = score(KEY, replies_from(KEY))

    assert {name: (s.correct, s.total) for name, s in result.fields.items()} == dict.fromkeys(
        ANSWER_FIELDS, (6, 6)
    )


# TC-0106
def test_tc0106_all_null_output_scores_only_the_expected_null() -> None:
    result = score(KEY, all_null())

    correct = {name: s.correct for name, s in result.fields.items()}
    assert correct == {
        "parties": 0,
        "effective_date": 0,
        "term": 0,
        "auto_renewal": 1,
        "notice_period": 0,
    }


@pytest.mark.parametrize(
    ("field", "expected", "got", "verdict"),
    [
        ("notice_period", "ninety (90) days", "ninety days", True),
        ("notice_period", "ninety (90) days", "three (3) months", False),
        ("effective_date", "1 January 2025", "1 January 2025.", True),
        ("effective_date", "1 January 2025", "1 February 2025", False),
        ("auto_renewal", "does not renew automatically", "This Lease does not renew.", True),
        ("auto_renewal", "does not renew automatically", "renews for one-year terms", False),
        ("parties", "A Ltd and B Inc", "B Inc and A Ltd", True),
        ("parties", "A Ltd and B Inc", "A Ltd", False),
        ("term", "two (2) years", None, False),
        ("auto_renewal", None, None, True),
        ("auto_renewal", None, "renews automatically", False),
    ],
)
# TC-0107
def test_tc0107_graders_compare_meaning_not_wording(
    field: str, expected: str | None, got: str | None, verdict: bool
) -> None:
    assert grade_field(field, expected, got) is verdict


# TC-0108
def test_tc0108_two_misses_over_one_allowed_fails_naming_the_field() -> None:
    replies = replies_from(KEY)
    wrong = FieldReply(value="seven (7) days", quote=None, clause_id=None)
    replies["lease-01"]["notice_period"] = wrong
    replies["lease-04"]["notice_period"] = wrong

    ok, messages = gate(score(KEY, replies), ALLOW_ONE)

    assert ok is False
    assert "notice_period 4/6 over allowed misses 1" in messages


# TC-0109
def test_tc0109_exactly_the_allowed_misses_passes() -> None:
    replies = replies_from(KEY)
    replies["lease-01"]["notice_period"] = FieldReply(
        value="seven (7) days", quote=None, clause_id=None
    )

    ok, messages = gate(score(KEY, replies), ALLOW_ONE)

    assert ok is True
    assert not [m for m in messages if "over allowed" in m]


# TC-0110
def test_tc0110_a_fabricated_quote_is_ungrounded() -> None:
    truth = load_truth(Path("data/contracts/lease-01.truth.json"))
    clauses = {
        c["number"]: StoredClause(uuid4(), c["number"], c["heading"], c["body"])
        for c in truth["clauses"]
    }

    real = quote_grounded("The term commences on 1 January 2025.", "2.1", clauses)
    made_up = quote_grounded("The rent is free forever.", "3", clauses)

    assert (real, made_up) == (True, False)


# TC-0111
def test_tc0111_one_changed_key_value_lowers_that_field_by_one() -> None:
    flipped = copy.deepcopy(KEY)
    flipped["contracts"]["lease-01"]["fields"]["term"]["value"] = "five (5) years"

    result = score(flipped, replies_from(KEY))

    assert (result.fields["term"].correct, result.fields["parties"].correct) == (5, 6)


# TC-0112
def test_tc0112_zero_cases_fail() -> None:
    empty: AnswerKey = {"contracts": {}}

    ok, messages = gate(score(empty, {}), ALLOW_ONE)

    assert ok is False
    assert "0 cases" in messages


# TC-0114
async def test_tc0114_offline_cache_miss_fails_naming_contracts(tmp_path: Path) -> None:
    sent: list[httpx.Request] = []

    def refuse(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return httpx.Response(500)

    client = httpx.AsyncClient(transport=httpx.MockTransport(refuse))

    code, lines = await run(client=client, cache_dir=tmp_path / "empty-cache", api_key=None)

    assert code == 1
    assert any(line.startswith("cache miss: lease-01") for line in lines)
    assert sent == []


# TC-0113
async def test_tc0113_a_live_pass_fills_the_cache_and_an_offline_replay_prints_the_same_scores(
    tmp_path: Path,
) -> None:
    by_title = {entry["title"]: cid for cid, entry in KEY["contracts"].items()}

    def live(request: httpx.Request) -> httpx.Response:
        system = json.loads(request.content)["messages"][0]["content"]
        title = system.split("<contract_title>\n", 1)[1].split("\n</contract_title>", 1)[0]
        fields = {
            name: {"value": f["value"], "quote": f["quote"], "clause_id": f["clause"]}
            for name, f in KEY["contracts"][by_title[title]]["fields"].items()
        }
        reply = {"status": "ok", "reason": None, "injection_suspected": False, "fields": fields}
        return httpx.Response(200, json=chat_reply(reply, cost=0.0034))

    cache = tmp_path / "replies"
    async with httpx.AsyncClient(transport=httpx.MockTransport(live)) as client:
        live_code, live_lines = await run(
            client=client, cache_dir=cache, api_key=SecretStr("sk-test")
        )
    refused: list[httpx.Request] = []

    def refuse(request: httpx.Request) -> httpx.Response:
        refused.append(request)
        return httpx.Response(599)

    async with httpx.AsyncClient(transport=httpx.MockTransport(refuse)) as client:
        offline_code, offline_lines = await run(client=client, cache_dir=cache, api_key=None)

    scores = re.compile(
        r"^(parties|effective_date|term|auto_renewal|notice_period|grounding|deadlines) "
    )
    assert (live_code, offline_code) == (0, 0)
    assert refused == []
    assert [line for line in offline_lines if scores.match(line)] == [
        line for line in live_lines if scores.match(line)
    ]
    assert "parties 6/6" in offline_lines
