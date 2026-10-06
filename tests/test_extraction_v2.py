"""Prompt extract_fields v2: 5 fields, invalid replies held for review (US-00-010, ADR-0015)."""

from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.domain.contracts import StoredClause
from app.extraction.schema import ExtractionReplyV2, FieldReply
from app.extraction.service import (
    PROMPT_VERSION,
    check_field,
    check_fields,
    invalid_reply_rows,
)
from evals.contracts.golden import ANSWER_FIELDS, load_answer_key
from evals.contracts.truth import load_truth

KEY = load_answer_key(Path("data/answer_key.json"))
NOTICE_QUOTE = (
    "Notice to prevent renewal must be given three (3) months before the end of the term."
)


def clauses_of(contract_id: str) -> dict[str, StoredClause]:
    truth = load_truth(Path(f"data/contracts/{contract_id}.truth.json"))
    return {
        c["number"]: StoredClause(
            id=uuid4(), number=c["number"], heading=c["heading"], body=c["body"]
        )
        for c in truth["clauses"]
    }


def v2_reply_from_key(contract_id: str) -> ExtractionReplyV2:
    fields = {
        name: {"value": f["value"], "quote": f["quote"], "clause_id": f["clause"]}
        for name, f in KEY["contracts"][contract_id]["fields"].items()
    }
    return ExtractionReplyV2.model_validate(
        {"status": "ok", "reason": None, "injection_suspected": False, "fields": fields}
    )


def test_extraction_uses_prompt_v2() -> None:
    assert PROMPT_VERSION == 2


# TC-0080
def test_tc0080_a_valid_v2_reply_gives_five_accepted_rows() -> None:
    reply = v2_reply_from_key("lease-01")

    rows = check_fields(reply, clauses_of("lease-01"))

    assert [r.field_name for r in rows] == list(ANSWER_FIELDS)
    assert {r.status for r in rows} == {"accepted"}


# TC-0081
def test_tc0081_a_reply_missing_notice_period_fails_the_schema() -> None:
    fields = {n: {"value": None, "quote": None, "clause_id": None} for n in ANSWER_FIELDS[:-1]}

    with pytest.raises(ValidationError, match="notice_period"):
        ExtractionReplyV2.model_validate(
            {"status": "ok", "reason": None, "injection_suspected": False, "fields": fields}
        )


# TC-0082
def test_tc0082_a_reply_with_payment_terms_fails_the_schema() -> None:
    fields: dict[str, dict[str, str | None]] = {
        n: {"value": None, "quote": None, "clause_id": None} for n in ANSWER_FIELDS
    }
    fields["payment_terms"] = {"value": "monthly", "quote": None, "clause_id": None}

    with pytest.raises(ValidationError, match="payment_terms"):
        ExtractionReplyV2.model_validate(
            {"status": "ok", "reason": None, "injection_suspected": False, "fields": fields}
        )


# TC-0084
def test_tc0084_an_invalid_reply_holds_all_five_fields() -> None:
    rows = invalid_reply_rows()

    assert [r.field_name for r in rows] == list(ANSWER_FIELDS)
    assert {(r.status, r.review_reason) for r in rows} == {("needs_review", "invalid_reply")}
    assert {r.value_text for r in rows} == {None}


# TC-0087
def test_tc0087_notice_quote_cited_as_clause_2_3_is_accepted() -> None:
    clauses = clauses_of("vendor-07")
    reply = FieldReply(
        value="three (3) months",
        quote=NOTICE_QUOTE,
        clause_id="2.3",
    )

    row = check_field("notice_period", reply, clauses)

    assert (row.status, row.cited_clause_number, row.clause_id) == (
        "accepted",
        "2.3",
        clauses["2.3"].id,
    )


# TC-0088
def test_tc0088_the_same_quote_cited_as_clause_7_is_held() -> None:
    reply = FieldReply(
        value="three (3) months",
        quote=NOTICE_QUOTE,
        clause_id="7",
    )

    row = check_field("notice_period", reply, clauses_of("vendor-07"))

    assert (row.status, row.review_reason) == ("needs_review", "quote_not_found")


def test_no_renewal_contract_holds_auto_renewal_as_value_missing() -> None:
    rows = check_fields(v2_reply_from_key("vendor-08"), clauses_of("vendor-08"))

    held = [(r.field_name, r.review_reason) for r in rows if r.status == "needs_review"]
    assert held == [("auto_renewal", "value_missing")]
