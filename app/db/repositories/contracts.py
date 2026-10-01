"""SQL for contracts and their clauses. Services own the transaction around these calls."""

import uuid

from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.tables import clauses, contracts
from app.domain.contracts import Clause, NewContract, StoredContract


async def find_by_sha256(session: AsyncSession, sha256: str) -> StoredContract | None:
    """The contract stored from a file with these bytes, if any."""
    row = (
        await session.execute(
            select(contracts.c.id, contracts.c.title).where(contracts.c.file_sha256 == sha256)
        )
    ).first()
    return StoredContract(id=row.id, title=row.title) if row else None


async def insert_contract(session: AsyncSession, contract: NewContract) -> uuid.UUID:
    """Insert one contract row and return its id."""
    result = await session.execute(
        insert(contracts)
        .values(
            title=contract.title,
            contract_type=contract.contract_type,
            source_filename=contract.source_filename,
            file_sha256=contract.file_sha256,
            full_text=contract.full_text,
            page_count=contract.page_count,
        )
        .returning(contracts.c.id)
    )
    contract_id: uuid.UUID = result.scalar_one()
    return contract_id


async def insert_clauses(
    session: AsyncSession, contract_id: uuid.UUID, found: list[Clause]
) -> None:
    """Insert the clauses of one contract, positions from 1 in document order."""
    await session.execute(
        insert(clauses),
        [
            {
                "contract_id": contract_id,
                "clause_number": c.number,
                "heading": c.heading,
                "body": c.body,
                "position": position,
            }
            for position, c in enumerate(found, start=1)
        ],
    )


async def find_clause(session: AsyncSession, contract_id: uuid.UUID, number: str) -> Clause | None:
    """Clause `number` of a contract, or None."""
    row = (
        await session.execute(
            select(clauses.c.clause_number, clauses.c.heading, clauses.c.body).where(
                clauses.c.contract_id == contract_id, clauses.c.clause_number == number
            )
        )
    ).first()
    return Clause(number=row.clause_number, heading=row.heading, body=row.body) if row else None


async def source_filename(session: AsyncSession, contract_id: uuid.UUID) -> str | None:
    """The file name a contract was loaded from, or None for an unknown id."""
    return await session.scalar(
        select(contracts.c.source_filename).where(contracts.c.id == contract_id)
    )
