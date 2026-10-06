"""Cosine ranking of clause vectors, in memory.

The app asks pgvector for the same thing (`<=>` is cosine distance); the offline eval uses this
function so `make check` needs no database. An integration test pins the two to the same order
and score (TC-0140). Score is cosine similarity: 1.0 identical direction, 0.0 unrelated.
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class Candidate:
    """A clause with its vector, as the ranker receives it."""

    contract_title: str
    clause_number: str
    heading: str
    body: str
    vector: Sequence[float]


@dataclass(frozen=True)
class Hit:
    """A retrieved clause and how close it is to the question."""

    contract_title: str
    clause_number: str
    heading: str
    body: str
    score: float


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    """Cosine similarity; a zero vector is similar to nothing."""
    if len(a) != len(b):
        raise ValueError(f"vector dimension mismatch: {len(a)} against {len(b)}")
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    if norm == 0.0:
        return 0.0
    return sum(x * y for x, y in zip(a, b, strict=True)) / norm


def rank(query: Sequence[float], clauses: Sequence[Candidate], k: int) -> list[Hit]:
    """The `k` clauses most similar to `query`, best first; ties keep document order."""
    scored = [
        Hit(c.contract_title, c.clause_number, c.heading, c.body, cosine(query, c.vector))
        for c in clauses
    ]
    return sorted(scored, key=lambda h: -h.score)[:k]
