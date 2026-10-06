"""Domain types for contracts, shared by ingestion and the repositories."""

import uuid
from dataclasses import dataclass

from app.core.errors import DomainError


@dataclass(frozen=True)
class Clause:
    """One numbered clause: its number as printed, heading, body and the pages it is on.

    Pages are 1-based and None when the text came without page boundaries
    (US-00-009).
    """

    number: str
    heading: str
    body: str
    first_page: int | None = None
    last_page: int | None = None


@dataclass(frozen=True)
class StoredClause:
    """A clause as stored, with the id an extraction cites."""

    id: uuid.UUID
    number: str
    heading: str
    body: str


@dataclass(frozen=True)
class FieldRow:
    """One extracted field ready to store (US-00-002)."""

    field_name: str
    value_text: str | None
    quote: str | None
    cited_clause_number: str | None
    clause_id: uuid.UUID | None
    status: str
    review_reason: str | None


@dataclass(frozen=True)
class StoredContract:
    """A contract already in the database, as the duplicate check needs it."""

    id: uuid.UUID
    title: str


@dataclass(frozen=True)
class NewContract:
    """Everything stored for a contract before its clauses."""

    title: str
    contract_type: str
    source_filename: str
    file_sha256: str
    full_text: str
    page_count: int


class ContractRefusedError(DomainError):
    """The database refused a contract or clause row; `constraint` names the rule."""

    status_code = 422
    code = "contract_refused"

    def __init__(self, constraint: str) -> None:
        super().__init__(f"refused by {constraint}", details={"constraint": constraint})
        self.constraint = constraint
