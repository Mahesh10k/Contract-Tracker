"""Signed session tokens (ADR-0017, TC-0190, TC-0191)."""

import uuid
from datetime import UTC, datetime, timedelta

from app.auth.tokens import issue_token, read_token

SECRET = "s" * 40
NOW = datetime(2026, 10, 12, 9, 0, tzinfo=UTC)
USER = uuid.UUID("6b1f3d2e-0c4a-4d57-9a3b-1f2e3d4c5b6a")


# TC-0190
def test_tc0190_a_token_reads_back_to_its_user_until_it_expires() -> None:
    token = issue_token(USER, SECRET, NOW, timedelta(hours=12))

    assert read_token(token, SECRET, NOW + timedelta(hours=11, minutes=59)) == USER
    assert read_token(token, SECRET, NOW + timedelta(hours=12)) is None


# TC-0191
def test_tc0191_forged_damaged_and_foreign_tokens_read_as_no_session() -> None:
    token = issue_token(USER, SECRET, NOW, timedelta(hours=12))
    payload, _, signature = token.partition(".")
    other = issue_token(uuid.uuid4(), SECRET, NOW, timedelta(hours=12)).partition(".")[0]

    assert read_token(token, "another secret of 40 characters long!!", NOW) is None
    assert read_token(f"{other}.{signature}", SECRET, NOW) is None
    assert read_token(f"{payload}.{signature[:-2]}AA", SECRET, NOW) is None
    for bad in ("", "nodot", "a.b", ".", f"{payload}.", "!!!.???"):
        assert read_token(bad, SECRET, NOW) is None
