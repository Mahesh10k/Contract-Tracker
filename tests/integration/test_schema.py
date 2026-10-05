"""Migration 0001 builds the schema in docs/design/schema.sql (review T3, TC-0021)."""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.integration

TABLES = {"contracts", "clauses", "extractions", "obligations", "reminders", "llm_calls"}


async def test_tc0021_the_six_tables_exist_and_the_probe_does_not(session: AsyncSession) -> None:
    rows = await session.scalars(
        text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
    )

    names = set(rows)

    assert names >= TABLES
    assert "schema_probe" not in names


async def test_tc0021_vector_extension_and_hnsw_index_exist(session: AsyncSession) -> None:
    extension = await session.scalar(
        text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
    )
    index = await session.scalar(
        text("SELECT indexdef FROM pg_indexes WHERE indexname = 'idx_clauses_embedding_hnsw'")
    )

    assert extension == "vector"
    assert index is not None
    assert "hnsw" in index


async def test_tc0089_review_reason_has_invalid_reply(session: AsyncSession) -> None:
    # TASK-008, migration 0003; its Down runs in make migrate-verify.
    values = await session.scalar(text("SELECT enum_range(NULL::review_reason)::text"))

    assert values is not None
    assert "invalid_reply" in values
