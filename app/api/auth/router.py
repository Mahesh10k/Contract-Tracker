"""Login, logout and who-am-I (ADR-0017). Users are created from the command line, not here."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from app.api.auth.deps import COOKIE_NAME, get_auth_service, require_user
from app.api.auth.schemas import LoginIn, MessageOut, UserOut
from app.auth.service import AuthApi
from app.core.errors import ErrorEnvelope
from app.db.repositories.users import UserRecord

router = APIRouter(
    prefix="/api/auth", tags=["auth"], responses={"default": {"model": ErrorEnvelope}}
)


@router.post("/login", response_model=UserOut)
async def login(
    body: LoginIn,
    request: Request,
    response: Response,
    service: Annotated[AuthApi, Depends(get_auth_service)],
) -> UserOut:
    """Check the password and set the session cookie."""
    user, token = await service.login(body.email, body.password)
    settings = request.app.state.settings
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=settings.session_ttl_hours * 3600,
        httponly=True,
        secure=settings.env == "production",
        samesite="lax",
        path="/",
    )
    response.headers["Cache-Control"] = "no-store"
    return UserOut(email=user.email)


@router.post("/logout", response_model=MessageOut)
async def logout(response: Response) -> MessageOut:
    """Clear the session cookie. A copied token still works until it expires (ADR-0017)."""
    response.delete_cookie(COOKIE_NAME, path="/")
    return MessageOut(message="Signed out.")


@router.get("/me", response_model=UserOut)
async def me(user: Annotated[UserRecord, Depends(require_user)]) -> UserOut:
    """Who the session belongs to; the page calls this on load to choose login or the app."""
    return UserOut(email=user.email)
