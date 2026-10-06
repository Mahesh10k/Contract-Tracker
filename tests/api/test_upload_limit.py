"""The upload limit is enforced from Content-Length, before the body is read (REQ-044, review 9)."""

from collections.abc import AsyncIterator, Iterator

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from app.api.ui.router import get_ui_service
from app.ui.service import MAX_UPLOAD_BYTES
from tests.api.fakes import FakeService


@pytest.fixture
def service(app: FastAPI) -> Iterator[FakeService]:
    fake = FakeService()
    app.dependency_overrides[get_ui_service] = lambda: fake
    yield fake
    app.dependency_overrides.clear()


# TC-0175
async def test_a_declared_length_far_over_the_limit_is_refused_without_reading_the_body(
    client: AsyncClient, service: FakeService
) -> None:
    read: list[bytes] = []

    async def body() -> AsyncIterator[bytes]:
        read.append(b"x")
        yield b"x"

    response = await client.post(
        "/api/contracts",
        content=body(),
        headers={
            "content-length": str(MAX_UPLOAD_BYTES * 4),
            "content-type": "multipart/form-data; boundary=x",
        },
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "upload_too_large"
    assert service.calls == []
    assert read == [], "the body was pulled from the client before the refusal"


# TC-0176
async def test_an_upload_with_no_declared_length_is_refused_with_411(
    client: AsyncClient, service: FakeService
) -> None:
    async def chunks() -> AsyncIterator[bytes]:
        yield b"--x\r\n"
        yield b"--x--\r\n"

    response = await client.post(
        "/api/contracts",
        content=chunks(),
        headers={"content-type": "multipart/form-data; boundary=x", "transfer-encoding": "chunked"},
    )

    assert response.status_code == 411
    assert response.json()["error"]["code"] == "length_required"
    assert service.calls == []


async def test_other_routes_are_not_subject_to_the_upload_limit(
    client: AsyncClient, service: FakeService
) -> None:
    response = await client.post(
        "/api/ask", json={"question": "Which law governs Supply Agreement 08?"}
    )

    assert response.status_code == 200
