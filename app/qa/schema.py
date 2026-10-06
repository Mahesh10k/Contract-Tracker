"""The reply schema sent to the model as strict JSON and validated on return."""

from pydantic import BaseModel, ConfigDict


class CitationRef(BaseModel):
    """One clause the model says it used, copied from the clause label."""

    model_config = ConfigDict(extra="forbid")

    contract: str
    clause: str


class AnswerReply(BaseModel):
    """The model's answer to one question (prompts/answer_question/v1.md)."""

    model_config = ConfigDict(extra="forbid")

    answerable: bool
    answer: str
    citations: list[CitationRef]
