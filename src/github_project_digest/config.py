"""@file config.py
@brief Load runtime configuration for github-project-digest.
@details
This module translates environment variables and optional `.env` values into a
single immutable `Config` object.  The configuration layer intentionally keeps
Jenkins, Docker, local shell usage, PAT authentication, GitHub App
authentication, SMTP delivery, template selection, Project filtering, due
marker thresholds, and empty-digest delivery preferences behind one consistent
interface so the rest of the application can operate on typed values rather
than raw process environment strings.

The module also owns the `GITHUB_USER` parsing convention.  A colon-separated
value identifies both the GitHub assignee and the optional email destination,
while a bare login or `@me` keeps the tool in STDOUT-only mode.  Multiple values
may be separated with commas so a future orchestration layer can fan out one
separate digest per configured user.
"""

from __future__ import annotations

from dataclasses import dataclass
import os

from dotenv import load_dotenv

from github_project_digest.emailer import SmtpConfig
from github_project_digest.github_auth import GitHubAppConfig


"""@var DEFAULT_FILTER
@brief Default Project filter used when no filter is supplied.
@details
The default filter encodes the primary daily-digest use case: show open issues
from the current sprint that are assigned to the selected GitHub user.  The
`@user` placeholder is resolved later against `GITHUB_USER` or the authenticated
viewer, which lets the same default work for local single-user runs and Jenkins
fan-out jobs.
"""
DEFAULT_FILTER = "sprint:@current assignee:@user is:issue state:open"

"""@var DEFAULT_DUE_SOON_DAYS
@brief Default maximum number of remaining days treated as urgent upcoming work.
@details
The default preserves the original digest behavior: issues due in one or two
days use the warning marker unless overridden by `DUE_SOON_DAYS`.
"""
DEFAULT_DUE_SOON_DAYS = 2

"""@var DEFAULT_DUE_UPCOMING_DAYS
@brief Default maximum number of remaining days treated as normal upcoming work.
@details
The default preserves the original digest behavior: issues due in three through
seven days use the calendar marker unless overridden by `DUE_UPCOMING_DAYS`.
"""
DEFAULT_DUE_UPCOMING_DAYS = 7

"""@var DEFAULT_SEND_EMPTY_EMAIL
@brief Default empty-digest email delivery behavior.
@details
The default preserves the original SMTP delivery behavior by sending configured
email digests even when the filtered issue count is zero.  Users who prefer quiet
automation can override this with `SEND_EMPTY_EMAIL=false` while still receiving
STDOUT output for logs, scheduled jobs, and local verification.
"""
DEFAULT_SEND_EMPTY_EMAIL = True


@dataclass(frozen=True)
class ConfiguredUser:
    """@class ConfiguredUser
    @brief Runtime configuration for one digest recipient or assignee.
    @details
    A configured user preserves the existing one-user-per-digest semantic model
    while giving the configuration layer a place to represent future fan-out.
    Each entry contains the GitHub user expression that will be resolved for one
    digest, the optional recipient email parsed from that expression, and the
    optional SMTP settings prepared for that recipient.
    """

    github_user: str
    recipient_email: str | None
    smtp: SmtpConfig | None


@dataclass(frozen=True)
class Config:
    """@class Config
    @brief Immutable runtime configuration for one digest execution.
    @details
    `Config` is the boundary between the operating environment and the digest
    pipeline.  The rest of the application receives typed values from this
    dataclass instead of reading environment variables directly.  This keeps
    command-line execution, Docker execution, Jenkins execution, PAT auth,
    GitHub App auth, SMTP delivery, due marker thresholds, template rendering,
    and empty-digest delivery behavior aligned through one configuration
    contract.

    The `users` collection is the forward-compatible representation used for
    digest fan-out.  The legacy `github_user`, `recipient_email`, and `smtp`
    fields remain populated from the first configured user so existing single
    user call sites continue to behave as before while the CLI evolves toward
    iterating over `users`.

    The `send_empty_email` field controls only SMTP delivery when a rendered
    digest has no matching issues.  STDOUT output remains available regardless of
    this setting so local runs, Jenkins logs, Docker runs, and GitHub Actions
    logs can still show what the application did.
    """

    github_token: str | None
    github_app: GitHubAppConfig
    project_owner: str
    project_number: int
    project_owner_type: str
    users: list[ConfiguredUser]
    github_user: str
    recipient_email: str | None
    filter_query: str
    output_format: str
    text_template: str
    html_template: str
    page_size: int
    field_value_limit: int
    due_soon_days: int
    due_upcoming_days: int
    send_empty_email: bool
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
    project number, page size, field-value limit, SMTP port, SMTP timeout, and
    due marker thresholds.  This helper keeps conversion and error reporting
    consistent across all of those values.

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


def _load_due_thresholds() -> tuple[int, int]:
    """@fn _load_due_thresholds()
    @brief Load and validate due marker threshold settings.
    @details
    Due marker thresholds control when future due dates move from the warning
    marker to the calendar marker and then to the later marker.  They are runtime
    settings so users can tune digest urgency without changing source code.

    The soon threshold must be greater than or equal to zero, and the upcoming
    threshold must be greater than or equal to the soon threshold.  Those rules
    keep the due-date ranges ordered and prevent unreachable marker states.

    @returns Tuple containing `due_soon_days` and `due_upcoming_days`.

    @par Examples
    @code
    due_soon_days, due_upcoming_days = _load_due_thresholds()
    @endcode
    """

    due_soon_days = _int_env("DUE_SOON_DAYS", DEFAULT_DUE_SOON_DAYS)
    due_upcoming_days = _int_env("DUE_UPCOMING_DAYS", DEFAULT_DUE_UPCOMING_DAYS)

    if due_soon_days < 0:
        raise ValueError("DUE_SOON_DAYS must be greater than or equal to 0")
    if due_upcoming_days < due_soon_days:
        raise ValueError("DUE_UPCOMING_DAYS must be greater than or equal to DUE_SOON_DAYS")

    return due_soon_days, due_upcoming_days


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


def _parse_configured_users(value: str) -> list[ConfiguredUser]:
    """@fn _parse_configured_users(value)
    @brief Parse one or more configured digest users.
    @details
    `GITHUB_USER` accepts the existing single-user forms and a comma-separated
    fan-out list of those same forms.  This parser deliberately treats commas as
    simple separators rather than implementing RFC CSV semantics.  Surrounding
    whitespace is ignored, and empty entries are rejected so accidental doubled
    commas fail visibly instead of silently skipping a recipient.

    Each parsed entry receives its own optional SMTP configuration.  That keeps
    future fan-out behavior aligned with the product rule that every digest has
    one selected GitHub user, one assignee context, one optional email recipient,
    and one render pass.

    @param value Raw `GITHUB_USER` value.
    @returns Configured user entries in declaration order.

    @par Examples
    @code
    users = _parse_configured_users("octocat,hubot:hubot@example.com")
    @endcode
    """

    entries = (value or "@me").split(",")
    configured_users: list[ConfiguredUser] = []

    for entry in entries:
        if entry.strip() == "":
            raise ValueError("GITHUB_USER contains an empty user entry")

        github_user, recipient_email = _split_user_and_email(entry)
        configured_users.append(
            ConfiguredUser(
                github_user=github_user,
                recipient_email=recipient_email,
                smtp=_load_smtp_config(recipient_email),
            )
        )

    return configured_users


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
    from the current working directory, validates constrained settings, parses
    the selected GitHub user list, loads due marker thresholds, loads the
    empty-digest email delivery preference, and returns a single immutable
    `Config` instance for the rest of the digest pipeline.

    Environment access is intentionally concentrated here so GitHub access,
    filtering, rendering, due marker selection, and email delivery can be tested
    with explicit values rather than direct process-state dependencies.  The
    `.env` lookup is deliberately anchored to the process working directory so
    tests that change directories do not accidentally load a developer's project
    secrets from the repository root.

    @returns Fully populated runtime `Config`.

    @par Examples
    @code
    config = load_config()
    @endcode
    """

    load_dotenv(dotenv_path=".env", override=True)

    owner_type = os.getenv("GITHUB_PROJECT_OWNER_TYPE", "organization").lower().strip()
    if owner_type not in {"organization", "user"}:
        raise ValueError("GITHUB_PROJECT_OWNER_TYPE must be 'organization' or 'user'")

    output_format = os.getenv("DIGEST_OUTPUT_FORMAT", os.getenv("OUTPUT_FORMAT", "text")).lower().strip()
    if output_format not in {"text", "html", "json", "yaml"}:
        raise ValueError("DIGEST_OUTPUT_FORMAT/OUTPUT_FORMAT must be one of: text, html, json, yaml")

    users = _parse_configured_users(_selected_user_value())
    first_user = users[0]
    due_soon_days, due_upcoming_days = _load_due_thresholds()

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
        users=users,
        github_user=first_user.github_user,
        recipient_email=first_user.recipient_email,
        filter_query=os.getenv("GITHUB_PROJECT_FILTER", DEFAULT_FILTER),
        output_format=output_format,
        text_template=os.getenv("DIGEST_TEMPLATE_TEXT", "digest.txt.j2"),
        html_template=os.getenv("DIGEST_TEMPLATE_HTML", "digest.html.j2"),
        page_size=_int_env("GITHUB_PROJECT_PAGE_SIZE", 50),
        field_value_limit=_int_env("GITHUB_PROJECT_FIELD_VALUE_LIMIT", 50),
        due_soon_days=due_soon_days,
        due_upcoming_days=due_upcoming_days,
        send_empty_email=_bool_env("SEND_EMPTY_EMAIL", DEFAULT_SEND_EMPTY_EMAIL),
        smtp=first_user.smtp,
    )