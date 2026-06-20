"""Normalize GitHub Project v2 GraphQL responses into template-friendly data."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any


def normalize_project(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize raw Project item data returned by the GitHub GraphQL client."""

    return {
        "project": raw.get("project", {}),
        "assignee": raw.get("assignee", {}),
        "items": [_normalize_item(item) for item in raw.get("items", [])],
    }


def _normalize_item(item: dict[str, Any]) -> dict[str, Any]:
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
    if not start_date or not duration:
        return False

    start = date.fromisoformat(start_date)
    end = start + timedelta(days=int(duration))
    today = date.today()
    return start <= today < end
