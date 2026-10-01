"""The migration pipeline produced the schema, and each test is rolled back.

Retargeted from the scaffold's schema_probe table to contracts when migration
0001 replaced the probe (review T4, TC-0022, TC-0023).
"""

import pytest
from sqlalchemy import func, insert, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.db.tables import contracts

pytestmark = pytest.mark.integration

PROBE = {
    "title": "Isolation probe",
    "contract_type": "lease",
    "source_filename": "probe.pdf",
    "file_sha256": "0" * 64,
    "full_text": "1 Parties\nA and B.",
    "page_count": 1,
}


async def test_tc0022_contracts_table_exists_and_is_empty(session: AsyncSession) -> None:
    count = await session.scalar(select(func.count()).select_from(contracts))

    assert count == 0


async def test_tc0023_a_rolled_back_insert_is_invisible_to_the_next_connection(
    engine: AsyncEngine,
) -> None:
    # Same begin-then-rollback pattern as the session fixture, in one test, so the
    # proof does not depend on test order.
    async with engine.connect() as first:
        transaction = await first.begin()
        await first.execute(insert(contracts).values(**PROBE))
        await transaction.rollback()

    async with engine.connect() as second:
        count = await second.scalar(
            select(func.count())
            .select_from(contracts)
            .where(contracts.c.title == "Isolation probe")
        )

    assert count == 0
