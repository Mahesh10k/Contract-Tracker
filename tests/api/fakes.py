"""An async UiService for route tests: canned data, records calls, no database."""

import uuid
from datetime import date

from app.core.errors import DomainError, NotFoundError
from app.domain.contracts import ContractSummary, StoredField
from app.ui.service import NotAvailableError
from app.ui.views import AnswerView, Citation, DeadlineRow

LEASE = ContractSummary(uuid.uuid4(), "Lease Agreement 01", "lease", "lease-01.pdf")


def stored(
    name: str, value: str | None, clause: str | None, status: str = "accepted"
) -> StoredField:
    reason = None if status == "accepted" else "value_missing"
    quote = f"Quote for {name}." if value else None
    return StoredField(LEASE.id, LEASE.title, name, value, quote, clause, status, reason)


FIELDS = [
    stored("parties", "Northgate Realty Inc and Delta Foods Inc", "1"),
    stored("effective_date", "1 January 2025", "2.1"),
    stored("term", "two (2) years", "2.2"),
    stored("auto_renewal", None, None, "needs_review"),
    stored("notice_period", "not less than thirty days", "7"),
]


class FakeService:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []
        self.missing: set[uuid.UUID] = set()

    async def list_contracts(self) -> list[ContractSummary]:
        return [LEASE]

    async def fields_of(self, contract_id: uuid.UUID) -> list[StoredField]:
        return FIELDS if contract_id == LEASE.id else []

    async def upload(self, filename: str, data: bytes, contract_type: str) -> str:
        self.calls.append(("upload", filename, data, contract_type))
        return "Lease Agreement 01"

    async def load_golden(self) -> list[str]:
        self.calls.append(("golden",))
        return ["Lease Agreement 01", "Supply Agreement 07 (already loaded)"]

    async def extract(self, contract_id: uuid.UUID) -> str:
        self.calls.append(("extract", contract_id))
        if contract_id != LEASE.id:
            raise NotFoundError(f"Contract {contract_id} not found")
        return "4 accepted, 1 need review"

    async def deadlines(self, today: date) -> list[DeadlineRow]:
        self.calls.append(("deadlines", today))
        return [
            DeadlineRow("Lease Agreement 01", "notice_deadline", date(2026, 12, 1), "7", 57),
            DeadlineRow("Lease Agreement 01", "expiry", date(2026, 12, 31), "2.2", 87),
        ]

    async def held(self) -> list[StoredField]:
        return [FIELDS[3]]

    async def ask(self, question: str) -> AnswerView:
        self.calls.append(("ask", question))
        if question.startswith("Which law"):
            return AnswerView(
                text="Supply Agreement 08 is governed by the laws of the State of California.",
                citations=[
                    Citation(
                        "Supply Agreement 08",
                        "8",
                        "This Agreement is governed by the laws of the State of California.",
                    )
                ],
                refused=False,
            )
        raise NotAvailableError("Questions cannot be answered right now.")

    async def send_due_reminders(self, today: date) -> str:
        self.calls.append(("remind", today))
        raise DomainError("Reminder emails arrive with Checkpoint 5.")
