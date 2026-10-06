"""SQL for clause vectors. The service owns the transaction around these calls.

`<=>` is pgvector's cosine distance, so similarity is `1 - distance`: 1.0 for the same direction,
0.0 for unrelated text. The HNSW index (vector_cosine_ops) serves the ordered scan; at a few
hundred clauses Postgres may scan sequentially, which returns the same rows.
"""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.retrieval.rank import Candidate, Hit

# Candidates examined by the index scan; set per query here, never once by hand in psql.
EF_SEARCH = 100


@dataclass(frozen=True)
class ClauseToEmbed:
    """A clause whose vector is missing, with the context its embedding text needs."""

    clause_id: uuid.UUID
    contract_title: str
    clause_number: str
    heading: str
    body: str


def vector_literal(vector: Sequence[float]) -> str:
    """pgvector's text form: [0.1,0.2,...]."""
    return "[" + ",".join(repr(float(x)) for x in vector) + "]"


def parse_vector(literal: str) -> list[float]:
    """The inverse of vector_literal."""
    return [float(x) for x in literal.strip("[]").split(",")]


async def clauses_missing_embedding(session: AsyncSession, limit: int) -> list[ClauseToEmbed]:
    """Clauses with no vector yet, in contract and document order (bounded by `limit`)."""
    result = await session.execute(
        text(
            "SELECT c.id, ct.title, c.clause_number, c.heading, c.body "
            "FROM clauses c JOIN contracts ct ON ct.id = c.contract_id "
            "WHERE c.embedding IS NULL ORDER BY ct.title, c.position LIMIT :limit"
        ),
        {"limit": limit},
    )
    return [ClauseToEmbed(r.id, r.title, r.clause_number, r.heading, r.body) for r in result]


async def set_embeddings(
    session: AsyncSession,
    vectors: Sequence[tuple[uuid.UUID, Sequence[float]]],
    model_name: str,
) -> None:
    """Store each clause's vector with the model that made it (chk_clauses_embedding_with_model)."""
    await session.execute(
        text(
            "UPDATE clauses SET embedding = CAST(:vec AS vector), embedding_model = :model, "
            "updated_at = now() WHERE id = :id"
        ),
        [{"id": cid, "vec": vector_literal(v), "model": model_name} for cid, v in vectors],
    )


async def nearest(session: AsyncSession, query: Sequence[float], k: int) -> list[Hit]:
    """The `k` embedded clauses closest to `query` by cosine, best first, with similarity."""
    await session.execute(text(f"SET LOCAL hnsw.ef_search = {EF_SEARCH}"))
    result = await session.execute(
        text(
            "SELECT ct.title, c.clause_number, c.heading, c.body, "
            "1 - (c.embedding <=> CAST(:vec AS vector)) AS score "
            "FROM clauses c JOIN contracts ct ON ct.id = c.contract_id "
            "WHERE c.embedding IS NOT NULL "
            "ORDER BY c.embedding <=> CAST(:vec AS vector), ct.title, c.position LIMIT :k"
        ),
        {"vec": vector_literal(query), "k": k},
    )
    return [Hit(r.title, r.clause_number, r.heading, r.body, float(r.score)) for r in result]


async def all_embedded(session: AsyncSession, limit: int = 5000) -> list[Candidate]:
    """Every embedded clause with its vector, for ranking in memory (tests and comparisons)."""
    result = await session.execute(
        text(
            "SELECT ct.title, c.clause_number, c.heading, c.body, c.embedding::text AS vec "
            "FROM clauses c JOIN contracts ct ON ct.id = c.contract_id "
            "WHERE c.embedding IS NOT NULL ORDER BY ct.title, c.position LIMIT :limit"
        ),
        {"limit": limit},
    )
    return [
        Candidate(r.title, r.clause_number, r.heading, r.body, parse_vector(r.vec)) for r in result
    ]
