"""Embed clauses once, then find the clauses closest to a question.

The embedding model is CPU-bound and synchronous, so it runs in a worker thread and never
blocks the event loop.
"""

import anyio
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories import embeddings as repo
from app.retrieval.embedder import MODEL_NAME, Embedder
from app.retrieval.rank import Hit
from app.retrieval.text import embedding_text

log = structlog.get_logger()
BATCH = 32
TOP_K = 5


async def embed_missing(session: AsyncSession, embedder: Embedder) -> int:
    """Embed every clause that has no vector; a second run finds nothing and writes nothing."""
    total = 0
    while batch := await repo.clauses_missing_embedding(session, BATCH):
        texts = [
            embedding_text(c.contract_title, c.clause_number, c.heading, c.body) for c in batch
        ]
        vectors = await anyio.to_thread.run_sync(embedder.embed_documents, texts)
        await repo.set_embeddings(
            session, [(c.clause_id, v) for c, v in zip(batch, vectors, strict=True)], MODEL_NAME
        )
        total += len(batch)
    log.info("clauses_embedded", count=total, model=MODEL_NAME)
    return total


async def search(
    session: AsyncSession, embedder: Embedder, question: str, k: int = TOP_K
) -> list[Hit]:
    """The `k` clauses closest to the question, best first, each with its similarity."""
    query = await anyio.to_thread.run_sync(embedder.embed_query, question)
    return await repo.nearest(session, query, k)
