"""What the page shows, built from domain data; no Streamlit, no database here.

Deadlines are computed on read from accepted or corrected fields with the
same compute_obligations the rest of the app uses, never stored twice and
never taken from a held field (REQ-007, AC-US-00-007-3).
"""

import uuid
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from app.domain.contracts import StoredField
from app.obligations.compute import FieldText, compute_obligations


@dataclass(frozen=True)
class DeadlineRow:
    """One dated duty on the Deadlines tab."""

    contract_title: str
    kind: str
    due: date
    clause: str | None
    days_left: int


@dataclass(frozen=True)
class Citation:
    """One [contract, clause] an answer cites, with the clause text to check it against."""

    contract_title: str
    clause_number: str
    clause_text: str


@dataclass(frozen=True)
class AnswerView:
    """An answer and its citations, or the refusal."""

    text: str
    citations: list[Citation]
    refused: bool


def deadlines_from(fields: Sequence[StoredField], today: date) -> list[DeadlineRow]:
    """Expiry and notice deadline per contract, soonest first."""
    by_contract: dict[uuid.UUID, list[StoredField]] = defaultdict(list)
    for f in fields:
        if f.status in ("accepted", "corrected") and f.value is not None:
            by_contract[f.contract_id].append(f)
    rows: list[DeadlineRow] = []
    for contract_fields in by_contract.values():
        texts = {f.field_name: FieldText(f.value or "", f.clause_number) for f in contract_fields}
        title = contract_fields[0].contract_title
        rows.extend(
            DeadlineRow(title, o.kind, o.due, o.clause, (o.due - today).days)
            for o in compute_obligations(texts).obligations
        )
    return sorted(rows, key=lambda r: (r.due, r.contract_title, r.kind))
