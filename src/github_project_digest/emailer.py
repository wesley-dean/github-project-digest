"""SMTP delivery for rendered digest emails."""

from __future__ import annotations

from dataclasses import dataclass
from email.message import EmailMessage
import smtplib
import ssl


@dataclass(frozen=True)
class SmtpConfig:
    """SMTP settings used to deliver a single digest email."""

    host: str
    port: int
    sender: str
    recipient: str
    subject: str
    username: str | None = None
    password: str | None = None
    use_tls: bool = True
    use_ssl: bool = False
    timeout: int = 30


def send_digest_email(config: SmtpConfig, text_body: str, html_body: str | None = None) -> None:
    """Send the digest as a multipart email through SMTP."""

    message = EmailMessage()
    message["From"] = config.sender
    message["To"] = config.recipient
    message["Subject"] = config.subject
    message.set_content(text_body)

    if html_body:
        message.add_alternative(html_body, subtype="html")

    context = ssl.create_default_context()

    if config.use_ssl:
        with smtplib.SMTP_SSL(config.host, config.port, timeout=config.timeout, context=context) as server:
            _login_if_configured(server, config)
            server.send_message(message)
        return

    with smtplib.SMTP(config.host, config.port, timeout=config.timeout) as server:
        server.ehlo()
        if config.use_tls:
            server.starttls(context=context)
            server.ehlo()
        _login_if_configured(server, config)
        server.send_message(message)


def _login_if_configured(server: smtplib.SMTP, config: SmtpConfig) -> None:
    """Authenticate to SMTP when username/password were supplied."""

    if config.username or config.password:
        if not config.username or not config.password:
            raise ValueError("SMTP_USERNAME and SMTP_PASSWORD must be supplied together")
        server.login(config.username, config.password)
