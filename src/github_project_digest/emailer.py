"""SMTP delivery for rendered digest emails."""

from __future__ import annotations

from dataclasses import dataclass
from email.message import EmailMessage
import smtplib
import ssl


@dataclass(frozen=True)
class SmtpConfig:
    """@class SmtpConfig
    @brief Immutable SMTP settings for one digest delivery.
    @details
    `SmtpConfig` keeps email delivery configuration separate from digest
    rendering and GitHub querying.  The digest pipeline can therefore render to
    STDOUT without SMTP settings, or deliver the same rendered text and HTML
    bodies when a recipient is supplied through `GITHUB_USER`.

    The class supports both STARTTLS and implicit SSL because different SMTP
    providers expose different secure transport conventions.  Username and
    password remain optional so the tool can also work with trusted relays that
    do not require application-level authentication.
    """

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
    """@fn send_digest_email(config, text_body, html_body=None)
    @brief Send a rendered digest email through SMTP.
    @details
    The digest is sent with the plain-text body always present.  When an HTML
    body is supplied, it is added as an alternate representation so email clients
    can choose the best display form while still preserving a readable fallback.

    SMTP transport behavior is selected from `SmtpConfig`: implicit SSL is used
    when requested, otherwise the function connects with ordinary SMTP and then
    upgrades with STARTTLS when configured.

    @param config SMTP connection, sender, recipient, subject, and security
                  settings for this delivery.
    @param text_body Plain-text digest body.  This is always included.
    @param html_body Optional HTML digest body to include as an alternate part.
    @returns None.

    @par Examples
    @code
    send_digest_email(config, text_output, html_output)
    @endcode
    """

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
    """@fn _login_if_configured(server, config)
    @brief Authenticate to SMTP when both login values were supplied.
    @details
    SMTP login values are treated as a pair.  Supplying only one is usually a
    configuration mistake, so the function fails before attempting delivery.
    When neither value is supplied, the function leaves the session unchanged to
    support trusted relays and local SMTP infrastructure.

    @param server Active SMTP or SMTP_SSL connection.
    @param config SMTP configuration that may include login values.
    @returns None.

    @par Examples
    @code
    _login_if_configured(server, config)
    @endcode
    """

    if config.username or config.password:
        if not config.username or not config.password:
            raise ValueError("SMTP_USERNAME and SMTP_PASSWORD must be supplied together")
        server.login(config.username, config.password)
