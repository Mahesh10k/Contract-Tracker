"""`make embed` and `make ask` argument handling and output (US-00-004)."""

import pytest

from app.core.errors import DomainError
from app.qa import cli
from app.ui.views import AnswerView, Citation


class FakeEngine:
    async def dispose(self) -> None:
        pass


class FakeService:
    def __init__(self, view: AnswerView | DomainError) -> None:
        self.view = view

    async def ask(self, question: str) -> AnswerView:
        if isinstance(self.view, DomainError):
            raise self.view
        return self.view


def patch_wiring(monkeypatch: pytest.MonkeyPatch, service: FakeService) -> None:
    monkeypatch.setattr(cli, "get_settings", lambda: object())
    monkeypatch.setattr(cli, "make_engine", lambda _s: FakeEngine())
    monkeypatch.setattr(cli, "make_session_factory", lambda _e: object())
    monkeypatch.setattr(cli, "UiService", lambda _settings, _factory: service)


def test_ask_prints_the_answer_and_each_citation_with_its_clause_text(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    view = AnswerView(
        "California.", [Citation("Supply Agreement 08", "8", "Governed by California.")], False
    )
    patch_wiring(monkeypatch, FakeService(view))

    code = cli.main(["ask", "Which law governs Supply Agreement 08?"])

    out = capsys.readouterr().out
    assert code == 0
    assert out.splitlines()[0] == "California."
    assert "[Supply Agreement 08, 8] Governed by California." in out


def test_ask_reports_a_service_error_on_stderr_and_exits_1(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    patch_wiring(monkeypatch, FakeService(DomainError("LLM budget reached")))

    code = cli.main(["ask", "Anything?"])

    captured = capsys.readouterr()
    assert code == 1
    assert captured.err == "LLM budget reached\n"
    assert captured.out == ""


def test_a_command_is_required() -> None:
    with pytest.raises(SystemExit) as raised:
        cli.main([])

    assert raised.value.code == 2


def test_embed_reports_how_many_clauses_it_embedded(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    class Session:
        async def __aenter__(self) -> "Session":
            return self

        async def __aexit__(self, *exc: object) -> None:
            return None

        def begin(self) -> "Session":
            return self

    async def fake_embed_missing(session: object, embedder: object) -> int:
        return 71

    monkeypatch.setattr(cli, "get_settings", lambda: type("S", (), {"embedding_model_dir": "m"})())
    monkeypatch.setattr(cli, "make_engine", lambda _s: FakeEngine())
    monkeypatch.setattr(cli, "make_session_factory", lambda _e: Session)
    monkeypatch.setattr(cli, "SentenceTransformerEmbedder", lambda _d: object())
    monkeypatch.setattr(cli, "embed_missing", fake_embed_missing)

    code = cli.main(["embed"])

    assert code == 0
    assert capsys.readouterr().out == "embedded 71 clauses\n"
