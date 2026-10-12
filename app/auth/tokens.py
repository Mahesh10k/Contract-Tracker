"""Signed session tokens (ADR-0017): `<payload>.<signature>`, HMAC-SHA256, no server-side state.

The payload holds the user id and an expiry. A changed payload, a wrong key or an old expiry
reads as no session. Logging out clears the cookie; a copied token works until it expires.
"""

import base64
import hashlib
import hmac
import json
import uuid
from datetime import UTC, datetime, timedelta


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _sign(payload: str, secret: str) -> str:
    return _b64(hmac.new(secret.encode("utf-8"), payload.encode("ascii"), hashlib.sha256).digest())


def issue_token(user_id: uuid.UUID, secret: str, now: datetime, ttl: timedelta) -> str:
    """A token for this user that stops working after `ttl`."""
    body = {"sub": str(user_id), "exp": int((now + ttl).timestamp())}
    payload = _b64(json.dumps(body, separators=(",", ":")).encode("utf-8"))
    return f"{payload}.{_sign(payload, secret)}"


def read_token(token: str, secret: str, now: datetime | None = None) -> uuid.UUID | None:
    """The user id the token was issued for, or None when it is forged, damaged or expired."""
    payload, dot, signature = token.partition(".")
    if not dot or not hmac.compare_digest(_sign(payload, secret), signature):
        return None
    try:
        body = json.loads(_unb64(payload))
        expires = datetime.fromtimestamp(int(body["exp"]), tz=UTC)
        user_id = uuid.UUID(str(body["sub"]))
    except (ValueError, KeyError, TypeError):
        return None
    return user_id if expires > (now or datetime.now(UTC)) else None
