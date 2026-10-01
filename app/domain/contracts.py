"""Domain types for contracts, shared by ingestion and the repositories."""

import uuid
from dataclasses import dataclass


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
