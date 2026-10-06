"""Extract one contract's fields and check each quote against its cited clause.

Prompt v2 (ADR-0015) asks for the 5 fields of REQ-045; v1's 10-field reply
schema stays for the record. A reply that is still invalid after the
gateway's one retry stores every field as needs_review with reason
invalid_reply (REQ-046), so the contract is held, never dropped.

Three steps: `prepare` reads and renders, the gateway call writes nothing
here, and `store` writes the fields in one savepoint, so a contract has all
10 rows or none (TC-0056). The command runs the call outside any write
transaction so its spend commits on its own. A quote is
accepted only if, after normalise_for_match, it appears in the clause it
cites (REQ-014); anything else is held in needs_review with the reason.
"""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.core.text import normalise_for_match
from app.db.repositories import contracts as contract_repo
from app.db.repositories import extractions as repo
from app.domain.contracts import FieldRow, StoredClause
from app.extraction.schema import ExtractionReply, ExtractionReplyV2, FieldReply, FieldsV2
from app.llm.gateway import Gateway, InvalidReplyError, LLMRequest
from app.prompts import load, render

PROMPT_NAME = "extract_fields"
PROMPT_VERSION = 2
type Reply = ExtractionReply | ExtractionReplyV2
REPLY_SCHEMA: type[ExtractionReplyV2] = ExtractionReplyV2

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
    """Run the extraction prompt on one stored contract and store its fields."""
    prepared = await prepare(session, contract_id)
    try:
        reply = (await gateway.parse(prepared.request, REPLY_SCHEMA)).value
    except InvalidReplyError:
        return await store_rows(
            session, prepared, invalid_reply_rows(), model_id=gateway.model, keep_accepted=True
        )
    return await store(session, prepared, reply, model_id=gateway.model)


class ClauseText(Protocol):
    """What the prompt needs of a clause: a stored one or one fresh from the splitter."""

    @property
    def number(self) -> str: ...
    @property
    def heading(self) -> str: ...
    @property
    def body(self) -> str: ...


def build_request(title: str, clauses: Sequence[ClauseText]) -> LLMRequest:
    """Render the extraction prompt for one contract; the app and the eval share it."""
    prompt = load(PROMPT_NAME, PROMPT_VERSION)
    text = "\n".join(f"{c.number} {c.heading}\n{c.body}" for c in clauses)
    return LLMRequest(
        feature="extraction",
        prompt_name=PROMPT_NAME,
        prompt_version=f"v{prompt.version}",
        system=render(prompt, {"contract_title": title, "contract": text}),
        user="Return the JSON object for the contract above.",
        max_tokens=prompt.max_tokens,
    )


async def prepare(session: AsyncSession, contract_id: uuid.UUID) -> PreparedExtraction:
    """Read the contract and render the extraction prompt with its clauses. Writes nothing."""
    contract = await contract_repo.find_contract(session, contract_id)
    if contract is None:
        raise NotFoundError(f"Contract {contract_id} not found")
    stored = await contract_repo.clauses_of(session, contract_id)
    request = build_request(contract.title, stored)
    return PreparedExtraction(contract_id, request, {c.number: c for c in stored})


async def store(
    session: AsyncSession, prepared: PreparedExtraction, reply: Reply, *, model_id: str
) -> ExtractionResult:
    """Check every quote and store the fields in one savepoint: all rows or none."""
    if reply.injection_suspected:
        log.warning("extraction_injection_suspected", contract_id=str(prepared.contract_id))
    return await store_rows(
        session, prepared, check_fields(reply, prepared.clauses), model_id=model_id
    )


async def store_rows(
    session: AsyncSession,
    prepared: PreparedExtraction,
    rows: list[FieldRow],
    *,
    model_id: str,
    keep_accepted: bool = False,
) -> ExtractionResult:
    """Store the checked rows of one contract in one savepoint; report what is stored after."""
    async with session.begin_nested():
        await repo.upsert_extractions(
            session,
            prepared.contract_id,
            rows,
            prompt_version=prepared.request.prompt_version,
            model_id=model_id,
            keep_accepted=keep_accepted,
        )
    accepted, held = await repo.status_counts(
        session, prepared.contract_id, [r.field_name for r in rows]
    )
    log.info(
        "extraction_stored",
        contract_id=str(prepared.contract_id),
        accepted=accepted,
        needs_review=held,
    )
    return ExtractionResult(accepted=accepted, needs_review=held)


def check_fields(reply: Reply, by_number: dict[str, StoredClause]) -> list[FieldRow]:
    """One checked row per field of the reply's schema, in schema order."""
    return [
        check_field(name, getattr(reply.fields, name), by_number)
        for name in type(reply.fields).model_fields
    ]


def invalid_reply_rows() -> list[FieldRow]:
    """Every v2 field held for review because the model reply could not be read."""
    return [
        FieldRow(
            field_name=name,
            value_text=None,
            quote=None,
            cited_clause_number=None,
            clause_id=None,
            status="needs_review",
            review_reason="invalid_reply",
        )
        for name in FieldsV2.model_fields
    ]


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
