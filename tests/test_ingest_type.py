"""Type and title for a file: from truth.json beside it, else from --type (US-00-001).

Written after app/ingestion/service.py; the same behaviour has red-first
integration tests (TC-0002 and the unknown-type case in test_ingest.py).
These run without a database so `make check` measures them.
"""

from pathlib import Path

import pytest

from app.domain.contracts import ContractRefusedError
from app.ingestion.cli import main
from app.ingestion.service import (
    ContractTypeRequiredError,
    InvalidContractError,
    _type_and_title,
)


async def test_truth_json_beside_the_file_gives_type_and_title(tmp_path: Path) -> None:
    (tmp_path / "lease-09.truth.json").write_text('{"contract_type": "lease", "title": "Lease 09"}')

    result = await _type_and_title(tmp_path / "lease-09.pdf", None)

    assert result == ("lease", "Lease 09")


async def test_truth_json_wins_over_the_type_argument(tmp_path: Path) -> None:
    (tmp_path / "lease-09.truth.json").write_text('{"contract_type": "lease", "title": "Lease 09"}')

    result = await _type_and_title(tmp_path / "lease-09.pdf", "vendor")

    assert result == ("lease", "Lease 09")


async def test_without_truth_the_type_argument_and_file_stem_are_used(tmp_path: Path) -> None:
    result = await _type_and_title(tmp_path / "acme-supply.pdf", "vendor")

    assert result == ("vendor", "acme-supply")


async def test_without_truth_or_type_the_file_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ContractTypeRequiredError):
        await _type_and_title(tmp_path / "acme-supply.pdf", None)


async def test_truth_json_without_a_title_is_refused(tmp_path: Path) -> None:
    (tmp_path / "x.truth.json").write_text('{"contract_type": "lease"}')

    with pytest.raises(InvalidContractError):
        await _type_and_title(tmp_path / "x.pdf", None)


async def test_truth_json_that_is_not_an_object_is_refused(tmp_path: Path) -> None:
    (tmp_path / "x.truth.json").write_text("[1, 2]")

    with pytest.raises(InvalidContractError) as raised:
        await _type_and_title(tmp_path / "x.pdf", None)

    assert raised.value.message == "x.truth.json: not valid JSON"


async def test_truth_json_that_cannot_be_read_is_refused(tmp_path: Path) -> None:
    (tmp_path / "x.truth.json").mkdir()

    with pytest.raises(InvalidContractError) as raised:
        await _type_and_title(tmp_path / "x.pdf", None)

    assert raised.value.message.startswith("x.truth.json: cannot be read")


def test_cli_refuses_an_unknown_type_before_touching_the_database(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as raised:
        main(["--type", "lorry", "x.pdf"])

    assert raised.value.code == 2
    assert "invalid choice: 'lorry'" in capsys.readouterr().err


def test_refused_contract_error_names_the_constraint() -> None:
    error = ContractRefusedError("chk_clauses_body_not_blank")

    assert (error.constraint, error.details) == (
        "chk_clauses_body_not_blank",
        {"constraint": "chk_clauses_body_not_blank"},
    )
