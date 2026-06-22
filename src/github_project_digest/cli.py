"""@file cli.py
@brief Command-line entrypoint for github-project-digest.
@details
This module wires the application's documented pieces into one executable flow.
It is intentionally thin: configuration, authentication, GitHub retrieval,
normalization, filtering, digest preparation, rendering, and SMTP delivery all
remain in their own modules so the entrypoint can describe the pipeline without
owning each implementation detail.

The CLI is designed for local shell usage, Docker execution, Jenkins jobs,
GitHub Actions, and other schedulers.  It writes the selected output format to
STDOUT and uses the process exit code to communicate success or failure.
"""

from __future__ import annotations

import json
import sys
from typing import Any

import yaml

from github_project_digest.config import load_config
from github_project_digest.filtering import apply_filter, parse_filter
from github_project_digest.digest import build_digest_sections, build_digest_summary
from github_project_digest.github import GitHubProjectClient
from github_project_digest.github_auth import resolve_github_token
from github_project_digest.normalize import normalize_project
from github_project_digest.emailer import send_digest_email
from github_project_digest.render import render_digest


def main() -> int:
    """@fn main()
    @brief Run the GitHub Project digest pipeline.
    @details
    This function is the command-line orchestration layer.  It deliberately keeps
    the application flow linear: load configuration, resolve authentication,
    fetch Project data, normalize GraphQL results, parse and apply the filter,
    build digest sections and summary counts, render templates, optionally send
    email, and finally write the requested output format to STDOUT.

    Email delivery and STDOUT output are both performed when SMTP is configured.
    That behavior keeps Jenkins and local runs observable even when the primary
    delivery mechanism is email.  A failed pipeline returns a non-zero exit code
    and writes a compact error message to STDERR so schedulers and CI systems can
    detect failures without parsing normal digest output.

    @returns Process-style exit code: `0` for success, `1` for failure.

    @par Examples
    @code
    raise SystemExit(main())
    @endcode
    """

    try:
        config = load_config()
        github_token = resolve_github_token(config.github_token, config.github_app)
        client = GitHubProjectClient(github_token)
        assignee_login = client.resolve_user_login(config.github_user)
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

        context: dict[str, Any] = {
            "project": normalized["project"],
            "assignee": normalized.get("assignee", {"login": assignee_login}),
            "requested_user": config.github_user,
            "recipient_email": config.recipient_email,
            "filter_query": config.filter_query,
            "issues": issues,
            "sections": sections,
            "count": len(issues),
            "summary": summary,
        }

        text_output = render_digest(config.text_template, context)
        html_output = render_digest(config.html_template, context)

        if config.smtp:
            send_digest_email(config.smtp, text_output, html_output)

        if config.output_format == "json":
            print(json.dumps(context, indent=2, sort_keys=True))
        elif config.output_format == "yaml":
            print(yaml.safe_dump(context, sort_keys=False))
        elif config.output_format == "html":
            print(html_output)
        else:
            print(text_output)

        return 0
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
