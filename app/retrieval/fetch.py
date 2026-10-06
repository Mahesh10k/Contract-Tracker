"""Download the embedding model once into a local folder (`make fetch-model`, run by `make setup`).

After this, embedding never touches the network (Q-016): the embedder loads from this folder.
"""

import sys

from app.core.config import Settings
from app.retrieval.embedder import MODEL_NAME


def main() -> int:
    """Fetch BAAI/bge-small-en-v1.5 into settings.embedding_model_dir."""
    from sentence_transformers import SentenceTransformer

    target = Settings.model_fields["embedding_model_dir"].default / MODEL_NAME.replace("/", "--")
    target.parent.mkdir(parents=True, exist_ok=True)
    SentenceTransformer(MODEL_NAME, device="cpu").save(str(target))
    sys.stdout.write(f"embedding model saved to {target}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
