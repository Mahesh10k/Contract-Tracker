"""Extract one contract's 10 fields and check each quote against its cited clause.

Three steps: `prepare` reads and renders, the gateway call writes nothing
here, and `store` writes the fields in one savepoint, so a contract has all
10 rows or none (TC-0056). The command runs the call outside any write
transaction so its spend commits on its own. A quote is
accepted only if, after normalise_for_match, it appears in the clause it
cites (REQ-014); anything else is held in needs_review with the reason.
"""

import uuid
from dataclasses import dataclass

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.core.text import normalise_for_match
from app.db.repositories import contracts as contract_repo
from app.db.repositories import extractions as repo
from app.domain.contracts import FieldRow, StoredClause
from app.extraction.schema import ExtractionReply, FieldReply, Fields
from app.llm.gateway import Gateway, LLMRequest
from app.prompts import load, render

PROMPT_NAME = "extract_fields"
PROMPT_VERSION = 1

log = structlog.get_logger()


@dataclass(frozen=True)
class ExtractionResult:
    """How many fields were accepted and how many are held for review."""

    accepted: int
    needs_review: int


@dataclass(frozen=True)
class PreparedExtraction:
    """The model request for one contract and the clauses its quotes are checked against."""

    contract_id: uuid.UUID
    request: LLMRequest
    clauses: dict[str, StoredClause]


async def extract_contract(
    session: AsyncSession, gateway: Gateway, contract_id: uuid.UUID
) -> ExtractionResult:
    """Run the extraction prompt on one stored contract and store its 10 fields."""
    prepared = await prepare(session, contract_id)
    reply = (await gateway.parse(prepared.request, ExtractionReply)).value
    return await store(session, prepared, reply, model_id=gateway.model)


async def prepare(session: AsyncSession, contract_id: uuid.UUID) -> PreparedExtraction:
    """Read the contract and render prompt v1 with its clauses. Writes nothing."""
    contract = await contract_repo.find_contract(session, contract_id)
    if contract is None:
        raise NotFoundError(f"Contract {contract_id} not found")
    stored = await contract_repo.clauses_of(session, contract_id)
    prompt = load(PROMPT_NAME, PROMPT_VERSION)
    text = "\n".join(f"{c.number} {c.heading}\n{c.body}" for c in stored)
    request = LLMRequest(
        feature="extraction",
        prompt_name=PROMPT_NAME,
        prompt_version=f"v{prompt.version}",
        system=render(prompt, {"contract_title": contract.title, "contract": text}),
        user="Return the JSON object for the contract above.",
        max_tokens=prompt.max_tokens,
    )
    return PreparedExtraction(contract_id, request, {c.number: c for c in stored})


async def store(
    session: AsyncSession, prepared: PreparedExtraction, reply: ExtractionReply, *, model_id: str
) -> ExtractionResult:
    """Check every quote and store the 10 fields in one savepoint: all rows or none."""
    if reply.injection_suspected:
        log.warning("extraction_injection_suspected", contract_id=str(prepared.contract_id))
    rows = [
        check_field(name, getattr(reply.fields, name), prepared.clauses)
        for name in Fields.model_fields
    ]
    async with session.begin_nested():
        await repo.upsert_extractions(
            session,
            prepared.contract_id,
            rows,
            prompt_version=prepared.request.prompt_version,
            model_id=model_id,
        )
    accepted = sum(1 for r in rows if r.status == "accepted")
    log.info(
        "extraction_stored",
        contract_id=str(prepared.contract_id),
        accepted=accepted,
        needs_review=len(rows) - accepted,
    )
    return ExtractionResult(accepted=accepted, needs_review=len(rows) - accepted)


def check_field(name: str, reply: FieldReply, by_number: dict[str, StoredClause]) -> FieldRow:
    """Accept a field only when its quote is non-empty and in the clause it cites."""
    clause = by_number.get(reply.clause_id or "")
    quote = normalise_for_match(reply.quote or "")
    if reply.value is None or reply.quote is None:
        status, reason = "needs_review", "value_missing"
    elif clause is None:
        status, reason = "needs_review", "clause_not_found"
    elif not quote or quote not in normalise_for_match(clause.body):
        status, reason = "needs_review", "quote_not_found"
    else:
        status, reason = "accepted", None
    return FieldRow(
        field_name=name,
        value_text=reply.value,
        quote=reply.quote,
        cited_clause_number=reply.clause_id,
        clause_id=clause.id if clause else None,
        status=status,
        review_reason=reason,
    )
