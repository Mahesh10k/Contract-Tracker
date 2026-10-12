"""Email and password rules (ADR-0017, TC-0192, TC-0193)."""

import pytest

from app.auth.validation import normalise_email, password_problems


# TC-0192
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("  Owner@Example.COM ", "owner@example.com"),
        ("a.b+c@sub.example.org", "a.b+c@sub.example.org"),
    ],
)
def test_tc0192_a_valid_email_is_trimmed_and_lower_cased(raw: str, expected: str) -> None:
    assert normalise_email(raw) == expected


@pytest.mark.parametrize(
    "raw",
    ["", "   ", "plain", "a@b", "a@@b.com", "a b@c.com", "@c.com", "a@c.", "x" * 250 + "@a.co"],
)
def test_tc0192_a_malformed_email_is_refused_with_a_reason(raw: str) -> None:
    with pytest.raises(ValueError, match="email"):
        normalise_email(raw)


# TC-0193
def test_tc0193_a_new_password_needs_length_variety_and_not_the_email_name() -> None:
    assert password_problems("tr1ckier-Passphrase", "owner@example.com") == []
    assert password_problems("short", "owner@example.com") == ["Use at least 10 characters."]
    assert "Use at least 4 different characters." in password_problems("aaaaaaaaaaaa", "o@x.com")
    assert any("email" in p for p in password_problems("my-owner-secret1", "owner@example.com"))
    assert any("at most" in p for p in password_problems("x1" * 70, "o@x.com"))
