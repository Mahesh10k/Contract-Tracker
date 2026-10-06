"""Dates computed in code from extracted text (US-00-003, ADR-0007, TC-0091 to TC-0102)."""

from datetime import date
from pathlib import Path

import pytest

from app.obligations.compute import (
    Duration,
    FieldText,
    compute_obligations,
    expiry_of,
    notice_deadline,
    parse_date_text,
    parse_duration,
)
from evals.contracts.golden import GOLDEN_IDS, AnswerEntry, load_answer_key

KEY = load_answer_key(Path("data/answer_key.json"))


def fields_of(entry: AnswerEntry) -> dict[str, FieldText | None]:
    return {
        name: None if f["value"] is None else FieldText(value=f["value"], clause=f["clause"])
        for name, f in entry["fields"].items()
    }


# TC-0091
def test_tc0091_expiry_is_the_day_before_the_anniversary() -> None:
    start = parse_date_text("1 March 2026")
    term = parse_duration("three (3) years")

    assert start is not None
    assert term is not None
    assert expiry_of(start, term) == date(2029, 2, 28)


# TC-0092
def test_tc0092_term_from_29_february_uses_the_clamped_anniversary() -> None:
    start = parse_date_text("29 February 2024")
    term = parse_duration("one (1) year")

    assert start is not None
    assert term is not None
    assert expiry_of(start, term) == date(2025, 2, 27)


# TC-0093
def test_tc0093_unreadable_effective_date_is_not_guessed() -> None:
    fields = {
        "effective_date": FieldText("sometime next spring", "2.1"),
        "term": FieldText("two (2) years", "2.2"),
        "notice_period": FieldText("sixty (60) days", "7"),
    }

    result = compute_obligations(fields)

    assert result.unparsed == ["effective_date"]
    assert result.obligations == []


# TC-0094
def test_tc0094_ninety_days_prior_to_expiry() -> None:
    duration = parse_duration("ninety (90) days prior to expiry")

    assert duration == Duration(90, "days")
    assert notice_deadline(date(2029, 2, 28), duration) == date(2028, 11, 30)


# TC-0095
def test_tc0095_not_less_than_thirty_days_is_thirty_days() -> None:
    assert parse_duration("not less than thirty days") == Duration(30, "days")


# TC-0096
def test_tc0096_months_before_a_month_end_clamp() -> None:
    duration = parse_duration("three (3) months")

    assert duration == Duration(3, "months")
    assert notice_deadline(date(2027, 5, 31), duration) == date(2027, 2, 28)


# TC-0097
def test_tc0097_months_and_days_give_different_deadlines() -> None:
    months = parse_duration("three (3) months")
    days = parse_duration("ninety (90) days")

    assert months is not None
    assert days is not None
    assert notice_deadline(date(2027, 2, 28), months) == date(2026, 11, 28)
    assert notice_deadline(date(2027, 2, 28), days) == date(2026, 11, 30)


# TC-0098
def test_tc0098_unparseable_notice_is_held_but_expiry_is_kept() -> None:
    fields = {
        "effective_date": FieldText("1 January 2025", "2.1"),
        "term": FieldText("two (2) years", "2.2"),
        "notice_period": FieldText("upon completion of phase two of the works", "7"),
    }

    result = compute_obligations(fields)

    assert result.unparsed == ["notice_period"]
    assert [(o.kind, o.due) for o in result.obligations] == [("expiry", date(2026, 12, 31))]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("60 days", Duration(60, "days")),
        ("one (1) month", Duration(1, "months")),
        ("forty-five days", Duration(45, "days")),
        ("zero (0) days", None),
        ("", None),
        ("a reasonable time", None),
    ],
)
# TC-0099
def test_tc0099_duration_boundaries(text: str, expected: Duration | None) -> None:
    assert parse_duration(text) == expected


# TC-0100
def test_tc0100_lease_01_has_expiry_and_notice_with_clauses() -> None:
    result = compute_obligations(fields_of(KEY["contracts"]["lease-01"]))

    assert [(o.kind, o.due, o.clause) for o in result.obligations] == [
        ("expiry", date(2026, 12, 31), "2.2"),
        ("notice_deadline", date(2026, 12, 1), "7"),
    ]


# TC-0101
def test_tc0101_notice_elsewhere_deadline_cites_clause_2_3() -> None:
    result = compute_obligations(fields_of(KEY["contracts"]["vendor-07"]))

    notice = result.obligations[1]

    assert (notice.kind, notice.due, notice.clause) == ("notice_deadline", date(2027, 5, 31), "2.3")


@pytest.mark.parametrize("contract_id", GOLDEN_IDS)
# TC-0102
def test_tc0102_golden_dates_equal_the_answer_key(contract_id: str) -> None:
    entry = KEY["contracts"][contract_id]

    result = compute_obligations(fields_of(entry))

    got = {o.kind: o.due.isoformat() for o in result.obligations}
    assert got == {
        "expiry": entry["expected"]["expiry"],
        "notice_deadline": entry["expected"]["notice_deadline"],
    }


def test_relative_effective_date_counts_from_its_anchor() -> None:
    assert parse_date_text("two (2) months after 1 January 2026") == date(2026, 3, 1)


@pytest.mark.parametrize("text", ["31 February 2026", "1 Smarch 2026", "2026-03-01", ""])
def test_invalid_date_text_is_not_parsed(text: str) -> None:
    assert parse_date_text(text) is None
