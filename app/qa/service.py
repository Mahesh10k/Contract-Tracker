"""Cited answers from retrieved clauses, and the checks that decide when to refuse.

Three layers keep an answer honest (ADR-0013, REQ-048 to REQ-051):
1. a similarity floor in code: a question whose best clause is too far away never reaches the model;
2. the prompt: use only the clauses shown, say so when they do not answer;
3. a citation check in code: every [contract, clause] the model cites must be one of the clauses
   it was given. Anything else, or no citation at all, becomes the refusal text.
The model proposes; code decides what the owner sees.
"""

from dataclasses import dataclass
from typing import Protocol

from app.llm.gateway import LLMRequest, Parsed
from app.prompts import load, render
from app.qa.schema import AnswerReply
from app.retrieval.rank import Hit

REFUSAL = "Not found in these contracts"
PROMPT_NAME = "answer_question"
PROMPT_VERSION = 1


@dataclass(frozen=True)
class AnsweredCitation:
    """A citation that passed the check, with the clause text to show beside it."""

    contract_title: str
    clause_number: str
    clause_text: str


@dataclass(frozen=True)
class Answer:
    """What the owner sees: an answer with checked citations, or the refusal."""

    text: str
    citations: list[AnsweredCitation]
    refused: bool


class AnswerParser(Protocol):
    """The part of the gateway this step uses."""

    async def parse(self, req: LLMRequest, schema: type[AnswerReply]) -> Parsed[AnswerReply]: ...


def refusal() -> Answer:
    """The one refusal, always the same words."""
    return Answer(REFUSAL, [], True)


def clause_block(hits: list[Hit]) -> str:
    """The retrieved clauses, each labelled [contract title, clause number]."""
    return "\n\n".join(
        f"[{h.contract_title}, {h.clause_number}] {h.heading}\n{h.body}" for h in hits
    )


def build_request(question: str, hits: list[Hit]) -> LLMRequest:
    """Render the answer prompt with only the retrieved clauses."""
    prompt = load(PROMPT_NAME, PROMPT_VERSION)
    return LLMRequest(
        feature="qa",
        prompt_name=PROMPT_NAME,
        prompt_version=f"v{prompt.version}",
        system=render(prompt, {"question": question, "clauses": clause_block(hits)}),
        user="Return the JSON object for the question above.",
        max_tokens=prompt.max_tokens,
    )


def check_reply(reply: AnswerReply, hits: list[Hit]) -> Answer:
    """Accept the reply only if it answers, says something and cites only retrieved clauses."""
    if not reply.answerable or not reply.answer.strip() or not reply.citations:
        return refusal()
    by_source = {(h.contract_title, h.clause_number): h for h in hits}
    cited: list[AnsweredCitation] = []
    for ref in reply.citations:
        found = by_source.get((ref.contract, ref.clause))
        if found is None:
            return refusal()
        cited.append(AnsweredCitation(found.contract_title, found.clause_number, found.body))
    return Answer(reply.answer.strip(), cited, False)


async def answer_from_hits(
    question: str, hits: list[Hit], gateway: AnswerParser, floor: float
) -> Answer:
    """Answer from the retrieved clauses, or refuse; no model call below the similarity floor."""
    if not hits or hits[0].score < floor:
        return refusal()
    reply = (await gateway.parse(build_request(question, hits), AnswerReply)).value
    return check_reply(reply, hits)
