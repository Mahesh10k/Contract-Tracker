"""SQL for contracts and their clauses. Services own the transaction around these calls."""

import uuid

from sqlalchemy import insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.tables import clauses, contracts
from app.domain.contracts import (
    Clause,
    ContractRefusedError,
    NewContract,
    StoredClause,
    StoredContract,
)


def _refused(exc: IntegrityError) -> ContractRefusedError:
    """The constraint asyncpg reports on the cause of the error, never parsed from its text."""
    name = getattr(getattr(exc.orig, "__cause__", None), "constraint_name", None)
    return ContractRefusedError(name or "unknown constraint")


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
    try:
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
    except IntegrityError as exc:
        raise _refused(exc) from exc
    contract_id: uuid.UUID = result.scalar_one()
    return contract_id


async def insert_clauses(
    session: AsyncSession, contract_id: uuid.UUID, found: list[Clause]
) -> None:
    """Insert the clauses of one contract, positions from 1 in document order."""
    try:
        await session.execute(
            insert(clauses),
            [
                {
                    "contract_id": contract_id,
                    "clause_number": c.number,
                    "heading": c.heading,
                    "body": c.body,
                    "position": position,
                    "first_page": c.first_page,
                    "last_page": c.last_page,
                }
                for position, c in enumerate(found, start=1)
            ],
        )
    except IntegrityError as exc:
        raise _refused(exc) from exc


async def find_clause(session: AsyncSession, contract_id: uuid.UUID, number: str) -> Clause | None:
    """Clause `number` of a contract, or None."""
    row = (
        await session.execute(
            select(
                clauses.c.clause_number,
                clauses.c.heading,
                clauses.c.body,
                clauses.c.first_page,
                clauses.c.last_page,
            ).where(clauses.c.contract_id == contract_id, clauses.c.clause_number == number)
        )
    ).first()
    if row is None:
        return None
    return Clause(row.clause_number, row.heading, row.body, row.first_page, row.last_page)


async def source_filename(session: AsyncSession, contract_id: uuid.UUID) -> str | None:
    """The file name a contract was loaded from, or None for an unknown id."""
    return await session.scalar(
        select(contracts.c.source_filename).where(contracts.c.id == contract_id)
    )


async def find_contract(session: AsyncSession, contract_id: uuid.UUID) -> StoredContract | None:
    """The contract's id and title, or None for an unknown id."""
    row = (
        await session.execute(
            select(contracts.c.id, contracts.c.title).where(contracts.c.id == contract_id)
        )
    ).first()
    return StoredContract(id=row.id, title=row.title) if row else None


async def find_by_source_stem(session: AsyncSession, stem: str) -> uuid.UUID | None:
    """The id of the contract loaded from `<stem>.pdf`, or None."""
    return await session.scalar(
        select(contracts.c.id).where(contracts.c.source_filename == f"{stem}.pdf")
    )


async def all_contract_ids(session: AsyncSession) -> list[uuid.UUID]:
    """Every contract id, oldest first (bounded by the synthetic set's size)."""
    result = await session.scalars(
        select(contracts.c.id).order_by(contracts.c.created_at, contracts.c.id).limit(1000)
    )
    return list(result)


async def source_name(session: AsyncSession, contract_id: uuid.UUID) -> str:
    """The file name a contract was loaded from ("" for an unknown id)."""
    return await source_filename(session, contract_id) or ""


async def clauses_of(session: AsyncSession, contract_id: uuid.UUID) -> list[StoredClause]:
    """A contract's clauses in document order."""
    result = await session.execute(
        select(clauses.c.id, clauses.c.clause_number, clauses.c.heading, clauses.c.body)
        .where(clauses.c.contract_id == contract_id)
        .order_by(clauses.c.position)
    )
    return [
        StoredClause(id=r.id, number=r.clause_number, heading=r.heading, body=r.body)
        for r in result
    ]
