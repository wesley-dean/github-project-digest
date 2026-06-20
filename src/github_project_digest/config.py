"""Configuration loading for github-project-digest."""

from __future__ import annotations

from dataclasses import dataclass
import os

from dotenv import load_dotenv

from github_project_digest.emailer import SmtpConfig


DEFAULT_FILTER = "sprint:@current assignee:@user is:issue state:open"


@dataclass(frozen=True)
class Config:
    """Runtime configuration loaded from environment variables."""

    github_token: str
    project_owner: str
    project_number: int
    project_owner_type: str
    github_user: str
    recipient_email: str | None
    filter_query: str
    output_format: str
    text_template: str
    html_template: str
    page_size: int
    field_value_limit: int
    smtp: SmtpConfig | None


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc



def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean value")


def _optional_env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _selected_user_value() -> str:
    """Return the requested digest assignee specification.

    GITHUB_USER may be either a GitHub login, @me, or a compound value in
    the form username:email@example.com. The ordinary shell USER variable is
    intentionally ignored so a login shell cannot accidentally change the
    digest assignee.
    """

    return _optional_env("GITHUB_USER") or "@me"


def _split_user_and_email(value: str) -> tuple[str, str | None]:
    """Split a GITHUB_USER value into GitHub login and optional destination email."""

    user_value = (value or "@me").strip() or "@me"
    if ":" not in user_value:
        return user_value, None

    user, email = user_value.split(":", 1)
    user = user.strip() or "@me"
    email = email.strip() or None
    return user, email


def _load_smtp_config(recipient: str | None) -> SmtpConfig | None:
    if not recipient:
        return None

    host = _required("SMTP_HOST")
    sender = _required("SMTP_FROM")
    use_ssl = _bool_env("SMTP_USE_SSL", False)
    default_port = 465 if use_ssl else 587

    return SmtpConfig(
        host=host,
        port=_int_env("SMTP_PORT", default_port),
        sender=sender,
        recipient=recipient,
        subject=os.getenv("SMTP_SUBJECT", "GitHub Project Digest"),
        username=_optional_env("SMTP_USERNAME"),
        password=_optional_env("SMTP_PASSWORD"),
        use_tls=_bool_env("SMTP_USE_TLS", not use_ssl),
        use_ssl=use_ssl,
        timeout=_int_env("SMTP_TIMEOUT", 30),
    )

def load_config() -> Config:
    """Load configuration from .env and the process environment."""

    load_dotenv(override=True)

    owner_type = os.getenv("GITHUB_PROJECT_OWNER_TYPE", "organization").lower().strip()
    if owner_type not in {"organization", "user"}:
        raise ValueError("GITHUB_PROJECT_OWNER_TYPE must be 'organization' or 'user'")

    output_format = os.getenv("DIGEST_OUTPUT_FORMAT", "text").lower().strip()
    if output_format not in {"text", "html", "json", "yaml"}:
        raise ValueError("DIGEST_OUTPUT_FORMAT must be one of: text, html, json, yaml")

    raw_github_user = _selected_user_value()
    github_user, recipient_email = _split_user_and_email(raw_github_user)

    return Config(
        github_token=_required("GITHUB_TOKEN"),
        project_owner=_required("GITHUB_PROJECT_OWNER"),
        project_number=_int_env("GITHUB_PROJECT_NUMBER", 0),
        project_owner_type=owner_type,
        github_user=github_user,
        recipient_email=recipient_email,
        filter_query=os.getenv("GITHUB_PROJECT_FILTER", DEFAULT_FILTER),
        output_format=output_format,
        text_template=os.getenv("DIGEST_TEMPLATE_TEXT", "digest.txt.j2"),
        html_template=os.getenv("DIGEST_TEMPLATE_HTML", "digest.html.j2"),
        page_size=_int_env("GITHUB_PROJECT_PAGE_SIZE", 50),
        field_value_limit=_int_env("GITHUB_PROJECT_FIELD_VALUE_LIMIT", 50),
        smtp=_load_smtp_config(recipient_email),
    )
