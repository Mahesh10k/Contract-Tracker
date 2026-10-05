"""Deterministic graders for the extraction eval (US-02-001, REQ-024, REQ-057).

A field is graded on what it decides, not on its wording: dates and durations
are compared after the same parsers the app uses (app/obligations/compute.py),
auto_renewal as renews or not, parties as a set of names. Grounding counts
every quote the model returned, before any routing to review (Q-015), so it
cannot read 100 percent by construction.
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass, field

from app.core.text import normalise_for_match
from app.domain.contracts import StoredClause
from app.extraction.schema import FieldReply
from app.obligations.compute import FieldText, compute_obligations, parse_date_text, parse_duration
from evals.contracts.golden import ANSWER_FIELDS, AnswerKey

_NOT_RENEW = re.compile(
    r"\b(does not|do not|will not|shall not|not) renew|\bno (automatic )?renewal"
)


@dataclass(frozen=True)
class Thresholds:
    """Allowed misses per field and the minimum grounded share of returned quotes."""

    allowed_misses: dict[str, int]
    grounding_min: float


@dataclass
class FieldScore:
    """Correct over total for one field across the golden contracts."""

    correct: int = 0
    total: int = 0


@dataclass
class Score:
    """Everything one eval run measured."""

    cases: int = 0
    fields: dict[str, FieldScore] = field(
        default_factory=lambda: {name: FieldScore() for name in ANSWER_FIELDS}
    )
    grounded: int = 0
    quotes: int = 0
    deadlines_correct: int = 0
    deadlines_total: int = 0
    misses: list[str] = field(default_factory=list)


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.casefold()).strip(" .,;:")


def _renews(text: str) -> bool:
    lowered = _norm(text)
    return "renew" in lowered and _NOT_RENEW.search(lowered) is None


def _parties(text: str) -> frozenset[str]:
    return frozenset(_norm(p) for p in re.split(r"\s+and\s+|,\s*", text) if _norm(p))


def grade_field(name: str, expected: str | None, got: str | None) -> bool:
    """True when `got` means the same as `expected` for this field."""
    if expected is None or got is None:
        return expected is None and got is None
    if name == "effective_date":
        want = parse_date_text(expected)
        return want is not None and want == parse_date_text(_norm(got))
    if name in ("term", "notice_period"):
        wanted = parse_duration(expected)
        return wanted is not None and wanted == parse_duration(_norm(got))
    if name == "auto_renewal":
        return _renews(expected) == _renews(got)
    if name == "parties":
        return _parties(expected) == _parties(got)
    return _norm(expected) == _norm(got)


def quote_grounded(quote: str, clause_id: str | None, clauses: Mapping[str, StoredClause]) -> bool:
    """True when the quote appears, normalised, in the clause it cites."""
    clause = clauses.get(clause_id or "")
    needle = normalise_for_match(quote)
    return clause is not None and bool(needle) and needle in normalise_for_match(clause.body)


def _deadlines(replies: Mapping[str, FieldReply]) -> dict[str, str]:
    texts = {
        name: FieldText(r.value, r.clause_id) for name, r in replies.items() if r.value is not None
    }
    return {o.kind: o.due.isoformat() for o in compute_obligations(texts).obligations}


def score(
    key: AnswerKey,
    replies: Mapping[str, Mapping[str, FieldReply]],
    clauses: Mapping[str, Mapping[str, StoredClause]] | None = None,
) -> Score:
    """Grade every golden contract that has a reply; quotes are checked when clauses are given."""
    result = Score()
    for cid, entry in key["contracts"].items():
        reply = replies.get(cid)
        if reply is None:
            continue
        result.cases += 1
        for name in ANSWER_FIELDS:
            got = reply[name]
            ok = grade_field(name, entry["fields"][name]["value"], got.value)
            result.fields[name].total += 1
            result.fields[name].correct += ok
            if not ok:
                result.misses.append(
                    f"{cid} {name}: expected {entry['fields'][name]['value']!r}, got {got.value!r}"
                )
            if clauses is not None and got.quote is not None:
                result.quotes += 1
                result.grounded += quote_grounded(got.quote, got.clause_id, clauses[cid])
        computed = _deadlines(reply)
        for kind in ("expiry", "notice_deadline"):
            want = entry["expected"][kind]
            if want is not None:
                result.deadlines_total += 1
                result.deadlines_correct += computed.get(kind) == want
    return result


def gate(result: Score, limits: Thresholds) -> tuple[bool, list[str]]:
    """Report lines and whether every field and grounding is within its limit."""
    if result.cases == 0:
        return False, ["0 cases"]
    ok, lines = True, []
    for name, s in result.fields.items():
        missed = s.total - s.correct
        allowed = limits.allowed_misses.get(name, 0)
        line = f"{name} {s.correct}/{s.total}"
        if missed > allowed:
            ok = False
            line += f" over allowed misses {allowed}"
        lines.append(line)
    if result.quotes:
        share = result.grounded / result.quotes
        line = f"grounding {result.grounded}/{result.quotes}"
        if share < limits.grounding_min:
            ok = False
            line += f" under {limits.grounding_min:.0%}"
        lines.append(line)
    lines.append(f"deadlines {result.deadlines_correct}/{result.deadlines_total}")
    return ok, lines
