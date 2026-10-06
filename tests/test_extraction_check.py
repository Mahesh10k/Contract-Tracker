"""check_field: a field is accepted only when its quote is in the clause it cites (REQ-014)."""

from uuid import uuid4

import pytest

from app.domain.contracts import StoredClause
from app.extraction.schema import FieldReply
from app.extraction.service import check_field

NOTICE = StoredClause(
    id=uuid4(),
    number="2.3",
    heading="Notice",
    body="Either party may end this Lease by giving ninety (90) days written\nnotice.",
)
CLAUSES = {"2.3": NOTICE}


def test_a_quote_inside_its_clause_is_accepted_with_the_clause_id() -> None:
    reply = FieldReply(
        value="ninety (90) days", quote="ninety (90) days written notice", clause_id="2.3"
    )

    row = check_field("notice_period", reply, CLAUSES)

    assert (row.status, row.review_reason, row.clause_id) == ("accepted", None, NOTICE.id)


# TC-0037
def test_tc0037_a_null_value_is_held_as_value_missing() -> None:
    reply = FieldReply(value=None, quote=None, clause_id=None)

    row = check_field("escalation", reply, CLAUSES)

    assert (row.status, row.review_reason, row.clause_id) == ("needs_review", "value_missing", None)


def test_a_value_without_a_quote_is_held_as_value_missing() -> None:
    reply = FieldReply(value="ninety (90) days", quote=None, clause_id="2.3")

    row = check_field("notice_period", reply, CLAUSES)

    assert row.review_reason == "value_missing"


# TC-0039
def test_tc0039_an_unknown_clause_number_is_held_and_kept_as_cited() -> None:
    reply = FieldReply(value="Delaware", quote="laws of Delaware", clause_id="99.1")

    row = check_field("governing_law", reply, CLAUSES)

    assert (row.review_reason, row.cited_clause_number, row.clause_id) == (
        "clause_not_found",
        "99.1",
        None,
    )


# TC-0044
def test_tc0044_a_quote_not_in_the_clause_is_held_but_keeps_the_clause_id() -> None:
    reply = FieldReply(
        value="thirty days", quote="giving thirty (30) days written notice", clause_id="2.3"
    )

    row = check_field("notice_period", reply, CLAUSES)

    assert (row.status, row.review_reason, row.clause_id) == (
        "needs_review",
        "quote_not_found",
        NOTICE.id,
    )


@pytest.mark.parametrize("quote", ["", "   ", "\n"])
def test_an_empty_quote_is_not_grounding(quote: str) -> None:
    # TASK-002 review finding 1: "" is a substring of every clause, so it was accepted.
    reply = FieldReply(value="thirty (30) days", quote=quote, clause_id="2.3")

    row = check_field("notice_period", reply, CLAUSES)

    assert (row.status, row.review_reason) == ("needs_review", "quote_not_found")
