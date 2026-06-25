from __future__ import annotations

import json
import sys
from typing import Any

import yaml

from github_project_digest.config import Config, ConfiguredUser, load_config
from github_project_digest.filtering import apply_filter, parse_filter
from github_project_digest.digest import build_digest_sections, build_digest_summary
from github_project_digest.github import GitHubProjectClient
from github_project_digest.github_auth import resolve_github_token
from github_project_digest.normalize import normalize_project
from github_project_digest.emailer import send_digest_email
from github_project_digest.render import render_digest


TEXT_DIGEST_SEPARATOR = "===== Digest for {user} ====="
HTML_DIGEST_SEPARATOR = "<h1>Digest for {user}</h1>"


def _build_user_digest_context(
    config: Config,
    configured_user: ConfiguredUser,
    client: GitHubProjectClient,
) -> dict[str, Any]:
    assignee_login = client.resolve_user_login(configured_user.github_user)
    raw = client.fetch_project_items(
        owner=config.project_owner,
        project_number=config.project_number,
        owner_type=config.project_owner_type,
        assignee_login=assignee_login,
        page_size=config.page_size,
        field_value_limit=config.field_value_limit,
    )
    normalized = normalize_project(raw)
    project_filter = parse_filter(config.filter_query, assignee_login)
    issues = apply_filter(normalized["items"], project_filter)
    sections = build_digest_sections(
        issues,
        current_assignee=assignee_login,
        due_soon_days=config.due_soon_days,
        due_upcoming_days=config.due_upcoming_days,
    )
    summary = build_digest_summary(issues)

    return {
        "project": normalized["project"],
        "assignee": normalized.get("assignee", {"login": assignee_login}),
        "requested_user": configured_user.github_user,
        "recipient_email": configured_user.recipient_email,
        "filter_query": config.filter_query,
        "issues": issues,
        "sections": sections,
        "count": len(issues),
        "summary": summary,
    }


def _render_user_digest(config: Config, context: dict[str, Any]) -> dict[str, str]:
    return {
        "text": render_digest(config.text_template, context),
        "html": render_digest(config.html_template, context),
    }


def _should_deliver_user_digest(
    config: Config,
    configured_user: ConfiguredUser,
    context: dict[str, Any],
) -> bool:
    """@fn _should_deliver_user_digest(config, configured_user, context)
    @brief Decide whether one rendered digest should be sent through SMTP.
    @details
    SMTP delivery requires a configured recipient.  When no recipient is present,
    the digest remains a STDOUT-only result regardless of issue count.

    Non-empty digests are always eligible for SMTP delivery when a recipient is
    configured.  Empty digests are controlled by `Config.send_empty_email`, which
    preserves the existing send-by-default behavior while allowing quiet scheduled
    jobs to suppress no-work emails.

    This helper intentionally makes the delivery decision before the SMTP layer
    so `emailer.py` can remain focused on message construction and transport.
    STDOUT rendering is unaffected by this decision.

    @param config Runtime configuration containing the empty-email preference.
    @param configured_user User-specific recipient and SMTP configuration.
    @param context Prepared digest context containing the filtered issue count.
    @returns `True` when SMTP delivery should be attempted, otherwise `False`.

    @par Examples
    @code
    if _should_deliver_user_digest(config, configured_user, context):
        _deliver_user_digest(configured_user, rendered)
    @endcode
    """

    if not configured_user.smtp:
        return False
    if context["count"] > 0:
        return True
    return config.send_empty_email


def _deliver_user_digest(configured_user: ConfiguredUser, rendered: dict[str, str]) -> None:
    if configured_user.smtp:
        send_digest_email(configured_user.smtp, rendered["text"], rendered["html"])


def _stdout_payload(
    config: Config,
    contexts: list[dict[str, Any]],
    rendered_outputs: list[dict[str, str]],
) -> str:
    multiple_users = len(contexts) > 1

    if config.output_format == "json":
        payload: Any = {"digests": contexts} if multiple_users else contexts[0]
        return json.dumps(payload, indent=2, sort_keys=True)

    if config.output_format == "yaml":
        payload = {"digests": contexts} if multiple_users else contexts[0]
        return yaml.safe_dump(payload, sort_keys=False)

    if config.output_format == "html":
        if not multiple_users:
            return rendered_outputs[0]["html"]
        return "\n\n".join(
            f"{HTML_DIGEST_SEPARATOR.format(user=context['requested_user'])}\n\n{rendered['html']}"
            for context, rendered in zip(contexts, rendered_outputs, strict=True)
        )

    if not multiple_users:
        return rendered_outputs[0]["text"]
    return "\n\n".join(
        f"{TEXT_DIGEST_SEPARATOR.format(user=context['requested_user'])}\n\n{rendered['text']}"
        for context, rendered in zip(contexts, rendered_outputs, strict=True)
    )


def main() -> int:
    try:
        config = load_config()
        github_token = resolve_github_token(config.github_token, config.github_app)
        client = GitHubProjectClient(github_token)

        contexts: list[dict[str, Any]] = []
        rendered_outputs: list[dict[str, str]] = []

        for configured_user in config.users:
            context = _build_user_digest_context(config, configured_user, client)
            rendered = _render_user_digest(config, context)
            if _should_deliver_user_digest(config, configured_user, context):
                _deliver_user_digest(configured_user, rendered)
            contexts.append(context)
            rendered_outputs.append(rendered)

        print(_stdout_payload(config, contexts, rendered_outputs))

        return 0
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())