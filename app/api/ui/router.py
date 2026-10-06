"""JSON routes under /api for the React page (ADR-0016). Routes parse, call one service, return."""

import uuid
from datetime import UTC, date, datetime
from pathlib import PurePosixPath, PureWindowsPath
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile

from app.api.ui.schemas import (
    AnswerOut,
    AskIn,
    CitationOut,
    ContractOut,
    DeadlineOut,
    FieldOut,
    HeldOut,
    LoadedOut,
    MessageOut,
    RemindIn,
)
from app.core.errors import ErrorEnvelope
from app.domain.contracts import StoredField
from app.reminders.plan import resolve_today
from app.ui.service import (
    MAX_UPLOAD_BYTES,
    UiApi,
    UploadNotPdfError,
    UploadTooLargeError,
)

router = APIRouter(prefix="/api", tags=["ui"], responses={"default": {"model": ErrorEnvelope}})


def get_ui_service(request: Request) -> UiApi:
    """The UiService the lifespan built; tests override this dependency."""
    service: UiApi = request.app.state.ui_service
    return service


Service = Annotated[UiApi, Depends(get_ui_service)]


def _field(f: StoredField) -> FieldOut:
    return FieldOut(
        field=f.field_name,
        value=f.value,
        quote=f.quote,
        clause=f.clause_number,
        status=f.status,
        review_reason=f.review_reason,
    )


def _base_name(filename: str | None) -> str:
    """A bare file name: no directory part from either path style."""
    return PurePosixPath(PureWindowsPath(filename or "contract.pdf").name).name or "contract.pdf"


@router.get("/contracts", response_model=list[ContractOut])
async def list_contracts(service: Service) -> list[ContractOut]:
    return [
        ContractOut.model_validate(c, from_attributes=True) for c in await service.list_contracts()
    ]


@router.post("/contracts", response_model=MessageOut, status_code=201)
async def upload_contract(
    service: Service,
    file: Annotated[UploadFile, File()],
    contract_type: Annotated[Literal["lease", "vendor", "service"], Form()],
) -> MessageOut:
    """Load a text PDF; limits and the signature are checked before the service sees it."""
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise UploadTooLargeError("File is larger than 5 MB")
    if not data.startswith(b"%PDF"):
        raise UploadNotPdfError("That file is not a PDF")
    title = await service.upload(_base_name(file.filename), data, contract_type)
    return MessageOut(message=title)


@router.post("/contracts/golden", response_model=LoadedOut)
async def load_golden(service: Service) -> LoadedOut:
    return LoadedOut(loaded=await service.load_golden())


@router.get("/contracts/{contract_id}/fields", response_model=list[FieldOut])
async def contract_fields(contract_id: uuid.UUID, service: Service) -> list[FieldOut]:
    return [_field(f) for f in await service.fields_of(contract_id)]


@router.post("/contracts/{contract_id}/extract", response_model=MessageOut)
async def extract_contract(contract_id: uuid.UUID, service: Service) -> MessageOut:
    return MessageOut(message=await service.extract(contract_id))


@router.get("/deadlines", response_model=list[DeadlineOut])
async def deadlines(
    request: Request, service: Service, today: Annotated[date | None, Query()] = None
) -> list[DeadlineOut]:
    on = resolve_today(today, request.app.state.settings.pretend_today, datetime.now(UTC).date())
    rows = await service.deadlines(on)
    return [
        DeadlineOut(
            contract=r.contract_title,
            kind=r.kind,
            due=r.due,
            days_left=r.days_left,
            clause=r.clause,
        )
        for r in rows
    ]


@router.get("/review", response_model=list[HeldOut])
async def review(service: Service) -> list[HeldOut]:
    return [
        HeldOut(
            contract=f.contract_title,
            field=f.field_name,
            value=f.value,
            quote=f.quote,
            reason=f.review_reason or "unknown",
        )
        for f in await service.held()
    ]


@router.post("/ask", response_model=AnswerOut)
async def ask(body: AskIn, service: Service) -> AnswerOut:
    answer = await service.ask(body.question)
    return AnswerOut(
        text=answer.text,
        refused=answer.refused,
        citations=[
            CitationOut(contract=c.contract_title, clause=c.clause_number, text=c.clause_text)
            for c in answer.citations
        ],
    )


@router.post("/reminders/send", response_model=MessageOut)
async def send_reminders(body: RemindIn, service: Service) -> MessageOut:
    return MessageOut(message=await service.send_due_reminders(body.today))
