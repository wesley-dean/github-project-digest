"""Prepare normalized Project items for digest templates."""

from __future__ import annotations

from datetime import date
from typing import Any

SECTION_DEFINITIONS = [
    {"key": "blocked", "title": "Blocked"},
    {"key": "in_progress", "title": "In Progress"},
    {"key": "open", "title": "Open"},
    {"key": "closed", "title": "Closed"},
]


def build_digest_sections(items: list[dict[str, Any]], today: date | None = None) -> list[dict[str, Any]]:
    """Group and sort issue items for digest templates."""

    today = today or date.today()
    grouped: dict[str, list[dict[str, Any]]] = {section["key"]: [] for section in SECTION_DEFINITIONS}

    for item in items:
        prepared = prepare_issue(item, today)
        section_key = classify_issue(prepared)
        if section_key in grouped:
            grouped[section_key].append(prepared)

    sections: list[dict[str, Any]] = []
    for section in SECTION_DEFINITIONS:
        section_items = sorted(grouped[section["key"]], key=_issue_sort_key)
        sections.append({**section, "issues": section_items, "count": len(section_items)})

    return sections


def build_digest_summary(items: list[dict[str, Any]], today: date | None = None) -> dict[str, int]:
    """Return simple counts used by digest templates."""

    today = today or date.today()
    prepared_items = [prepare_issue(item, today) for item in items]

    due_today = 0
    overdue = 0
    with_due_date = 0

    for item in prepared_items:
        due_date = item.get("due_date_obj")
        if isinstance(due_date, date):
            with_due_date += 1
            if due_date == today:
                due_today += 1
            elif due_date < today:
                overdue += 1

    total = len(prepared_items)
    return {
        "total": total,
        "due_today": due_today,
        "overdue": overdue,
        "with_due_date": with_due_date,
        "without_due_date": total - with_due_date,
    }


def prepare_issue(item: dict[str, Any], today: date) -> dict[str, Any]:
    """Add template-friendly status, due date, and marker values to an issue item."""

    fields = item.get("fields") or {}
    due_date = _first_present_field(fields, "Due Date", "Due", "due_date")
    status = _first_present_field(fields, "Status", "status")
    due_date_obj = _parse_date(due_date)

    if due_date_obj and due_date_obj < today:
        due_marker = "💥"
        due_state = "overdue"
    elif due_date_obj == today:
        due_marker = "🚨"
        due_state = "today"
    elif due_date_obj:
        due_marker = "⚠️"
        due_state = "upcoming"
    else:
        due_marker = "☐"
        due_state = "none"

    repository = str(item.get("repository") or "")
    number = item.get("number")
    issue_ref = f"{repository}#{number}" if repository and number is not None else f"#{number}" if number is not None else ""

    return {
        **item,
        "status": status or "",
        "due_date": due_date or "",
        "due_date_obj": due_date_obj,
        "due_marker": due_marker,
        "due_state": due_state,
        "issue_ref": issue_ref,
    }


def classify_issue(item: dict[str, Any]) -> str:
    """Return the digest section key for an issue item."""

    status = str(item.get("status") or "").strip().lower()
    state = str(item.get("state") or "").strip().lower()

    if status == "done" or state == "closed":
        return "closed"
    if status == "blocked":
        return "blocked"
    if status == "in progress":
        return "in_progress"
    return "open"


def _issue_sort_key(item: dict[str, Any]) -> tuple[int, date, str, int]:
    due_date = item.get("due_date_obj")
    title = str(item.get("title") or "").lower()
    number = item.get("number") if isinstance(item.get("number"), int) else 0
    if isinstance(due_date, date):
        return (0, due_date, title, number)
    return (1, date.max, title, number)


def _first_present_field(fields: dict[str, Any], *names: str) -> Any:
    lowered = {name.lower(): value for name, value in fields.items()}
    for name in names:
        value = lowered.get(name.lower())
        if value not in (None, ""):
            return value
    return None


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None
