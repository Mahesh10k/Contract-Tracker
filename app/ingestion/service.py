"""Load one contract file into Postgres as a contract and its clauses (US-00-001).

The contract and all its clauses are written in one savepoint: a clause the
database refuses rolls the whole contract back, so a contract never exists
with half its clauses (TC-0024). The caller owns the outer transaction.
"""

import hashlib
import json
import re
import uuid
from dataclasses import dataclass
from pathlib import Path

import anyio
import structlog
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError, NotFoundError
from app.db.repositories import contracts as repo
from app.domain.contracts import Clause, NewContract
from app.ingestion.pdf import read_pdf
from app.ingestion.splitter import split_clauses

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


class NoClausesError(DomainError):
    """The PDF has text but no numbered clause the splitter recognises."""

    status_code = 422
    code = "no_clauses"


class FileMissingError(DomainError):
    """The path given to the loader does not exist."""

    status_code = 404
    code = "file_missing"


CONSTRAINT = re.compile(r'constraint "([^"]+)"')


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
        try:
            data = json.loads(await truth.read_text())
        except ValueError as exc:
            raise InvalidContractError(f"{truth.name}: not valid JSON") from exc
        if not isinstance(data, dict):
            raise InvalidContractError(f"{truth.name}: not valid JSON")
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
    try:
        data = await anyio.Path(path).read_bytes()
    except FileNotFoundError as exc:
        raise FileMissingError(f"File not found: {path.name}") from exc
    sha256 = hashlib.sha256(data).hexdigest()
    existing = await repo.find_by_sha256(session, sha256)
    if existing:
        log.info("contract_already_loaded", file=path.name, contract_id=str(existing.id))
        return IngestResult(contract_id=existing.id, title=existing.title, created=False)

    kind, title = await _type_and_title(path, contract_type)
    pdf = await anyio.to_thread.run_sync(read_pdf, data)
    found = split_clauses(pdf.text)
    if not found:
        raise NoClausesError(f"No numbered clauses found in {path.name}")
    try:
        async with session.begin_nested():
            contract_id = await repo.insert_contract(
                session,
                NewContract(
                    title=title,
                    contract_type=kind,
                    source_filename=path.name,
                    file_sha256=sha256,
                    full_text=pdf.text,
                    page_count=pdf.page_count,
                ),
            )
            await repo.insert_clauses(session, contract_id, found)
    except IntegrityError as exc:
        match = CONSTRAINT.search(str(exc.orig))
        constraint = match[1] if match else "unknown constraint"
        log.warning("contract_refused", file=path.name, constraint=constraint)
        raise InvalidContractError(
            f"Contract could not be stored: {path.name} ({constraint})"
        ) from exc
    log.info("contract_loaded", file=path.name, contract_id=str(contract_id), clauses=len(found))
    return IngestResult(contract_id=contract_id, title=title, created=True)


async def get_clause(session: AsyncSession, contract_id: uuid.UUID, number: str) -> Clause:
    """Return clause `number` of a contract exactly as stored (AC-US-00-001-3)."""
    clause = await repo.find_clause(session, contract_id, number)
    if clause is None:
        name = await repo.source_filename(session, contract_id)
        raise NotFoundError(f"Clause {number} not found in {Path(name or '').stem}")
    return clause
