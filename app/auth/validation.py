"""The rules for an email address and a new password, shared by the API and the command line."""

import re

EMAIL_MAX_LENGTH = 254
PASSWORD_MAX_LENGTH = 128
NEW_PASSWORD_MIN_LENGTH = 10
_EMAIL = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}$")


def normalise_email(raw: str) -> str:
    """The address trimmed and lower-cased; raises ValueError with a readable reason."""
    email = raw.strip().lower()
    if not email:
        msg = "Enter your email address."
        raise ValueError(msg)
    if len(email) > EMAIL_MAX_LENGTH or not _EMAIL.match(email):
        msg = "Enter a valid email address."
        raise ValueError(msg)
    return email


def password_problems(password: str, email: str) -> list[str]:
    """Why a new password is refused; empty when it is acceptable."""
    problems: list[str] = []
    if len(password) < NEW_PASSWORD_MIN_LENGTH:
        problems.append(f"Use at least {NEW_PASSWORD_MIN_LENGTH} characters.")
    if len(password) > PASSWORD_MAX_LENGTH:
        problems.append(f"Use at most {PASSWORD_MAX_LENGTH} characters.")
    if len(set(password)) < 4:
        problems.append("Use at least 4 different characters.")
    local = email.split("@", 1)[0]
    if len(local) >= 3 and local in password.lower():
        problems.append("Do not include the part of your email before the @.")
    return problems
