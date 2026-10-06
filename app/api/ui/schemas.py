"""Request and response shapes for the React page. Mirrored by web/src/api.ts."""

import uuid
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ContractOut(BaseModel):
    id: uuid.UUID
    title: str
    contract_type: Literal["lease", "vendor", "service"]
    source_filename: str


class FieldOut(BaseModel):
    field: str
    value: str | None
    quote: str | None
    clause: str | None
    status: Literal["accepted", "needs_review", "corrected"]
    review_reason: str | None


class DeadlineOut(BaseModel):
    contract: str
    kind: Literal["expiry", "notice_deadline"]
    due: date
    days_left: int
    clause: str | None


class HeldOut(BaseModel):
    contract: str
    field: str
    value: str | None
    quote: str | None
    reason: str


class CitationOut(BaseModel):
    contract: str
    clause: str
    text: str


class AnswerOut(BaseModel):
    text: str
    citations: list[CitationOut]
    refused: bool


class MessageOut(BaseModel):
    message: str


class LoadedOut(BaseModel):
    loaded: list[str]


class AskIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=500)


class RemindIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    today: date
