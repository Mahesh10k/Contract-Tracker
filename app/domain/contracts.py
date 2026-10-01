"""Domain types for contracts, shared by ingestion and the repositories."""

import uuid
from dataclasses import dataclass

from app.core.errors import DomainError


@dataclass(frozen=True)
class Clause:
    """One numbered clause: its number as printed, heading and body text."""

    number: str
    heading: str
    body: str


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
