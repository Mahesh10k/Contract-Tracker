"""The dependency that guards every /api route except login (ADR-0017)."""

from typing import Annotated

from fastapi import Depends, Request

from app.auth.service import AuthApi
from app.core.errors import UnauthorizedError
from app.db.repositories.users import UserRecord

COOKIE_NAME = "ct_session"


def get_auth_service(request: Request) -> AuthApi:
    """The AuthService the lifespan built; tests override this dependency."""
    service: AuthApi = request.app.state.auth_service
    return service


async def require_user(
    request: Request, service: Annotated[AuthApi, Depends(get_auth_service)]
) -> UserRecord:
    """The signed-in account, or a 401 the page turns into the login screen."""
    token = request.cookies.get(COOKIE_NAME)
    user = await service.user_for_token(token) if token else None
    if user is None:
        msg = "Sign in to continue."
        raise UnauthorizedError(msg)
    return user
