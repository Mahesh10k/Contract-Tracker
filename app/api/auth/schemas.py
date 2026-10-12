"""Request and response bodies of the login routes."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.auth.validation import PASSWORD_MAX_LENGTH, normalise_email


class LoginIn(BaseModel):
    """An email and a password. The password is never trimmed or logged."""

    model_config = ConfigDict(extra="forbid")

    email: str
    password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)

    @field_validator("email")
    @classmethod
    def _valid_email(cls, value: str) -> str:
        return normalise_email(value)


class UserOut(BaseModel):
    """The signed-in account."""

    email: str


class MessageOut(BaseModel):
    """A short confirmation."""

    message: str
