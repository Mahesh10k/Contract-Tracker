"""SMTP delivery to MailHog (ADR-0010); MailHog keeps what it gets, nothing reaches a real inbox."""

import smtplib
from email.message import EmailMessage

import anyio

from app.reminders.service import ReminderDeliveryError

TIMEOUT_S = 10.0


class SmtpMailer:
    """Sends one email over plain SMTP; any failure becomes a ReminderDeliveryError."""

    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port

    def _send_sync(self, message: EmailMessage) -> None:
        with smtplib.SMTP(self.host, self.port, timeout=TIMEOUT_S) as smtp:
            smtp.send_message(message)

    async def send(self, message: EmailMessage) -> None:
        try:
            await anyio.to_thread.run_sync(self._send_sync, message)
        except (OSError, smtplib.SMTPException) as exc:
            raise ReminderDeliveryError(
                f"Could not send through MailHog at {self.host}:{self.port}; "
                "the reminder stays pending. Start it with make mail."
            ) from exc
