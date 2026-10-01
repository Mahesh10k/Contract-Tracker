"""The truth.json answer key shape, validated whenever a file is loaded.

Graders in TASK-003 and TASK-004 read these files; validating at load means a
hand edit that breaks the shape fails loudly instead of scoring wrong.
"""

from pathlib import Path
from typing import TypedDict

from pydantic import TypeAdapter


class TruthClause(TypedDict):
    """One clause exactly as written into the PDF."""

    number: str
    heading: str
    body: str


class TruthField(TypedDict):
    """One extracted field: its value as written, the exact quote and its clause."""

    value: str
    quote: str
    clause: str


class TruthDates(TypedDict):
    """Dates the product must compute, as ISO strings; None where there is none."""

    expiry: str
    notice_deadline: str | None
    renewal: str | None
    escalation_dates: list[str]
    payment_dates: list[str]


class Truth(TypedDict):
    """The answer key for one synthetic contract."""

    id: str
    title: str
    contract_type: str
    start: str
    term_years: int
    holdout: bool
    expected_review: list[str]
    clauses: list[TruthClause]
    fields: dict[str, TruthField]
    expected: TruthDates


TRUTH = TypeAdapter(Truth)


def load_truth(path: Path) -> Truth:
    """Read and validate one truth.json file."""
    return TRUTH.validate_json(path.read_bytes())
