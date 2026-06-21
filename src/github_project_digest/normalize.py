"""Normalize GitHub Project v2 GraphQL responses into template-friendly data."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any


def normalize_project(raw: dict[str, Any]) -> dict[str, Any]:
    """@fn normalize_project(raw)
    @brief Normalize the raw GitHub Project payload returned by the client.
    @details
    The GraphQL client returns data in a shape that mirrors GitHub's API.  That
    structure is useful at the boundary, but it is awkward for filtering,
    digest grouping, and templates.  This function creates the stable internal
    representation used by the rest of the pipeline while preserving project and
    assignee metadata for rendering.

    @param raw Raw dictionary returned by `GitHubProjectClient.fetch_project_items()`.
    @returns Dictionary containing project metadata, assignee metadata, and
             normalized item dictionaries.

    @par Examples
    @code
    normalized = normalize_project(raw_project_payload)
    items = normalized["items"]
    @endcode
    """

    return {
        "project": raw.get("project", {}),
        "assignee": raw.get("assignee", {}),
        "items": [_normalize_item(item) for item in raw.get("items", [])],
    }


def _normalize_item(item: dict[str, Any]) -> dict[str, Any]:
    """@fn _normalize_item(item)
    @brief Normalize one GitHub Project item node.
    @details
    Project items wrap underlying content such as issues and pull requests.  The
    digest needs a flatter structure containing common content fields,
    repository metadata, assignees, and Project field values.  This helper
    performs that flattening so later stages can work with one predictable item
    shape instead of nested GraphQL connections.

    @param item Raw Project item node from the GraphQL response.
    @returns Normalized item dictionary used by filtering and digest generation.

    @par Examples
    @code
    normalized_item = _normalize_item(project_item_node)
    @endcode
    """

    content = item.get("content") or {}
    fields = _normalize_fields(item.get("fieldValues", {}).get("nodes", []))
    assignees = [node.get("login") for node in (content.get("assignees", {}).get("nodes") or []) if node.get("login")]
    repository = content.get("repository") or {}

    return {
        "project_item_id": item.get("id"),
        "content_type": content.get("__typename"),
        "id": content.get("id"),
        "number": content.get("number"),
        "title": content.get("title"),
        "url": content.get("url"),
        "state": (content.get("state") or "").lower(),
        "repository": repository.get("nameWithOwner"),
        "repository_url": repository.get("url"),
        "assignees": assignees,
        "fields": fields,
    }


def _normalize_fields(nodes: list[dict[str, Any]]) -> dict[str, Any]:
    """@fn _normalize_fields(nodes)
    @brief Normalize Project field-value nodes into a name-to-value mapping.
    @details
    GitHub Project field values are returned as typed GraphQL nodes.  The digest
    does not need to preserve the full GraphQL object for each field; it needs
    template-friendly values keyed by the human-visible Project field name.  This
    helper converts supported field types into strings, numbers, lists, or small
    dictionaries as appropriate.

    Unsupported field types are intentionally ignored.  That keeps the MVP
    conservative: unknown data will not break the digest, and support for new
    field types can be added deliberately when a template or filter needs them.

    @param nodes Project field-value nodes from one Project item.
    @returns Dictionary mapping Project field names to normalized values.

    @par Examples
    @code
    fields = _normalize_fields(item["fieldValues"]["nodes"])
    due_date = fields.get("Due Date")
    @endcode
    """

    fields: dict[str, Any] = {}

    for node in nodes or []:
        field_name = ((node.get("field") or {}).get("name") or "").strip()
        if not field_name:
            continue

        typename = node.get("__typename")
        if typename == "ProjectV2ItemFieldTextValue":
            fields[field_name] = node.get("text")
        elif typename == "ProjectV2ItemFieldDateValue":
            fields[field_name] = node.get("date")
        elif typename == "ProjectV2ItemFieldNumberValue":
            fields[field_name] = node.get("number")
        elif typename == "ProjectV2ItemFieldSingleSelectValue":
            fields[field_name] = node.get("name")
        elif typename == "ProjectV2ItemFieldIterationValue":
            fields[field_name] = {
                "title": node.get("title"),
                "start_date": node.get("startDate"),
                "duration": node.get("duration"),
                "is_current": _iteration_is_current(node.get("startDate"), node.get("duration")),
            }
        elif typename == "ProjectV2ItemFieldUserValue":
            users = node.get("users", {}).get("nodes") or []
            fields[field_name] = [user.get("login") for user in users if user.get("login")]
        elif typename == "ProjectV2ItemFieldRepositoryValue":
            repository = node.get("repository") or {}
            fields[field_name] = repository.get("nameWithOwner")

    return fields


def _iteration_is_current(start_date: str | None, duration: int | None) -> bool:
    """@fn _iteration_is_current(start_date, duration)
    @brief Determine whether an iteration field value includes today.
    @details
    GitHub Project iteration values expose a start date and duration rather than
    a direct `is_current` flag.  The digest computes that flag during
    normalization so filtering can use a simple boolean and avoid duplicating
    date arithmetic elsewhere.

    The end date is treated as exclusive, matching the common half-open interval
    convention for date ranges: an iteration is current when today is on or
    after the start date and before the computed end date.

    @param start_date ISO-formatted iteration start date.
    @param duration Number of days in the iteration.
    @returns `True` when today's date falls within the iteration window.

    @par Examples
    @code
    is_current = _iteration_is_current("2026-06-15", 14)
    @endcode
    """

    if not start_date or not duration:
        return False

    start = date.fromisoformat(start_date)
    end = start + timedelta(days=int(duration))
    today = date.today()
    return start <= today < end
