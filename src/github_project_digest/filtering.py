"""Small local filter implementation for the MVP digest workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ProjectFilter:
    """@class ProjectFilter
    @brief Parsed representation of the supported Project digest filter subset.
    @details
    `ProjectFilter` captures the small, intentional subset of GitHub
    Project-like filter syntax that this tool supports today.  The class avoids
    pretending to be a complete implementation of GitHub's Project search
    language.  Instead, it records the specific fields the digest pipeline needs
    in order to decide whether a normalized Project item belongs in one user's
    daily digest.

    The original raw terms are preserved because unsupported or future filter
    terms may still be useful for debugging, logging, or later expansion without
    changing the public shape of the parsed filter object.
    """

    assignee: str | None = None
    content_type: str | None = None
    state: str | None = None
    current_sprint: bool = False
    raw_terms: list[str] = field(default_factory=list)


def parse_filter(filter_query: str, user_login: str) -> ProjectFilter:
    """Parse a minimal filter subset.

    Supported terms:
    - assignee:<login>, assignee:@me, assignee:@user
    - user:<login>, user:@me, user:@user
    - is:issue
    - state:open, state:closed, status:open, status:closed
    - sprint:@current, iteration:@current

    @me and @user both resolve to the configured GITHUB_USER value. If
    GITHUB_USER itself is @me, the caller should pass the authenticated viewer
    login as user_login.
    """

    assignee = None
    content_type = None
    state = None
    current_sprint = False
    raw_terms: list[str] = []

    for token in filter_query.split():
        raw_terms.append(token)
        if ":" not in token:
            continue

        key, value = token.split(":", 1)
        key = key.strip().lower()
        value = value.strip()
        value_lower = value.lower()

        if key in {"assignee", "user"}:
            assignee = user_login if value_lower in {"@me", "@user", "$user", "${user}"} else value
        elif key == "is" and value_lower in {"issue", "pullrequest", "pr"}:
            content_type = "PullRequest" if value_lower in {"pullrequest", "pr"} else "Issue"
        elif key in {"state", "status"} and value_lower in {"open", "closed", "merged"}:
            state = value_lower
        elif key in {"sprint", "iteration"} and value_lower == "@current":
            current_sprint = True

    return ProjectFilter(
        assignee=assignee,
        content_type=content_type,
        state=state,
        current_sprint=current_sprint,
        raw_terms=raw_terms,
    )


def apply_filter(items: list[dict[str, Any]], project_filter: ProjectFilter) -> list[dict[str, Any]]:
    """Apply the MVP local filter to normalized Project items."""

    return [item for item in items if _matches(item, project_filter)]


def _matches(item: dict[str, Any], project_filter: ProjectFilter) -> bool:
    if project_filter.content_type and item.get("content_type") != project_filter.content_type:
        return False

    if project_filter.state and item.get("state") != project_filter.state:
        return False

    if project_filter.assignee and project_filter.assignee not in item.get("assignees", []):
        return False

    if project_filter.current_sprint and not _has_current_iteration(item):
        return False

    return True


def _has_current_iteration(item: dict[str, Any]) -> bool:
    fields = item.get("fields") or {}
    for field_name, value in fields.items():
        if field_name.lower() not in {"sprint", "iteration"}:
            continue
        if isinstance(value, dict) and value.get("is_current"):
            return True
    return False
