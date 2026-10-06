"""A deterministic embedder for tests: a hashed bag of words, normalised, 384 dimensions.

Texts that share words get similar vectors, which is all the tests need. It is not the real
model: real retrieval quality is measured by the Q&A eval, never by this fake.
"""

import hashlib
import math
import re
from collections.abc import Sequence

from app.retrieval.embedder import DIMENSIONS
from app.retrieval.text import QUERY_INSTRUCTION


def _vector(text: str) -> list[float]:
    vector = [0.0] * DIMENSIONS
    for word in re.findall(r"[a-z0-9]+", text.lower()):
        slot = int.from_bytes(hashlib.sha256(word.encode()).digest()[:4], "big") % DIMENSIONS
        vector[slot] += 1.0
    norm = math.sqrt(sum(x * x for x in vector)) or 1.0
    return [x / norm for x in vector]


class FakeEmbedder:
    """Records what it was asked to embed so tests can check the query form."""

    def __init__(self) -> None:
        self.documents: list[str] = []
        self.queries: list[str] = []

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        self.documents.extend(texts)
        return [_vector(t) for t in texts]

    def embed_query(self, question: str) -> list[float]:
        from app.retrieval.text import query_text

        self.queries.append(query_text(question))
        return _vector(question.removeprefix(QUERY_INSTRUCTION))
