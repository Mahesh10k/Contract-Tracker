"""The SMTP mailer, the `make remind` command and the blank PRETEND_TODAY setting (US-00-006)."""

import smtplib
from datetime import date
from email.message import EmailMessage
from typing import ClassVar

import pytest

from app.core.config import Settings
from app.core.errors import DomainError
from app.reminders import cli
from app.reminders.mailer import SmtpMailer
from app.reminders.service import ReminderDeliveryError


def message() -> EmailMessage:
    mail = EmailMessage()
    mail["Subject"] = "Reminder"
    mail["From"] = "r@x.test"
    mail["To"] = "o@x.test"
    mail.set_content("body")
    return mail


class FakeSmtp:
    sent: ClassVar[list[EmailMessage]] = []

    def __init__(self, host: str, port: int, timeout: float) -> None:
        self.target = (host, port, timeout)

    def __enter__(self) -> "FakeSmtp":
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def send_message(self, mail: EmailMessage) -> None:
        FakeSmtp.sent.append(mail)


async def test_the_mailer_sends_the_message_to_the_configured_host_and_port(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeSmtp.sent = []
    monkeypatch.setattr(smtplib, "SMTP", FakeSmtp)

    await SmtpMailer("localhost", 1025).send(message())

    assert [m["Subject"] for m in FakeSmtp.sent] == ["Reminder"]


@pytest.mark.parametrize("error", [ConnectionRefusedError("refused"), smtplib.SMTPException("bad")])
async def test_a_refused_connection_or_smtp_error_becomes_a_delivery_error_naming_mailhog(
    monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    def refuse(*_args: object, **_kwargs: object) -> None:
        raise error

    monkeypatch.setattr(smtplib, "SMTP", refuse)

    with pytest.raises(ReminderDeliveryError) as raised:
        await SmtpMailer("localhost", 1).send(message())

    assert "MailHog at localhost:1" in raised.value.message
    assert "stays pending" in raised.value.message


class FakeEngine:
    async def dispose(self) -> None:
        pass


class FakeService:
    def __init__(self, outcome: str | DomainError) -> None:
        self.outcome = outcome
        self.days: list[date] = []

    async def send_due_reminders(self, today: date) -> str:
        self.days.append(today)
        if isinstance(self.outcome, DomainError):
            raise self.outcome
        return self.outcome


def wire(monkeypatch: pytest.MonkeyPatch, service: FakeService, pretend: date | None) -> None:
    settings = Settings(
        _env_file=None,
        env="test",
        database_url="postgresql+asyncpg://postgres:postgres@localhost:5432/unused",
        pretend_today=pretend,
    )
    monkeypatch.setattr(cli, "get_settings", lambda: settings)
    monkeypatch.setattr(cli, "make_engine", lambda _s: FakeEngine())
    monkeypatch.setattr(cli, "make_session_factory", lambda _e: object())
    monkeypatch.setattr(cli, "UiService", lambda _settings, _factory: service)


def test_remind_uses_the_given_date_and_prints_the_result(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    service = FakeService("1 reminder sent")
    wire(monkeypatch, service, pretend=date(2028, 10, 1))

    code = cli.main(["--today", "2028-10-31"])

    assert (code, service.days) == (0, [date(2028, 10, 31)])
    assert capsys.readouterr().out == "1 reminder sent (today is 2028-10-31)\n"


def test_remind_falls_back_to_pretend_today_from_the_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = FakeService("No reminders are due.")
    wire(monkeypatch, service, pretend=date(2028, 10, 1))

    cli.main([])

    assert service.days == [date(2028, 10, 1)]


def test_remind_with_mailhog_down_prints_the_message_on_stderr_and_exits_1(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    wire(monkeypatch, FakeService(ReminderDeliveryError("Could not send through MailHog")), None)

    code = cli.main(["--today", "2026-10-31"])

    captured = capsys.readouterr()
    assert code == 1
    assert captured.err == "Could not send through MailHog\n"
    assert captured.out == ""


def test_a_blank_pretend_today_in_the_environment_means_the_real_date(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PRETEND_TODAY", "")

    settings = Settings(
        _env_file=None,
        database_url="postgresql+asyncpg://postgres:postgres@localhost:5432/unused",
    )

    assert settings.pretend_today is None


def test_a_set_pretend_today_is_parsed_as_a_date(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PRETEND_TODAY", "2028-10-31")

    settings = Settings(
        _env_file=None,
        database_url="postgresql+asyncpg://postgres:postgres@localhost:5432/unused",
    )

    assert settings.pretend_today == date(2028, 10, 31)
