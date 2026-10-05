"""The reply schema sent to the model as a strict JSON schema and validated on return."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class FieldReply(BaseModel):
    """One field as the model returns it: the words, the sentence and the clause number."""

    model_config = ConfigDict(extra="forbid")

    value: str | None
    quote: str | None
    clause_id: str | None


class Fields(BaseModel):
    """The 10 fields of REQ-005, all required, each possibly null inside."""

    model_config = ConfigDict(extra="forbid")

    parties: FieldReply
    effective_date: FieldReply
    term: FieldReply
    auto_renewal: FieldReply
    notice_period: FieldReply
    payment_terms: FieldReply
    escalation: FieldReply
    liability_cap: FieldReply
    termination_rights: FieldReply
    governing_law: FieldReply


class ExtractionReply(BaseModel):
    """The whole reply for one contract (prompts/extract_fields/v1.md)."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ok", "unsupported"]
    reason: str | None
    injection_suspected: bool
    fields: Fields


class FieldsV2(BaseModel):
    """The 5 fields of REQ-045 (prompt v2, ADR-0015), all required, each possibly null inside."""

    model_config = ConfigDict(extra="forbid")

    parties: FieldReply
    effective_date: FieldReply
    term: FieldReply
    auto_renewal: FieldReply
    notice_period: FieldReply


class ExtractionReplyV2(BaseModel):
    """The whole reply for one contract (prompts/extract_fields/v2.md)."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ok", "unsupported"]
    reason: str | None
    injection_suspected: bool
    fields: FieldsV2
