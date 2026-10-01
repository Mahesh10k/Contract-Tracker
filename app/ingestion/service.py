"""Load one contract file into Postgres as a contract and its clauses (US-00-001).

The contract and all its clauses are written in one savepoint: a clause the
database refuses rolls the whole contract back, so a contract never exists
with half its clauses (TC-0024). The caller owns the outer transaction.
"""

import hashlib
import json
import uuid
from dataclasses import dataclass
from pathlib import Path

import anyio
import structlog
from sqlalchemy import insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError, NotFoundError
from app.db.tables import clauses, contracts
from app.ingestion.pdf import read_pdf
from app.ingestion.splitter import Clause, split_clauses

CONTRACT_TYPES = ("lease", "vendor", "service")

log = structlog.get_logger()


class ContractTypeRequiredError(DomainError):
    """No truth.json beside the file and no --type given (Q-026; the picker is TASK-005)."""

    status_code = 422
    code = "contract_type_required"


class InvalidContractError(DomainError):
    """The database refused the contract or one of its clauses."""

    status_code = 422
    code = "invalid_contract"


@dataclass(frozen=True)
class IngestResult:
    """What happened to one file: stored now, or already loaded earlier."""

    contract_id: uuid.UUID
    title: str
    created: bool


async def _type_and_title(path: Path, contract_type: str | None) -> tuple[str, str]:
    """Type and title from the truth.json beside a generated contract, else from the caller."""
    truth = anyio.Path(path.with_name(f"{path.stem}.truth.json"))
    if await truth.exists():
        data = json.loads(await truth.read_text())
        kind, title = data.get("contract_type"), data.get("title")
        if kind not in CONTRACT_TYPES or not isinstance(title, str):
            raise InvalidContractError(
                f"{truth.name}: contract_type must be lease, vendor or service"
            )
        return str(kind), title
    if contract_type not in CONTRACT_TYPES:
        raise ContractTypeRequiredError("Contract type required: --type lease, vendor or service")
    return contract_type, path.stem


async def ingest_file(
    session: AsyncSession, path: Path, contract_type: str | None = None
) -> IngestResult:
    """Store `path` as a contract with its clauses, or report that it is already stored."""
    data = await anyio.Path(path).read_bytes()
    sha256 = hashlib.sha256(data).hexdigest()
    existing = (
        await session.execute(
            select(contracts.c.id, contracts.c.title).where(contracts.c.file_sha256 == sha256)
        )
    ).first()
    if existing:
        log.info("contract_already_loaded", file=path.name, contract_id=str(existing.id))
        return IngestResult(contract_id=existing.id, title=existing.title, created=False)

    kind, title = await _type_and_title(path, contract_type)
    pdf = await anyio.to_thread.run_sync(read_pdf, data)
    found = split_clauses(pdf.text)
    try:
        async with session.begin_nested():
            inserted = await session.execute(
                insert(contracts)
                .values(
                    title=title,
                    contract_type=kind,
                    source_filename=path.name,
                    file_sha256=sha256,
                    full_text=pdf.text,
                    page_count=pdf.page_count,
                )
                .returning(contracts.c.id)
            )
            contract_id: uuid.UUID = inserted.scalar_one()
            await session.execute(insert(clauses), _clause_rows(contract_id, found))
    except IntegrityError as exc:
        log.warning("contract_refused", file=path.name, reason="integrity")
        raise InvalidContractError(f"Contract could not be stored: {path.name}") from exc
    log.info("contract_loaded", file=path.name, contract_id=str(contract_id), clauses=len(found))
    return IngestResult(contract_id=contract_id, title=title, created=True)


def _clause_rows(contract_id: uuid.UUID, found: list[Clause]) -> list[dict[str, object]]:
    return [
        {
            "contract_id": contract_id,
            "clause_number": c.number,
            "heading": c.heading,
            "body": c.body,
            "position": position,
        }
        for position, c in enumerate(found, start=1)
    ]


async def get_clause(session: AsyncSession, contract_id: uuid.UUID, number: str) -> Clause:
    """Return clause `number` of a contract exactly as stored (AC-US-00-001-3)."""
    row = (
        await session.execute(
            select(clauses.c.clause_number, clauses.c.heading, clauses.c.body).where(
                clauses.c.contract_id == contract_id, clauses.c.clause_number == number
            )
        )
    ).first()
    if row is None:
        name = await session.scalar(
            select(contracts.c.source_filename).where(contracts.c.id == contract_id)
        )
        raise NotFoundError(f"Clause {number} not found in {Path(name or '').stem}")
    return Clause(number=row.clause_number, heading=row.heading, body=row.body)
