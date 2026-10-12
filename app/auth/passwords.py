"""Password hashing with scrypt from the standard library (ADR-0017). No new dependency.

A stored hash reads `scrypt$N$r$p$salt$hash` (base64), so the cost can be raised later and old
hashes still verify. Hashing takes tens of milliseconds, so async callers run it in a thread.
"""

import base64
import hashlib
import hmac
import secrets
from functools import cache

N = 2**14
R = 8
P = 1
KEY_LENGTH = 32
SALT_LENGTH = 16
_MAX_MEMORY = 64 * 1024 * 1024


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _derive(password: str, salt: bytes, n: int, r: int, p: int) -> bytes:
    return hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=n, r=r, p=p, dklen=KEY_LENGTH, maxmem=_MAX_MEMORY
    )


def hash_password(password: str) -> str:
    """A salted hash of the password, safe to store."""
    salt = secrets.token_bytes(SALT_LENGTH)
    return f"scrypt${N}${R}${P}${_b64(salt)}${_b64(_derive(password, salt, N, R, P))}"


def verify_password(password: str, stored: str) -> bool:
    """True when the password matches the stored hash; a malformed hash never matches."""
    try:
        scheme, n, r, p, salt, expected = stored.split("$")
        if scheme != "scrypt":
            return False
        derived = _derive(password, base64.b64decode(salt), int(n), int(r), int(p))
        return hmac.compare_digest(derived, base64.b64decode(expected))
    except ValueError:
        return False


@cache
def dummy_hash() -> str:
    """A hash to check against when the email is unknown, so timing does not reveal accounts."""
    return hash_password("a password nobody has")
