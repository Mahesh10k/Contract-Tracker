"""The offline Q&A eval needs the saved embedding model and says so when it is missing (Q-016)."""

from pathlib import Path

from app.retrieval.embedder import MODEL_NAME
from evals.qa.run import missing_model_message


def test_a_missing_model_folder_gives_a_message_naming_the_fix(tmp_path: Path) -> None:
    message = missing_model_message(tmp_path)

    assert message is not None
    assert "make fetch-model" in message
    assert "never downloads" in message


def test_a_saved_model_folder_gives_no_message(tmp_path: Path) -> None:
    (tmp_path / MODEL_NAME.replace("/", "--")).mkdir()

    assert missing_model_message(tmp_path) is None
