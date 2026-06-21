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
    """@fn parse_filter(filter_query, user_login)
    @brief Parse the supported subset of Project digest filter syntax.
    @details
    The digest uses familiar GitHub-style filter terms, but it intentionally
    supports only the subset needed for the daily task-list workflow.  This keeps
    the MVP predictable and avoids implying full compatibility with GitHub's
    Project search language.

    `@me`, `@user`, `$user`, and `${user}` resolve to the already-selected
    assignee login.  That lets templates, Jenkins jobs, and local runs reuse the
    same default filter while changing only `GITHUB_USER`.

    @param filter_query Raw filter expression from configuration.
    @param user_login Resolved GitHub login for the selected digest assignee.
    @returns Parsed `ProjectFilter` object.

    @par Examples
    @code
    project_filter = parse_filter(
        "sprint:@current assignee:@user is:issue state:open",
        "wesley-dean",
    )
    @endcode
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
    """@fn apply_filter(items, project_filter)
    @brief Apply a parsed Project filter to normalized Project items.
    @details
    Filtering happens locally after GraphQL retrieval because Project item data
    includes fields, assignees, state, and content type in one normalized shape.
    This keeps the GraphQL query simpler and allows the digest to evolve its
    supported filter subset without rewriting the query for every condition.

    @param items Normalized Project items.
    @param project_filter Parsed filter criteria.
    @returns Items that match the supported filter criteria.

    @par Examples
    @code
    visible_items = apply_filter(normalized_items, project_filter)
    @endcode
    """

    return [item for item in items if _matches(item, project_filter)]


def _matches(item: dict[str, Any], project_filter: ProjectFilter) -> bool:
    """@fn _matches(item, project_filter)
    @brief Determine whether one normalized item satisfies a parsed filter.
    @details
    Each supported filter field is optional.  When a criterion is absent, it is
    ignored.  When present, the item must satisfy that criterion to remain in the
    digest.  This explicit conjunction keeps the MVP behavior easy to reason
    about and avoids hidden ranking or partial-match behavior.

    @param item Normalized Project item to test.
    @param project_filter Parsed filter criteria.
    @returns `True` when the item should be included in the digest.

    @par Examples
    @code
    if _matches(item, project_filter):
        included.append(item)
    @endcode
    """

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
    """@fn _has_current_iteration(item)
    @brief Detect whether an item belongs to the current sprint or iteration.
    @details
    GitHub Projects may use either `Sprint` or `Iteration` field names depending
    on how the board was configured.  The digest treats those names as
    equivalent and looks for a normalized field value whose `is_current` flag is
    true.

    @param item Normalized Project item whose fields should be inspected.
    @returns `True` when the item has a current sprint or iteration value.

    @par Examples
    @code
    current = _has_current_iteration(item)
    @endcode
    """

    fields = item.get("fields") or {}
    for field_name, value in fields.items():
        if field_name.lower() not in {"sprint", "iteration"}:
            continue
        if isinstance(value, dict) and value.get("is_current"):
            return True
    return False
