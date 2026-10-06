"""The sentence-transformers embedder and the model fetch, with a stand-in library (ADR-0004)."""

import sys
import types
import uuid
from collections.abc import Sequence
from pathlib import Path
from typing import ClassVar

import pytest

from app.retrieval import fetch
from app.retrieval.embedder import MODEL_NAME, ModelNotFetchedError, SentenceTransformerEmbedder
from app.retrieval.service import embed_missing, search
from app.retrieval.text import QUERY_INSTRUCTION
from tests.retrieval.fakes import FakeEmbedder


class StandIn:
    """Records how the real library would have been called."""

    loads: ClassVar[list[tuple[str, str]]] = []
    encoded: ClassVar[list[tuple[list[str], bool]]] = []
    saved: ClassVar[list[str]] = []

    def __init__(self, name: str, device: str = "cpu") -> None:
        StandIn.loads.append((name, device))

    def encode(
        self, texts: list[str], normalize_embeddings: bool, show_progress_bar: bool
    ) -> list[list[float]]:
        StandIn.encoded.append((texts, normalize_embeddings))
        return [[1.0, 0.0] for _ in texts]

    def save(self, path: str) -> None:
        StandIn.saved.append(path)


@pytest.fixture(autouse=True)
def stand_in_library(monkeypatch: pytest.MonkeyPatch) -> None:
    StandIn.loads, StandIn.encoded, StandIn.saved = [], [], []
    module = types.ModuleType("sentence_transformers")
    module.SentenceTransformer = StandIn  # type: ignore[attr-defined]  # a stand-in module
    monkeypatch.setitem(sys.modules, "sentence_transformers", module)


def saved_model(root: Path) -> Path:
    """A folder where `make fetch-model` would have saved the model."""
    folder = root / MODEL_NAME.replace("/", "--")
    folder.mkdir()
    return folder


def test_a_question_gets_the_instruction_a_clause_does_not_and_vectors_are_normalised(
    tmp_path: Path,
) -> None:
    saved_model(tmp_path)
    embedder = SentenceTransformerEmbedder(tmp_path)

    embedder.embed_query("Who pays?")
    embedder.embed_documents(["clause text"])

    (query_texts, query_norm), (doc_texts, doc_norm) = StandIn.encoded
    assert query_texts == [f"{QUERY_INSTRUCTION}Who pays?"]
    assert doc_texts == ["clause text"]
    assert query_norm is True
    assert doc_norm is True


def test_the_model_is_loaded_once_from_the_local_folder_on_the_cpu_and_only_when_first_used(
    tmp_path: Path,
) -> None:
    local = saved_model(tmp_path)
    embedder = SentenceTransformerEmbedder(tmp_path)
    assert StandIn.loads == []

    embedder.embed_documents(["a"])
    embedder.embed_documents(["b"])

    assert StandIn.loads == [(str(local), "cpu")]


# TC-0178
def test_a_missing_model_folder_is_an_error_naming_the_fix_and_nothing_is_downloaded(
    tmp_path: Path,
) -> None:
    # Review 15: Q-016, no embedding ever needs the network.
    with pytest.raises(ModelNotFetchedError, match="make fetch-model"):
        SentenceTransformerEmbedder(tmp_path).embed_query("Who pays?")

    assert StandIn.loads == []


def test_fetch_saves_the_model_into_the_models_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    code = fetch.main()

    assert code == 0
    assert StandIn.saved == [str(Path("models") / "BAAI--bge-small-en-v1.5")]


class Rows:
    """Stands in for the repository: two batches of missing clauses, then none."""

    def __init__(self) -> None:
        self.batches = [
            [
                _clause("Lease Agreement 01", "1", "Parties", "A and B."),
                _clause("Lease Agreement 01", "2", "Term", "Two years."),
            ],
            [_clause("Lease Agreement 02", "1", "Parties", "C and D.")],
            [],
        ]
        self.stored: list[tuple[uuid.UUID, Sequence[float]]] = []
        self.model: str | None = None
        self.asked: Sequence[float] | None = None

    async def clauses_missing_embedding(self, session: object, limit: int) -> list[object]:
        return self.batches.pop(0)

    async def set_embeddings(
        self,
        session: object,
        vectors: Sequence[tuple[uuid.UUID, Sequence[float]]],
        model_name: str,
    ) -> None:
        self.stored.extend(vectors)
        self.model = model_name

    async def nearest(self, session: object, query: Sequence[float], k: int) -> list[object]:
        self.asked = query
        return []


def _clause(title: str, number: str, heading: str, body: str) -> object:
    from app.db.repositories.embeddings import ClauseToEmbed

    return ClauseToEmbed(uuid.uuid4(), title, number, heading, body)


async def test_embed_missing_embeds_every_batch_with_title_number_heading_and_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = Rows()
    monkeypatch.setattr("app.retrieval.service.repo", rows)
    embedder = FakeEmbedder()

    count = await embed_missing(object(), embedder)  # type: ignore[arg-type]  # the repo is faked

    assert count == 3
    assert embedder.documents[0] == "Lease Agreement 01 | 1 Parties | A and B."
    assert len(rows.stored) == 3
    assert rows.model == MODEL_NAME


async def test_search_embeds_the_question_in_query_form_and_asks_for_the_nearest_five(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = Rows()
    monkeypatch.setattr("app.retrieval.service.repo", rows)
    embedder = FakeEmbedder()

    await search(object(), embedder, "Who pays?")  # type: ignore[arg-type]  # the repo is faked

    assert embedder.queries == [f"{QUERY_INSTRUCTION}Who pays?"]
    assert rows.asked is not None
    assert len(rows.asked) == 384
