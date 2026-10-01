"""Loading contracts into Postgres (US-00-001, TC-0001 to TC-0019, TC-0024)."""

from pathlib import Path

import pytest
from sqlalchemy import FromClause, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from structlog.testing import capture_logs

from app.core.errors import NotFoundError
from app.db.tables import clauses, contracts
from app.ingestion.pdf import NoTextLayerError, UnreadablePdfError
from app.ingestion.service import (
    ContractTypeRequiredError,
    InvalidContractError,
    get_clause,
    ingest_file,
)
from evals.contracts.generate import generate
from evals.contracts.truth import load_truth
from tests.pdf_fixtures import image_only_pdf, text_pdf

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def generated(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("contracts")
    generate(out)
    return out


@pytest.fixture(scope="module")
def truth_paths(generated: Path) -> list[Path]:
    return sorted(generated.glob("*.truth.json"))


def write(tmp_path: Path, name: str, data: bytes) -> Path:
    path = tmp_path / name
    path.write_bytes(data)
    return path


async def count(session: AsyncSession, table: FromClause) -> int:
    return await session.scalar(select(func.count()).select_from(table)) or 0


async def test_tc0001_generated_lease_is_stored_with_title_type_and_text(
    session: AsyncSession, generated: Path
) -> None:
    truth = load_truth(generated / "lease-01.truth.json")

    result = await ingest_file(session, generated / "lease-01.pdf")

    row = (await session.execute(select(contracts))).one()
    assert result.created is True
    assert (row.title, row.contract_type) == (truth["title"], "lease")
    assert [c["heading"] for c in truth["clauses"] if c["heading"] not in row.full_text] == []
    assert await count(session, contracts) == 1


async def test_tc0002_pdf_without_truth_and_type_is_refused(
    session: AsyncSession, tmp_path: Path
) -> None:
    path = write(tmp_path, "plain-contract.pdf", text_pdf("1 Parties\nA and B."))

    with pytest.raises(ContractTypeRequiredError) as raised:
        await ingest_file(session, path)

    assert raised.value.message == "Contract type required: --type lease, vendor or service"
    assert await count(session, contracts) == 0


async def test_tc0003_one_page_one_clause_contract_is_stored(
    session: AsyncSession, tmp_path: Path
) -> None:
    path = write(tmp_path, "one-clause.pdf", text_pdf("1 Services\nCleaning of the offices."))

    await ingest_file(session, path, contract_type="service")

    assert await session.scalar(select(contracts.c.page_count)) == 1
    assert list(await session.scalars(select(clauses.c.clause_number))) == ["1"]


async def test_tc0004_every_generated_contract_stores_its_truth_clauses(
    session: AsyncSession, truth_paths: list[Path]
) -> None:
    mismatched = []
    for truth_path in truth_paths:
        truth = load_truth(truth_path)
        result = await ingest_file(session, truth_path.with_name(f"{truth['id']}.pdf"))
        stored = await session.execute(
            select(clauses.c.clause_number, clauses.c.heading)
            .where(clauses.c.contract_id == result.contract_id)
            .order_by(clauses.c.position)
        )
        if [tuple(r) for r in stored] != [(c["number"], c["heading"]) for c in truth["clauses"]]:
            mismatched.append(truth["id"])

    assert mismatched == []
    assert await count(session, contracts) == 18


async def test_tc0008_clause_7_2_is_returned_without_its_neighbours(
    session: AsyncSession, tmp_path: Path
) -> None:
    text = "7.1 Term\nThree years.\n7.2 Renewal\nRenews yearly.\n7.3 Notice\nSixty days."
    result = await ingest_file(
        session, write(tmp_path, "c7.pdf", text_pdf(text)), contract_type="lease"
    )

    clause = await get_clause(session, result.contract_id, "7.2")

    assert clause.body == "Renews yearly."
    assert "Three years." not in clause.body
    assert "Sixty days." not in clause.body


async def test_tc0009_missing_clause_number_is_not_found(
    session: AsyncSession, generated: Path
) -> None:
    result = await ingest_file(session, generated / "lease-01.pdf")

    with pytest.raises(NotFoundError) as raised:
        await get_clause(session, result.contract_id, "99.1")

    assert raised.value.message == "Clause 99.1 not found in lease-01"


async def test_tc0010_first_and_last_clause_bodies_match_the_truth(
    session: AsyncSession, generated: Path
) -> None:
    truth = load_truth(generated / "lease-01.truth.json")
    result = await ingest_file(session, generated / "lease-01.pdf")
    first, last = truth["clauses"][0], truth["clauses"][-1]

    got_first = await get_clause(session, result.contract_id, first["number"])
    got_last = await get_clause(session, result.contract_id, last["number"])

    assert " ".join(got_first.body.split()) == first["body"]
    assert " ".join(got_last.body.split()) == last["body"]


@pytest.mark.parametrize(
    ("name", "data", "error"),
    [
        ("scanned.pdf", image_only_pdf(2), NoTextLayerError),  # TC-0011
        ("whitespace.pdf", text_pdf("   ", ""), NoTextLayerError),  # TC-0012
        ("not-a-pdf.pdf", b"hello\n", UnreadablePdfError),  # TC-0017
        ("truncated.pdf", text_pdf("1 Parties\nA and B.")[:300], UnreadablePdfError),  # TC-0018
        ("empty.pdf", b"", UnreadablePdfError),  # TC-0019
    ],
)
async def test_bad_files_are_refused_and_nothing_is_stored(
    session: AsyncSession, tmp_path: Path, name: str, data: bytes, error: type[Exception]
) -> None:
    with pytest.raises(error):
        await ingest_file(session, write(tmp_path, name, data), contract_type="lease")

    assert await count(session, contracts) == 0
    assert await count(session, clauses) == 0


async def test_tc0013_text_page_then_blank_page_is_stored(
    session: AsyncSession, tmp_path: Path
) -> None:
    path = write(tmp_path, "text-then-blank.pdf", text_pdf("1 Supply\nParts.", ""))

    await ingest_file(session, path, contract_type="vendor")

    assert await session.scalar(select(contracts.c.page_count)) == 2


async def test_tc0014_same_file_twice_keeps_one_contract(
    session: AsyncSession, generated: Path
) -> None:
    await ingest_file(session, generated / "lease-01.pdf")
    clause_count = await count(session, clauses)

    again = await ingest_file(session, generated / "lease-01.pdf")

    assert (again.created, again.title) == (False, "Lease Agreement 01")
    assert await count(session, contracts) == 1
    assert await count(session, clauses) == clause_count


async def test_tc0015_same_bytes_under_another_name_is_a_duplicate(
    session: AsyncSession, generated: Path, tmp_path: Path
) -> None:
    await ingest_file(session, generated / "lease-01.pdf")
    copy = write(tmp_path, "lease-01-copy.pdf", (generated / "lease-01.pdf").read_bytes())

    again = await ingest_file(session, copy, contract_type="lease")

    assert again.created is False
    assert await count(session, contracts) == 1


async def test_tc0016_file_with_one_different_character_is_a_new_contract(
    session: AsyncSession, tmp_path: Path
) -> None:
    await ingest_file(
        session, write(tmp_path, "a.pdf", text_pdf("1 Parties\nA and B.")), contract_type="lease"
    )

    await ingest_file(
        session, write(tmp_path, "b.pdf", text_pdf("1 Parties\nA and C.")), contract_type="lease"
    )

    assert await count(session, contracts) == 2


async def test_tc0024_failure_while_storing_clauses_leaves_nothing(
    session: AsyncSession, tmp_path: Path
) -> None:
    text = "1 Parties\nA and B.\n2 Term\n\n3 Payment\nMonthly."
    path = write(tmp_path, "blank-clause.pdf", text_pdf(text))

    with pytest.raises(InvalidContractError):
        await ingest_file(session, path, contract_type="lease")

    assert await count(session, contracts) == 0
    assert await count(session, clauses) == 0


async def test_truth_json_with_an_unknown_type_is_refused_with_a_message(
    session: AsyncSession, tmp_path: Path
) -> None:
    write(tmp_path, "lorry-01.pdf", text_pdf("1 Parties\nA and B."))
    (tmp_path / "lorry-01.truth.json").write_text('{"contract_type": "lorry", "title": "Lorry 01"}')

    with pytest.raises(InvalidContractError) as raised:
        await ingest_file(session, tmp_path / "lorry-01.pdf")

    assert (
        raised.value.message
        == "lorry-01.truth.json: contract_type must be lease, vendor or service"
    )
    assert await count(session, contracts) == 0


async def test_loading_logs_the_contract_and_its_clause_count(
    session: AsyncSession, generated: Path
) -> None:
    with capture_logs() as logs:
        await ingest_file(session, generated / "lease-01.pdf")
        await ingest_file(session, generated / "lease-01.pdf")

    events = [(e["event"], e.get("clauses")) for e in logs]
    assert events == [("contract_loaded", 12), ("contract_already_loaded", None)]
