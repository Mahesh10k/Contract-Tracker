"""The migration pipeline produced the schema, and each test is rolled back.

Retargeted from the scaffold's schema_probe table to contracts when migration
0001 replaced the probe (review T4, TC-0022, TC-0023).
"""

import pytest
from sqlalchemy import func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

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


async def test_tc0023_insert_is_rolled_back_between_tests_a(session: AsyncSession) -> None:
    await session.execute(insert(contracts).values(**PROBE))

    count = await session.scalar(select(func.count()).select_from(contracts))

    assert count == 1


async def test_tc0023_insert_is_rolled_back_between_tests_b(session: AsyncSession) -> None:
    count = await session.scalar(
        select(func.count()).select_from(contracts).where(contracts.c.title == "Isolation probe")
    )

    assert count == 0
