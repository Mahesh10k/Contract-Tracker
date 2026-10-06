"""The JSON API under the React page (US-00-007, ADR-0016, TC-0126 to TC-0134)."""

import re
import uuid
from collections.abc import Iterator
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import AsyncClient, Response

from app.api.ui.router import get_ui_service
from tests.api.fakes import LEASE, FakeService

PDF = Path("data/contracts/lease-01.pdf").read_bytes()
MAX_BYTES = 5 * 1024 * 1024


@pytest.fixture
def service(app: FastAPI) -> Iterator[FakeService]:
    fake = FakeService()
    app.dependency_overrides[get_ui_service] = lambda: fake
    yield fake
    app.dependency_overrides.clear()


async def post_pdf(
    client: AsyncClient, name: str, data: bytes, contract_type: str = "lease"
) -> Response:
    return await client.post(
        "/api/contracts",
        files={"file": (name, data, "application/pdf")},
        data={"contract_type": contract_type},
    )


# TC-0126
async def test_tc0126_a_valid_pdf_with_a_type_is_accepted(
    client: AsyncClient, service: FakeService
) -> None:
    response = await post_pdf(client, "lease-01.pdf", PDF)

    assert response.status_code == 201
    assert response.json() == {"message": "Lease Agreement 01"}
    assert service.calls == [("upload", "lease-01.pdf", PDF, "lease")]


# TC-0127
async def test_tc0127_a_file_over_five_megabytes_is_refused(
    client: AsyncClient, service: FakeService
) -> None:
    big = b"%PDF" + b"0" * MAX_BYTES

    response = await post_pdf(client, "big.pdf", big)

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "upload_too_large"
    assert service.calls == []


async def test_a_file_of_exactly_five_megabytes_is_accepted(
    client: AsyncClient, service: FakeService
) -> None:
    exact = b"%PDF" + b"0" * (MAX_BYTES - 4)

    response = await post_pdf(client, "edge.pdf", exact)

    assert response.status_code == 201
    assert len(service.calls) == 1


# TC-0128
async def test_tc0128_a_file_that_is_not_a_pdf_is_refused(
    client: AsyncClient, service: FakeService
) -> None:
    response = await post_pdf(client, "notes.pdf", b"hello\n")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "upload_not_pdf"
    assert service.calls == []


async def test_an_unknown_contract_type_is_a_validation_error(
    client: AsyncClient, service: FakeService
) -> None:
    response = await post_pdf(client, "a.pdf", PDF, "mortgage")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert service.calls == []


# TC-0129
async def test_tc0129_a_path_in_the_file_name_is_reduced_to_its_base(
    client: AsyncClient, service: FakeService
) -> None:
    await post_pdf(client, "../../etc/evil.pdf", PDF)

    assert service.calls[0][1] == "evil.pdf"


async def test_golden_contracts_are_loaded_in_one_call(
    client: AsyncClient, service: FakeService
) -> None:
    response = await client.post("/api/contracts/golden")

    assert response.status_code == 200
    assert response.json() == {
        "loaded": ["Lease Agreement 01", "Supply Agreement 07 (already loaded)"]
    }


async def test_contracts_are_listed(client: AsyncClient, service: FakeService) -> None:
    response = await client.get("/api/contracts")

    assert response.json() == [
        {
            "id": str(LEASE.id),
            "title": "Lease Agreement 01",
            "contract_type": "lease",
            "source_filename": "lease-01.pdf",
        }
    ]


# TC-0130
async def test_tc0130_fields_carry_status_reason_quote_and_clause(
    client: AsyncClient, service: FakeService
) -> None:
    response = await client.get(f"/api/contracts/{LEASE.id}/fields")

    rows = response.json()
    assert len(rows) == 5
    assert {tuple(r) for r in rows} == {
        ("field", "value", "quote", "clause", "status", "review_reason")
    }
    held = next(r for r in rows if r["field"] == "auto_renewal")
    assert (held["status"], held["review_reason"], held["value"]) == (
        "needs_review",
        "value_missing",
        None,
    )


# TC-0131
async def test_tc0131_deadlines_have_iso_dates_and_integer_days(
    client: AsyncClient, service: FakeService
) -> None:
    response = await client.get("/api/deadlines", params={"today": "2026-10-05"})

    rows = response.json()
    assert [r["due"] for r in rows] == ["2026-12-01", "2026-12-31"]
    assert all(re.fullmatch(r"\d{4}-\d{2}-\d{2}", r["due"]) for r in rows)
    assert [r["days_left"] for r in rows] == [57, 87]
    assert rows[0]["kind"] == "notice_deadline"


# TC-0132
async def test_tc0132_a_bad_today_is_422_and_an_absent_one_means_today(
    client: AsyncClient, service: FakeService
) -> None:
    bad = await client.get("/api/deadlines", params={"today": "31-02-2026"})
    absent = await client.get("/api/deadlines")

    assert bad.status_code == 422
    assert bad.json()["error"]["code"] == "validation_error"
    assert absent.status_code == 200
    assert service.calls == [("deadlines", datetime.now(UTC).date())]


async def test_review_lists_held_fields_with_their_reason(
    client: AsyncClient, service: FakeService
) -> None:
    response = await client.get("/api/review")

    assert response.json() == [
        {
            "contract": "Lease Agreement 01",
            "field": "auto_renewal",
            "value": None,
            "quote": None,
            "reason": "value_missing",
        }
    ]


async def test_extract_reports_the_counts(client: AsyncClient, service: FakeService) -> None:
    response = await client.post(f"/api/contracts/{LEASE.id}/extract")

    assert response.json() == {"message": "4 accepted, 1 need review"}


# TC-0133
async def test_tc0133_an_unknown_contract_is_a_404_envelope(
    client: AsyncClient, service: FakeService
) -> None:
    response = await client.post(f"/api/contracts/{uuid.uuid4()}/extract")

    assert response.status_code == 404
    body = response.json()["error"]
    assert body["code"] == "not_found"
    assert "Traceback" not in body["message"]


async def test_ask_returns_the_answer_with_each_citation_and_its_clause_text(
    client: AsyncClient, service: FakeService
) -> None:
    response = await client.post(
        "/api/ask", json={"question": "Which law governs Supply Agreement 08?"}
    )

    assert response.status_code == 200
    assert response.json() == {
        "text": "Supply Agreement 08 is governed by the laws of the State of California.",
        "refused": False,
        "citations": [
            {
                "contract": "Supply Agreement 08",
                "clause": "8",
                "text": "This Agreement is governed by the laws of the State of California.",
            }
        ],
    }


# TC-0134
async def test_tc0134_an_empty_question_is_422_and_a_service_failure_is_the_envelope(
    client: AsyncClient, service: FakeService
) -> None:
    empty = await client.post("/api/ask", json={"question": ""})
    early = await client.post("/api/ask", json={"question": "Who pays?"})

    assert empty.status_code == 422
    assert early.status_code == 501
    assert early.json()["error"]["message"] == "Questions cannot be answered right now."


async def test_ask_refuses_unknown_fields_in_the_body(
    client: AsyncClient, service: FakeService
) -> None:
    response = await client.post("/api/ask", json={"question": "Who pays?", "extra": 1})

    assert response.status_code == 422


async def test_reminders_surface_the_services_message(
    client: AsyncClient, service: FakeService
) -> None:
    response = await client.post("/api/reminders/send", json={"today": "2026-10-05"})

    assert response.status_code == 400
    assert response.json()["error"]["message"] == "Reminder emails arrive with Checkpoint 5."


# TC-0180
async def test_a_deadlines_request_without_today_honours_pretend_today_from_the_settings(
    app: FastAPI, client: AsyncClient, service: FakeService
) -> None:
    app.state.settings = app.state.settings.model_copy(update={"pretend_today": date(2028, 10, 1)})

    await client.get("/api/deadlines")

    assert service.calls == [("deadlines", date(2028, 10, 1))]
