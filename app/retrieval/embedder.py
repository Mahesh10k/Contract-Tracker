"""The embedding model behind one small interface (ADR-0004).

`Embedder` is what the rest of the code depends on; tests and the offline path use a fake, and
`SentenceTransformerEmbedder` loads BAAI/bge-small-en-v1.5 on CPU only when it is first used, so
importing the app never imports PyTorch. The model is fetched once by `make setup` into a local
folder and then loaded from there, so no embedding ever needs the network (Q-016).
"""

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from app.core.errors import DomainError
from app.retrieval.text import query_text

MODEL_NAME = "BAAI/bge-small-en-v1.5"
DIMENSIONS = 384


class ModelNotFetchedError(DomainError):
    """The embedding model is not saved locally; embedding never downloads it (Q-016)."""

    status_code = 503
    code = "embedding_model_missing"


class Embedder(Protocol):
    """Turns text into vectors: passages as they are, questions in query form."""

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]: ...

    def embed_query(self, question: str) -> list[float]: ...


class SentenceTransformerEmbedder:
    """bge-small on CPU, vectors normalised so cosine similarity is a dot product."""

    def __init__(self, model_dir: Path) -> None:
        self.model_dir = model_dir
        self._model: object | None = None

    def _load(self) -> object:
        if self._model is None:
            local = self.model_dir / MODEL_NAME.replace("/", "--")
            if not local.exists():
                raise ModelNotFetchedError(
                    f"The embedding model is not in {self.model_dir}/. Run make fetch-model once."
                )
            # Imported here so the app and its tests start without PyTorch.
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(str(local), device="cpu")
        return self._model

    def _encode(self, texts: Sequence[str]) -> list[list[float]]:
        model = self._load()
        vectors = model.encode(  # type: ignore[attr-defined]  # loaded lazily; typed as object
            list(texts), normalize_embeddings=True, show_progress_bar=False
        )
        return [[float(x) for x in row] for row in vectors]

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return self._encode(texts)

    def embed_query(self, question: str) -> list[float]:
        return self._encode([query_text(question)])[0]
