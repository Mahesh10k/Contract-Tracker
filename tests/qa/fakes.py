"""A model double for the answer step: returns a canned reply, counts calls, keeps the request."""

from app.llm.gateway import LLMRequest, Parsed
from app.qa.schema import AnswerReply, CitationRef


def reply(
    answer: str = "England and Wales.",
    *,
    answerable: bool = True,
    cites: tuple[tuple[str, str], ...] = (("Supply Agreement 07", "8"),),
) -> AnswerReply:
    return AnswerReply(
        answerable=answerable,
        answer=answer,
        citations=[CitationRef(contract=c, clause=n) for c, n in cites],
    )


class FakeGateway:
    def __init__(self, canned: AnswerReply | Exception) -> None:
        self.canned = canned
        self.requests: list[LLMRequest] = []

    async def parse(self, req: LLMRequest, schema: type[AnswerReply]) -> Parsed[AnswerReply]:
        self.requests.append(req)
        if isinstance(self.canned, Exception):
            raise self.canned
        return Parsed(value=self.canned, cache_hit=False)
