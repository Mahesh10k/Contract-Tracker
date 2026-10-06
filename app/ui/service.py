"""What the web UI may ask for, as async services over the same code the CLI uses (ADR-0016).

The JSON routes call a `UiService`; tests give them a fake. No HTTP types here and no
SQL: reads go through the repositories, writes through the ingestion and extraction
services, and dates through compute_obligations (never computed in the browser).
"""

import json
import tempfile
import uuid
from collections.abc import Callable
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Protocol

import anyio
import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.core.errors import DomainError
from app.db.repositories import contracts as contract_repo
from app.db.repositories import extractions as field_repo
from app.db.repositories.reminders import PgReminderStore
from app.domain.contracts import ContractSummary, StoredField
from app.extraction.cli import extract_one, gateway_factory
from app.extraction.schema import FieldsV2
from app.ingestion.service import ingest_file
from app.qa.service import AnswerParser, answer_from_hits
from app.reminders.mailer import SmtpMailer
from app.reminders.service import Mailer, send_due
from app.reminders.sync import sync_all
from app.retrieval.embedder import Embedder, SentenceTransformerEmbedder
from app.retrieval.service import embed_missing, search
from app.ui.views import AnswerView, Citation, DeadlineRow, deadlines_from

FIELDS = tuple(FieldsV2.model_fields)
GOLDEN_DIR = Path("data/contracts")
GOLDEN_KEY = Path("data/answer_key.json")
MAX_UPLOAD_BYTES = 5 * 1024 * 1024


class NotAvailableError(DomainError):
    """A tab whose service is not built yet in this task."""

    status_code = 501
    code = "not_available"


class UploadTooLargeError(DomainError):
    """The file is over the upload limit (REQ-044)."""

    status_code = 413
    code = "upload_too_large"


class UploadNotPdfError(DomainError):
    """The file does not start with a PDF signature."""

    status_code = 422
    code = "upload_not_pdf"


class UiApi(Protocol):
    """Everything the JSON routes call."""

    async def list_contracts(self) -> list[ContractSummary]: ...
    async def fields_of(self, contract_id: uuid.UUID) -> list[StoredField]: ...
    async def upload(self, filename: str, data: bytes, contract_type: str) -> str: ...
    async def load_golden(self) -> list[str]: ...
    async def extract(self, contract_id: uuid.UUID) -> str: ...
    async def deadlines(self, today: date) -> list[DeadlineRow]: ...
    async def held(self) -> list[StoredField]: ...
    async def ask(self, question: str) -> AnswerView: ...
    async def send_due_reminders(self, today: date) -> str: ...


class UiService:
    """The UiApi on Postgres, the ingestion service and the extraction gateway."""

    def __init__(
        self,
        settings: Settings,
        factory: async_sessionmaker[AsyncSession],
        *,
        embedder: Embedder | None = None,
        gateway_for: Callable[[AsyncSession], AnswerParser] | None = None,
        mailer: Mailer | None = None,
    ) -> None:
        self.settings = settings
        self.factory = factory
        self._embedder = embedder
        self._gateway_for = gateway_for
        self._mailer = mailer

    async def list_contracts(self) -> list[ContractSummary]:
        async with self.factory() as session:
            return await contract_repo.list_contracts(session)

    async def fields_of(self, contract_id: uuid.UUID) -> list[StoredField]:
        async with self.factory() as session:
            return await field_repo.fields_of(session, contract_id, FIELDS)

    async def upload(self, filename: str, data: bytes, contract_type: str) -> str:
        """Store an uploaded PDF through the same checks as `make ingest`; return its title."""
        with tempfile.TemporaryDirectory() as tmp:
            path = anyio.Path(tmp) / Path(filename).name
            await path.write_bytes(data)
            return await self._ingest(Path(path), contract_type)

    async def load_golden(self) -> list[str]:
        """Load the 6 golden PDFs named in data/answer_key.json, with their truth.json titles."""
        key = json.loads(await anyio.Path(GOLDEN_KEY).read_text(encoding="utf-8"))
        return [await self._ingest(GOLDEN_DIR / f"{cid}.pdf", None) for cid in key["contracts"]]

    async def _ingest(self, path: Path, contract_type: str | None) -> str:
        async with self.factory() as session, session.begin():
            result = await ingest_file(session, path, contract_type)
        return result.title if result.created else f"{result.title} (already loaded)"

    async def extract(self, contract_id: uuid.UUID) -> str:
        # The client is made here, not at start-up: TLS setup is only needed for a live call.
        async with httpx.AsyncClient() as client:
            gateway_for = gateway_factory(self.settings, client, uuid.uuid4())
            result = await extract_one(self.factory, gateway_for, contract_id)
        return f"{result.accepted} accepted, {result.needs_review} need review"

    async def deadlines(self, today: date) -> list[DeadlineRow]:
        async with self.factory() as session:
            usable = await field_repo.usable_fields(session, FIELDS)
        return deadlines_from(usable, today)

    async def held(self) -> list[StoredField]:
        async with self.factory() as session:
            return await field_repo.held_fields(session, FIELDS)

    def _embedder_in_use(self) -> Embedder:
        """The embedding model, loaded on the first question and kept for the process."""
        if self._embedder is None:
            self._embedder = SentenceTransformerEmbedder(self.settings.embedding_model_dir)
        return self._embedder

    async def ask(self, question: str) -> AnswerView:
        """Embed new clauses, retrieve the closest 5, answer from them, check the citations."""
        embedder = self._embedder_in_use()
        async with self.factory() as session, session.begin():
            await embed_missing(session, embedder)
        async with self.factory() as session:
            hits = await search(session, embedder, question)
        async with self.factory() as ledger_session:
            try:
                if self._gateway_for is not None:
                    gateway = self._gateway_for(ledger_session)
                    answer = await answer_from_hits(
                        question, hits, gateway, self.settings.qa_similarity_floor
                    )
                else:
                    async with httpx.AsyncClient() as client:
                        gateway = gateway_factory(self.settings, client, uuid.uuid4())(
                            ledger_session
                        )
                        answer = await answer_from_hits(
                            question, hits, gateway, self.settings.qa_similarity_floor
                        )
            finally:
                await ledger_session.commit()
        return AnswerView(
            text=answer.text,
            refused=answer.refused,
            citations=[
                Citation(c.contract_title, c.clause_number, c.clause_text) for c in answer.citations
            ],
        )

    async def send_due_reminders(self, today: date) -> str:
        """Sync obligations and reminders from the accepted fields, then email what is due."""
        async with self.factory() as session, session.begin():
            await sync_all(session)
        mailer = self._mailer or SmtpMailer(self.settings.smtp_host, self.settings.smtp_port)
        preview = today > datetime.now(UTC).date()
        result = await send_due(
            PgReminderStore(self.factory),
            mailer,
            today,
            self.settings.reminder_to,
            self.settings.reminder_from,
            record=not preview,
        )
        if preview:
            return (
                f"Preview for {today.isoformat()}: {result.sent} email"
                f"{'s' if result.sent != 1 else ''} sent to MailHog, nothing recorded "
                "(that date has not happened yet)."
            )
        if result.sent == 0 and result.skipped == 0:
            return "No reminders are due."
        parts = [f"{result.sent} reminder{'s' if result.sent != 1 else ''} sent"]
        if result.skipped:
            parts.append(f"{result.skipped} skipped (older or expired)")
        return ", ".join(parts)
