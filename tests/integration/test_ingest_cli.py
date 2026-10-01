"""The ingest command: messages and exit codes (TC-0002, TC-0011, TC-0014, TC-0017)."""

from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ingestion.cli import run
from evals.contracts.generate import generate
from tests.pdf_fixtures import image_only_pdf, text_pdf

pytestmark = pytest.mark.integration


@pytest.fixture
async def factory(session: AsyncSession) -> async_sessionmaker[AsyncSession]:
    """Sessions that share the test's rolled-back connection, each in a savepoint."""
    connection = await session.connection()
    return async_sessionmaker(bind=connection, join_transaction_mode="create_savepoint")


async def test_tc0002_missing_type_exits_2_with_the_message(
    factory: async_sessionmaker[AsyncSession], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "plain-contract.pdf"
    path.write_bytes(text_pdf("1 Parties\nA and B."))

    code = await run([path], None, factory)

    assert code == 2
    assert "Contract type required: --type lease, vendor or service" in capsys.readouterr().err


async def test_tc0011_scanned_pdf_exits_1_with_the_message(
    factory: async_sessionmaker[AsyncSession], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "scanned.pdf"
    path.write_bytes(image_only_pdf(2))

    code = await run([path], "lease", factory)

    assert code == 1
    assert "No text found" in capsys.readouterr().err


async def test_tc0017_text_file_exits_1_with_the_message(
    factory: async_sessionmaker[AsyncSession], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "not-a-pdf.pdf"
    path.write_bytes(b"hello\n")

    code = await run([path], "lease", factory)

    assert code == 1
    assert "Not a readable PDF" in capsys.readouterr().err


async def test_tc0014_second_load_reports_already_loaded(
    factory: async_sessionmaker[AsyncSession], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    generate(tmp_path)
    await run([tmp_path / "lease-01.pdf"], None, factory)
    capsys.readouterr()

    code = await run([tmp_path / "lease-01.pdf"], None, factory)

    assert code == 0
    assert "Already loaded as Lease Agreement 01" in capsys.readouterr().out


async def test_missing_file_does_not_stop_the_other_files(
    factory: async_sessionmaker[AsyncSession], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # TASK-001 review finding 2: a missing path used to end the run with a traceback.
    generate(tmp_path)

    code = await run([tmp_path / "typo.pdf", tmp_path / "lease-01.pdf"], None, factory)

    output = capsys.readouterr()
    assert code == 1
    assert "typo.pdf: File not found: typo.pdf" in output.err
    assert "lease-01.pdf: Loaded Lease Agreement 01" in output.out
