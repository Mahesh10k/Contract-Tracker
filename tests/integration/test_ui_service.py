"""The real UiService on Postgres (US-00-007, TC-0135). Needs make db and make migrate."""

from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.llm.gateway import LLMRequest, Parsed
from app.qa.schema import AnswerReply, CitationRef
from app.ui.service import UiService
from tests.retrieval.fakes import FakeEmbedder

pytestmark = pytest.mark.integration


class ScriptedParser:
    def __init__(self, reply: AnswerReply) -> None:
        self.reply = reply

    async def parse(self, req: LLMRequest, schema: type[AnswerReply]) -> Parsed[AnswerReply]:
        return Parsed(value=self.reply, cache_hit=False)


@pytest.fixture
async def factory(session: AsyncSession) -> async_sessionmaker[AsyncSession]:
    connection = await session.connection()
    return async_sessionmaker(bind=connection, join_transaction_mode="create_savepoint")


@pytest.fixture
def service(factory: async_sessionmaker[AsyncSession]) -> UiService:
    settings = Settings(
        _env_file=None,
        env="test",
        database_url="postgresql+asyncpg://postgres:postgres@localhost:5432/unused",
    )
    return UiService(settings, factory)


# TC-0135
async def test_tc0135_golden_set_loads_lists_and_starts_without_deadlines(
    service: UiService,
) -> None:
    first = await service.load_golden()
    again = await service.load_golden()

    assert len(first) == 6
    assert not any("already loaded" in t for t in first)
    assert [t.endswith("(already loaded)") for t in again] == [True] * 6
    assert len(await service.list_contracts()) == 6
    assert await service.deadlines(date(2026, 10, 5)) == []
    assert await service.held() == []


# TC-0160
async def test_tc0160_ask_embeds_retrieves_answers_and_returns_citation_text(
    factory: async_sessionmaker[AsyncSession],
) -> None:
    # The real service on Postgres with a fake embedder and a scripted model (US-00-004).
    reply = AnswerReply(
        answerable=True,
        answer="California.",
        citations=[CitationRef(contract="Supply Agreement 08", clause="8")],
    )
    settings = Settings(
        _env_file=None,
        env="test",
        database_url="postgresql+asyncpg://postgres:postgres@localhost:5432/unused",
        qa_similarity_floor=0.0,
    )
    service = UiService(
        settings,
        factory,
        embedder=FakeEmbedder(),
        gateway_for=lambda _session: ScriptedParser(reply),
    )
    await service.load_golden()

    answer = await service.ask("Which law governs Supply Agreement 08?")

    assert answer.refused is False
    assert [(c.contract_title, c.clause_number) for c in answer.citations] == [
        ("Supply Agreement 08", "8")
    ]
    assert "California" in answer.citations[0].clause_text
