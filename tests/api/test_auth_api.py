"""Login, logout and the guard on every other route (ADR-0017, TC-0197 to TC-0200)."""

import uuid

import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.auth.deps import COOKIE_NAME, get_auth_service, require_user
from app.api.ui.router import get_ui_service
from app.core.config import Settings
from app.core.errors import InvalidCredentialsError
from app.db.repositories.users import UserRecord
from app.main import create_app
from tests.api.fakes import FakeService

USER = UserRecord(uuid.uuid4(), "owner@example.com", "x", 0, None, None)
RIGHT_ONE = "right-password-1"
GOOD_COOKIE = "good-token"


class FakeAuth:
    """Knows one account, owner@example.com with RIGHT_ONE, and one token."""

    async def login(self, email: str, password: str) -> tuple[UserRecord, str]:
        if (email, password) != ("owner@example.com", RIGHT_ONE):
            msg = "Wrong email or password, or the account is locked for a few minutes."
            raise InvalidCredentialsError(msg)
        return USER, GOOD_COOKIE

    async def user_for_token(self, token: str) -> UserRecord | None:
        return USER if token == GOOD_COOKIE else None


@pytest.fixture
def guarded(app: FastAPI) -> FastAPI:
    """The app with the real guard (the shared fixture replaces it) and a fake login service."""
    app.dependency_overrides.pop(require_user, None)
    app.dependency_overrides[get_auth_service] = FakeAuth
    app.dependency_overrides[get_ui_service] = FakeService
    return app


def login_body(email: str = "owner@example.com", password: str = RIGHT_ONE) -> dict[str, str]:
    return {"email": email, "password": password}


# TC-0197
async def test_tc0197_login_sets_an_http_only_same_site_cookie(
    guarded: FastAPI, client: AsyncClient
) -> None:
    response = await client.post("/api/auth/login", json=login_body("  OWNER@example.com "))

    assert response.status_code == 200
    assert response.json() == {"email": "owner@example.com"}
    cookie = response.headers["set-cookie"]
    assert f"{COOKIE_NAME}={GOOD_COOKIE}" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    assert "Secure" not in cookie
    assert response.headers["cache-control"] == "no-store"


async def test_tc0197_the_cookie_is_secure_in_production() -> None:
    settings = Settings.model_validate(
        {
            "env": "production",
            "session_secret": "p" * 40,
            "database_url": "postgresql+asyncpg://u:p@localhost/db",
        }
    )
    application = create_app(settings)
    async with LifespanManager(application):
        application.dependency_overrides[get_auth_service] = FakeAuth
        transport = ASGITransport(app=application)
        async with AsyncClient(transport=transport, base_url="http://t") as client:
            response = await client.post("/api/auth/login", json=login_body())

    assert "Secure" in response.headers["set-cookie"]


# TC-0198
@pytest.mark.parametrize(
    "body",
    [
        {"email": "", "password": "x"},
        {"email": "not-an-email", "password": "x"},
        {"email": "owner@example.com", "password": ""},
        {"email": "owner@example.com", "password": "x" * 129},
        {"email": "owner@example.com"},
        {"email": "owner@example.com", "password": "x", "admin": True},
    ],
)
async def test_tc0198_a_badly_formed_login_is_refused_before_any_check(
    guarded: FastAPI, client: AsyncClient, body: dict[str, object]
) -> None:
    response = await client.post("/api/auth/login", json=body)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert "set-cookie" not in response.headers


async def test_tc0198_a_wrong_login_is_a_401_with_one_message(
    guarded: FastAPI, client: AsyncClient
) -> None:
    unknown = await client.post("/api/auth/login", json=login_body("nobody@example.com"))
    wrong = await client.post("/api/auth/login", json=login_body(password="nope-nope-nope"))

    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json()["error"]["code"] == "invalid_credentials"
    assert unknown.json()["error"]["message"] == wrong.json()["error"]["message"]
    assert "set-cookie" not in wrong.headers


# TC-0199
@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/api/contracts"),
        ("GET", "/api/review"),
        ("GET", "/api/auth/me"),
        ("POST", "/api/contracts/golden"),
    ],
)
async def test_tc0199_without_a_session_every_route_is_a_401(
    guarded: FastAPI, client: AsyncClient, method: str, path: str
) -> None:
    response = await client.request(method, path)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


async def test_tc0199_with_a_good_session_the_routes_answer(
    guarded: FastAPI, client: AsyncClient
) -> None:
    client.cookies.set(COOKIE_NAME, GOOD_COOKIE)

    assert (await client.get("/api/contracts")).status_code == 200
    assert (await client.get("/api/auth/me")).json() == {"email": "owner@example.com"}


async def test_tc0199_a_bad_token_is_a_401(guarded: FastAPI, client: AsyncClient) -> None:
    client.cookies.set(COOKIE_NAME, "forged")

    assert (await client.get("/api/contracts")).status_code == 401


# TC-0200
async def test_tc0200_logout_clears_the_cookie(guarded: FastAPI, client: AsyncClient) -> None:
    response = await client.post("/api/auth/logout")

    assert response.status_code == 200
    assert "Max-Age=0" in response.headers["set-cookie"]
