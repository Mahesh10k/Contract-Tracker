"""The golden questions: 7 answerable (one expected contract and clause each) and 3 not (REQ-056).

Loading checks every expected clause against the contract's truth.json, so a renumbered clause or
a typo fails here, not as a silently wrong score.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from evals.contracts.truth import load_truth

CONTRACTS = Path("data/contracts")


@dataclass(frozen=True)
class Expected:
    """Where the answer lives and words that prove the answer says it."""

    contract: str
    clause: str
    answer_contains_any: list[str]


@dataclass(frozen=True)
class Question:
    """One golden question; `expected` is None exactly when it is unanswerable."""

    id: str
    question: str
    answerable: bool
    expected: Expected | None


def _clause_numbers() -> dict[str, set[str]]:
    """Clause numbers per contract title, from the generator's truth files."""
    found: dict[str, set[str]] = {}
    for path in sorted(CONTRACTS.glob("*.truth.json")):
        truth = load_truth(path)
        found[truth["title"]] = {c["number"] for c in truth["clauses"]}
    return found


def load_questions(path: Path) -> list[Question]:
    """Read the golden file and refuse any expected clause the contracts do not have."""
    known = _clause_numbers()
    questions: list[Question] = []
    for raw in json.loads(path.read_text(encoding="utf-8")):
        e = raw["expected"]
        expected = (
            None
            if e is None
            else Expected(e["contract"], e["clause"], list(e["answer_contains_any"]))
        )
        if expected is not None and expected.clause not in known.get(expected.contract, set()):
            raise ValueError(
                f"{raw['id']}: {expected.contract} has no clause {expected.clause} "
                "in its truth.json"
            )
        questions.append(Question(raw["id"], raw["question"], raw["answerable"], expected))
    return questions
