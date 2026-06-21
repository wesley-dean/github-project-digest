"""@file config.py
@brief Load runtime configuration for github-project-digest.
@details
This module translates environment variables and optional `.env` values into a
single immutable `Config` object.  The configuration layer intentionally keeps
Jenkins, Docker, local shell usage, PAT authentication, GitHub App
authentication, SMTP delivery, template selection, and Project filtering behind
one consistent interface so the rest of the application can operate on typed
values rather than raw process environment strings.

The module also owns the `GITHUB_USER` parsing convention.  A colon-separated
value identifies both the GitHub assignee and the optional email destination,
while a bare login or `@me` keeps the tool in STDOUT-only mode.
"""

from __future__ import annotations

from dataclasses import dataclass
import os

from dotenv import load_dotenv

from github_project_digest.emailer import SmtpConfig
from github_project_digest.github_auth import GitHubAppConfig


DEFAULT_FILTER = "sprint:@current assignee:@user is:issue state:open"


@dataclass(frozen=True)
class Config:
    """@class Config
    @brief Immutable runtime configuration for one digest execution.
    @details
    `Config` is the boundary between the operating environment and the digest
    pipeline.  The rest of the application receives typed values from this
    dataclass instead of reading environment variables directly.  This keeps
    command-line execution, Docker execution, Jenkins execution, PAT auth,
    GitHub App auth, SMTP delivery, and template rendering aligned through one
    configuration contract.
    """

    github_token: str | None
    github_app: GitHubAppConfig
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
    """@fn _required(name)
    @brief Return a required environment variable value.
    @details
    This helper centralizes required-setting validation so missing values fail
    early with a clear message.  It treats empty strings as missing because an
    empty setting is not meaningful for required values such as project owner,
    SMTP host, or sender address.

    @param name Environment variable name to read.
    @returns The configured value.

    @par Examples
    @code
    owner = _required("GITHUB_PROJECT_OWNER")
    @endcode
    """

    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def _int_env(name: str, default: int) -> int:
    """@fn _int_env(name, default)
    @brief Read an integer environment variable with a default.
    @details
    Environment variables arrive as strings, but several settings are numeric:
    project number, page size, field-value limit, SMTP port, and SMTP timeout.
    This helper keeps conversion and error reporting consistent across all of
    those values.

    @param name Environment variable name to read.
    @param default Value to use when the variable is unset or empty.
    @returns Parsed integer value.

    @par Examples
    @code
    page_size = _int_env("GITHUB_PROJECT_PAGE_SIZE", 50)
    @endcode
    """

    value = os.getenv(name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc



def _bool_env(name: str, default: bool) -> bool:
    """@fn _bool_env(name, default)
    @brief Read a boolean environment variable with a default.
    @details
    CI systems and shell environments commonly represent booleans using several
    spellings.  This helper accepts common truthy and falsey values while still
    rejecting ambiguous input so configuration mistakes are visible.

    @param name Environment variable name to read.
    @param default Value to use when the variable is unset or empty.
    @returns Parsed boolean value.

    @par Examples
    @code
    use_ssl = _bool_env("SMTP_USE_SSL", False)
    @endcode
    """

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
    """@fn _optional_env(name)
    @brief Read an optional environment variable.
    @details
    Optional values are normalized by stripping surrounding whitespace and
    converting empty strings to `None`.  This keeps downstream configuration
    checks focused on semantic presence rather than string cleanup.

    @param name Environment variable name to read.
    @returns A stripped string when present, otherwise `None`.

    @par Examples
    @code
    token = _optional_env("GITHUB_TOKEN")
    @endcode
    """

    value = os.getenv(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _selected_user_value() -> str:
    """@fn _selected_user_value()
    @brief Return the requested digest assignee specification.
    @details
    The tool intentionally reads `GITHUB_USER` rather than the shell's ordinary
    `USER` variable.  That choice prevents a login shell, Jenkins agent, or
    container runtime from accidentally changing which GitHub assignee receives
    a digest.  When `GITHUB_USER` is absent, `@me` keeps local use convenient by
    deferring assignee resolution to the authenticated GitHub account.

    @returns The configured GitHub user expression, or `@me` by default.

    @par Examples
    @code
    raw_user = _selected_user_value()
    @endcode
    """

    return _optional_env("GITHUB_USER") or "@me"


def _split_user_and_email(value: str) -> tuple[str, str | None]:
    """@fn _split_user_and_email(value)
    @brief Split a GitHub user expression into assignee and recipient parts.
    @details
    `GITHUB_USER` supports both a bare assignee and a compound `assignee:email`
    form.  The compound form lets shells and Jenkins jobs iterate over users
    without introducing a separate recipients file.  Only the first colon is
    significant so the parser remains predictable.

    @param value Raw `GITHUB_USER` value.
    @returns Tuple containing the GitHub login expression and optional email.

    @par Examples
    @code
    user, email = _split_user_and_email("octocat:octocat@example.com")
    @endcode
    """

    user_value = (value or "@me").strip() or "@me"
    if ":" not in user_value:
        return user_value, None

    user, email = user_value.split(":", 1)
    user = user.strip() or "@me"
    email = email.strip() or None
    return user, email


def _load_smtp_config(recipient: str | None) -> SmtpConfig | None:
    """@fn _load_smtp_config(recipient)
    @brief Build SMTP configuration when email delivery is requested.
    @details
    SMTP delivery is optional.  A missing recipient means the tool should render
    to STDOUT only, which keeps local testing and dry shell runs useful.  When a
    recipient is present, the required SMTP connection values are read and
    validated here before the digest pipeline attempts delivery.

    @param recipient Destination email address parsed from `GITHUB_USER`.
    @returns `SmtpConfig` when delivery is enabled, otherwise `None`.

    @par Examples
    @code
    smtp = _load_smtp_config(recipient_email)
    @endcode
    """

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
    """@fn load_config()
    @brief Load and normalize all runtime configuration.
    @details
    This function is the public entrypoint for configuration.  It loads `.env`
    values, validates constrained settings, parses the selected GitHub user and
    optional recipient email, and returns a single immutable `Config` instance
    for the rest of the digest pipeline.

    Environment access is intentionally concentrated here so GitHub access,
    filtering, rendering, and email delivery can be tested with explicit values
    rather than direct process-state dependencies.

    @returns Fully populated runtime `Config`.

    @par Examples
    @code
    config = load_config()
    @endcode
    """

    load_dotenv(override=True)

    owner_type = os.getenv("GITHUB_PROJECT_OWNER_TYPE", "organization").lower().strip()
    if owner_type not in {"organization", "user"}:
        raise ValueError("GITHUB_PROJECT_OWNER_TYPE must be 'organization' or 'user'")

    output_format = os.getenv("DIGEST_OUTPUT_FORMAT", os.getenv("OUTPUT_FORMAT", "text")).lower().strip()
    if output_format not in {"text", "html", "json", "yaml"}:
        raise ValueError("DIGEST_OUTPUT_FORMAT/OUTPUT_FORMAT must be one of: text, html, json, yaml")

    raw_github_user = _selected_user_value()
    github_user, recipient_email = _split_user_and_email(raw_github_user)

    return Config(
        github_token=_optional_env("GITHUB_TOKEN"),
        github_app=GitHubAppConfig(
            app_id=_optional_env("GITHUB_APP_ID"),
            installation_id=_optional_env("GITHUB_APP_INSTALLATION_ID"),
            private_key=_optional_env("GITHUB_APP_PRIVATE_KEY"),
            private_key_file=_optional_env("GITHUB_APP_PRIVATE_KEY_FILE"),
        ),
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
