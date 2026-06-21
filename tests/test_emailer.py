from __future__ import annotations

import smtplib
from typing import Any

import pytest

from github_project_digest.emailer import SmtpConfig, send_digest_email


class FakeSMTP:
    instances: list["FakeSMTP"] = []

    def __init__(self, host: str, port: int, timeout: int | None = None, context: Any | None = None) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.context = context
        self.ehlo_count = 0
        self.started_tls = False
        self.login_args: tuple[str, str] | None = None
        self.message = None
        FakeSMTP.instances.append(self)

    def __enter__(self) -> "FakeSMTP":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def ehlo(self) -> None:
        self.ehlo_count += 1

    def starttls(self, context: Any | None = None) -> None:
        self.started_tls = True
        self.context = context

    def login(self, username: str, password: str) -> None:
        self.login_args = (username, password)

    def send_message(self, message) -> None:
        self.message = message


def test_send_digest_email_builds_multipart_tls_message(monkeypatch) -> None:
    FakeSMTP.instances.clear()
    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    config = SmtpConfig(
        host="smtp.example.com",
        port=587,
        sender="from@example.com",
        recipient="to@example.com",
        subject="Digest",
        username="user",
        password="pass",
        use_tls=True,
    )

    send_digest_email(config, "plain body", "<p>html body</p>")

    server = FakeSMTP.instances[0]
    assert server.host == "smtp.example.com"
    assert server.started_tls is True
    assert server.login_args == ("user", "pass")
    assert server.message["From"] == "from@example.com"
    assert server.message["To"] == "to@example.com"
    assert server.message["Subject"] == "Digest"
    assert server.message.is_multipart()


def test_send_digest_email_requires_username_and_password_together(monkeypatch) -> None:
    FakeSMTP.instances.clear()
    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    config = SmtpConfig(
        host="smtp.example.com",
        port=587,
        sender="from@example.com",
        recipient="to@example.com",
        subject="Digest",
        username="user",
        password=None,
    )

    with pytest.raises(ValueError, match="SMTP_USERNAME and SMTP_PASSWORD"):
        send_digest_email(config, "plain body")
