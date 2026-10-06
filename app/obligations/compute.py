"""Turn extracted text into expiry and notice deadline, in code (REQ-007, ADR-0007).

The model returns dates and durations as written ("three (3) months"); this
module parses them and does the arithmetic with python-dateutil, so no date
ever comes from the LLM. Conventions match the generator (evals/contracts/dates.py):
expiry is the day before the term's anniversary; a notice period in months
moves by calendar months and clamps to the month end; in days it counts days.
Anything the parsers do not understand is reported as unparsed, never guessed.
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal

from dateutil.relativedelta import relativedelta

Unit = Literal["days", "months", "years"]
Kind = Literal["expiry", "notice_deadline"]

_ONES = [
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "eleven",
    "twelve",
    "thirteen",
    "fourteen",
    "fifteen",
    "sixteen",
    "seventeen",
    "eighteen",
    "nineteen",
]
_TENS = ["twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
_WORDS = {w: n for n, w in enumerate(_ONES)} | {w: 20 + 10 * n for n, w in enumerate(_TENS)}
_MONTHS = [
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
]

_DURATION = re.compile(
    r"^(?:not less than\s+|at least\s+)?"
    r"(?P<words>[a-z]+(?:-[a-z]+)?)?\s*(?:\((?P<paren>\d+)\))?\s*(?P<digits>\d+)?\s*"
    r"(?P<unit>days?|months?|years?)\b",
)
_DATE = re.compile(r"^(?P<day>\d{1,2})\s+(?P<month>[a-z]+)\s+(?P<year>\d{4})$")
_RELATIVE = re.compile(r"^(?P<duration>.+?)\s+after\s+(?P<anchor>.+)$")


@dataclass(frozen=True)
class Duration:
    """A whole number of days, months or years."""

    amount: int
    unit: Unit


@dataclass(frozen=True)
class FieldText:
    """One extracted field as written, with the clause its quote came from."""

    value: str
    clause: str | None


@dataclass(frozen=True)
class Obligation:
    """One dated duty and the clause it was computed from."""

    kind: Kind
    due: date
    source_field: str
    clause: str | None


@dataclass(frozen=True)
class ObligationResult:
    """The obligations computed, and the fields whose text could not be parsed."""

    obligations: list[Obligation]
    unparsed: list[str]


def _number(words: str | None, paren: str | None, digits: str | None) -> int | None:
    if paren or digits:
        return int(paren or digits or "0")
    if not words:
        return None
    if words in _WORDS:
        return _WORDS[words]
    tens, _, ones = words.partition("-")
    if tens in _TENS and ones in _ONES[1:10]:
        return _WORDS[tens] + _WORDS[ones]
    return None


def parse_duration(text: str) -> Duration | None:
    """Parse "ninety (90) days", "not less than thirty days" or "60 days"; None otherwise."""
    m = _DURATION.match(text.strip().lower())
    if m is None:
        return None
    amount = _number(m["words"], m["paren"], m["digits"])
    if not amount:
        return None
    unit = m["unit"].rstrip("s") + "s"
    return Duration(amount, "days" if unit == "days" else "months" if unit == "months" else "years")


def _shift(day: date, duration: Duration, sign: int) -> date:
    if duration.unit == "days":
        return day + sign * timedelta(days=duration.amount)
    months = duration.amount * (12 if duration.unit == "years" else 1)
    return day + relativedelta(months=sign * months)


def parse_date_text(text: str) -> date | None:
    """Parse "1 March 2026" or "two (2) months after 1 January 2026"; None otherwise."""
    lowered = text.strip().lower()
    relative = _RELATIVE.match(lowered)
    if relative:
        offset = parse_duration(relative["duration"])
        anchor = parse_date_text(relative["anchor"])
        return _shift(anchor, offset, +1) if offset and anchor else None
    m = _DATE.match(lowered)
    if m is None or m["month"] not in _MONTHS:
        return None
    try:
        return date(int(m["year"]), _MONTHS.index(m["month"]) + 1, int(m["day"]))
    except ValueError:
        return None


def expiry_of(start: date, term: Duration) -> date:
    """Last day of a term: the day before the (month-end clamped) anniversary."""
    return _shift(start, term, +1) - timedelta(days=1)


def notice_deadline(expiry: date, period: Duration) -> date:
    """Last day notice can be given: `period` before expiry."""
    return _shift(expiry, period, -1)


def compute_obligations(fields: Mapping[str, FieldText | None]) -> ObligationResult:
    """Compute expiry and notice deadline from effective_date, term and notice_period."""
    unparsed: list[str] = []
    start_text, term_text = fields.get("effective_date"), fields.get("term")
    start = parse_date_text(start_text.value) if start_text else None
    term = parse_duration(term_text.value) if term_text else None
    if start_text and start is None:
        unparsed.append("effective_date")
    if term_text and term is None:
        unparsed.append("term")
    notice_text = fields.get("notice_period")
    period = parse_duration(notice_text.value) if notice_text else None
    if notice_text and period is None:
        unparsed.append("notice_period")
    if start is None or term is None or term_text is None:
        return ObligationResult(obligations=[], unparsed=unparsed)
    expiry = expiry_of(start, term)
    found = [Obligation("expiry", expiry, "term", term_text.clause)]
    if period is not None and notice_text is not None:
        found.append(
            Obligation(
                "notice_deadline",
                notice_deadline(expiry, period),
                "notice_period",
                notice_text.clause,
            )
        )
    return ObligationResult(obligations=found, unparsed=unparsed)
