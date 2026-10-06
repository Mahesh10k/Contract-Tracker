"""A Backend for page tests: records calls, holds canned data, no database."""

import uuid

from app.domain.contracts import ContractSummary, StoredField

LEASE_01 = ContractSummary(uuid.uuid4(), "Lease Agreement 01", "lease", "lease-01.pdf")


def field(
    contract: ContractSummary,
    name: str,
    value: str | None,
    clause: str | None,
    status: str = "accepted",
    reason: str | None = None,
) -> StoredField:
    quote = f"Quote for {name}." if value else None
    return StoredField(contract.id, contract.title, name, value, quote, clause, status, reason)


LEASE_01_FIELDS = [
    field(LEASE_01, "parties", "Northgate Realty Inc and Delta Foods Inc", "1"),
    field(LEASE_01, "effective_date", "1 January 2025", "2.1"),
    field(LEASE_01, "term", "two (2) years", "2.2"),
    field(LEASE_01, "auto_renewal", "does not renew automatically", "2.3"),
    field(LEASE_01, "notice_period", "not less than thirty days", "7"),
]
