"""Command-line entrypoint for github-project-digest."""

from __future__ import annotations

import json
import sys
from typing import Any

import yaml

from github_project_digest.config import load_config
from github_project_digest.filtering import apply_filter, parse_filter
from github_project_digest.digest import build_digest_sections, build_digest_summary
from github_project_digest.github import GitHubProjectClient
from github_project_digest.normalize import normalize_project
from github_project_digest.emailer import send_digest_email
from github_project_digest.render import render_digest


def main() -> int:
    """Run the MVP Project digest pipeline and write the result to STDOUT."""

    try:
        config = load_config()
        client = GitHubProjectClient(config.github_token)
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
        sections = build_digest_sections(issues)
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
