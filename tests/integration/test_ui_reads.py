"""The reads behind the Streamlit page (US-00-007 AC-2, US-00-008 AC-1, TC-0125)."""

from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories import contracts as contract_repo
from app.db.repositories import extractions as field_repo
from app.domain.contracts import FieldRow, StoredClause
from app.ingestion.service import ingest_file

pytestmark = pytest.mark.integration

DATA = Path(__file__).parents[2] / "data" / "contracts"
FIELDS = ("parties", "effective_date", "term", "auto_renewal", "notice_period")


def accepted(name: str, clause: StoredClause) -> FieldRow:
    return FieldRow(
        name, f"value of {name}", f"Quote of {name}.", clause.number, clause.id, "accepted", None
    )


def held(name: str, reason: str) -> FieldRow:
    return FieldRow(name, f"value of {name}", None, "9", None, "needs_review", reason)


# TC-0125
async def test_tc0125_fields_of_reads_five_rows_with_status_and_reason(
    session: AsyncSession,
) -> None:
    contract = (await ingest_file(session, DATA / "lease-01.pdf")).contract_id
    clause = (await contract_repo.clauses_of(session, contract))[0]
    rows = [accepted(n, clause) for n in FIELDS[:-1]] + [held("notice_period", "quote_not_found")]
    await field_repo.upsert_extractions(session, contract, rows, prompt_version="v2", model_id="m")

    stored = await field_repo.fields_of(session, contract, FIELDS)

    assert [f.field_name for f in stored] == list(FIELDS)
    assert stored[-1].review_reason == "quote_not_found"
    assert {f.contract_title for f in stored} == {"Lease Agreement 01"}


async def test_held_and_usable_fields_split_by_status(session: AsyncSession) -> None:
    contract = (await ingest_file(session, DATA / "lease-01.pdf")).contract_id
    clause = (await contract_repo.clauses_of(session, contract))[0]
    rows = [accepted("parties", clause), held("term", "could_not_parse")]
    await field_repo.upsert_extractions(session, contract, rows, prompt_version="v2", model_id="m")

    waiting = await field_repo.held_fields(session, FIELDS)
    usable = await field_repo.usable_fields(session, FIELDS)

    assert [(f.field_name, f.review_reason) for f in waiting] == [("term", "could_not_parse")]
    assert [f.field_name for f in usable] == ["parties"]


async def test_list_contracts_shows_title_type_and_file(session: AsyncSession) -> None:
    await ingest_file(session, DATA / "vendor-07.pdf")

    listed = await contract_repo.list_contracts(session)

    assert [(c.title, c.contract_type, c.source_filename) for c in listed] == [
        ("Supply Agreement 07", "vendor", "vendor-07.pdf")
    ]
