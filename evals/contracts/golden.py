"""The 6-contract golden set and its answer key, data/answer_key.json (US-02-006).

The one-day brief (2026-10-05) scores extraction on 6 contracts, two of each
type, including the notice-elsewhere and no-renewal hard cases. The key is
built from the truth.json files the generator already writes (Q-035), so the
generator stays the single source of truth; holdout contracts are never picked.
"""

import json
from pathlib import Path
from typing import TypedDict

from pydantic import TypeAdapter

from evals.contracts.truth import Truth, load_truth

GOLDEN_IDS: tuple[str, ...] = (
    "lease-01",
    "lease-04",
    "vendor-07",
    "vendor-08",
    "service-01",
    "service-04",
)
# The 5 fields of REQ-045, in prompt extract_fields v2 order.
ANSWER_FIELDS: tuple[str, ...] = (
    "parties",
    "effective_date",
    "term",
    "auto_renewal",
    "notice_period",
)


class AnswerField(TypedDict):
    """Expected value, quote and clause; all None when the contract has no such clause."""

    value: str | None
    quote: str | None
    clause: str | None


class AnswerDates(TypedDict):
    """The two dates code must compute (REQ-008, REQ-009), as ISO strings."""

    expiry: str
    notice_deadline: str | None


class AnswerEntry(TypedDict):
    """The answer key for one golden contract."""

    title: str
    contract_type: str
    hard_case: str | None
    fields: dict[str, AnswerField]
    expected: AnswerDates


class AnswerKey(TypedDict):
    """data/answer_key.json: golden contract id to its expected answers."""

    contracts: dict[str, AnswerEntry]


ANSWER_KEY = TypeAdapter(AnswerKey)
_ABSENT: AnswerField = {"value": None, "quote": None, "clause": None}


def _entry(truth: Truth) -> AnswerEntry:
    fields: dict[str, AnswerField] = {}
    for name in ANSWER_FIELDS:
        found = truth["fields"].get(name)
        fields[name] = (
            {"value": found["value"], "quote": found["quote"], "clause": found["clause"]}
            if found
            else _ABSENT
        )
    return {
        "title": truth["title"],
        "contract_type": truth["contract_type"],
        "hard_case": truth.get("hard_case"),
        "fields": fields,
        "expected": {
            "expiry": truth["expected"]["expiry"],
            "notice_deadline": truth["expected"]["notice_deadline"],
        },
    }


def build_answer_key(truths: dict[str, Truth], ids: tuple[str, ...]) -> AnswerKey:
    """Build the key for `ids`; an id with no truth is a ValueError naming it."""
    missing = [cid for cid in ids if cid not in truths]
    if missing:
        raise ValueError(f"golden contract without truth.json: {', '.join(missing)}")
    return {"contracts": {cid: _entry(truths[cid]) for cid in ids}}


def write_answer_key(
    contracts_dir: Path, target: Path, ids: tuple[str, ...] = GOLDEN_IDS
) -> AnswerKey:
    """Read the golden truth.json files in `contracts_dir` and write the key to `target`."""
    truths = {
        cid: load_truth(path)
        for cid in ids
        if (path := contracts_dir / f"{cid}.truth.json").exists()
    }
    key = build_answer_key(truths, ids)
    target.write_text(json.dumps(key, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return key


def load_answer_key(path: Path) -> AnswerKey:
    """Read and validate data/answer_key.json."""
    return ANSWER_KEY.validate_json(path.read_bytes())
