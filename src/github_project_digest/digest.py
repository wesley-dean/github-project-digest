"""Prepare normalized Project items for digest templates."""

from __future__ import annotations

from datetime import date
from typing import Any

"""@var SECTION_DEFINITIONS
@brief Ordered digest sections rendered by the text and HTML templates.
@details
The section list is deliberately data-driven so grouping order stays consistent
across plain text, HTML, JSON, YAML, and future delivery mechanisms.  The keys
are internal stable identifiers used by the grouping logic, while the titles are
human-facing labels rendered by templates.
"""
SECTION_DEFINITIONS = [
    {"key": "blocked", "title": "Blocked"},
    {"key": "in_progress", "title": "In Progress"},
    {"key": "open", "title": "Open"},
    {"key": "closed", "title": "Closed"},
]

"""@var UPCOMING_SOON_DAYS
@brief Maximum number of remaining days treated as urgent upcoming work.
@details
Issues due within this many days use the warning marker.  The threshold keeps
near-term work visually prominent without treating every future due date as
urgent.
"""
UPCOMING_SOON_DAYS = 2

"""@var UPCOMING_WINDOW_DAYS
@brief Maximum number of remaining days treated as normal upcoming work.
@details
Issues due after the urgent upcoming window and within this many days use the
calendar marker.  Later work uses the lower-urgency later marker so digest
readers can distinguish near-term scheduling from longer-range planning.
"""
UPCOMING_WINDOW_DAYS = 7


def build_digest_sections(items: list[dict[str, Any]], today: date | None = None) -> list[dict[str, Any]]:
    """@fn build_digest_sections(items, today=None)
    @brief Group, prepare, and sort issues for digest templates.
    @details
    This function is the main bridge between normalized Project items and the
    rendered digest.  Each item is enriched with template-friendly values,
    classified into a human-facing section, and sorted so dated work appears
    before undated work.

    The section order is intentionally fixed by `SECTION_DEFINITIONS` rather
    than inferred from item data.  That keeps the digest stable from day to day
    and presents the most urgent workflow states first: blocked work, active
    work, open work, and then closed work.

    @param items Normalized and filtered Project items.
    @param today Optional date used for deterministic tests and due-date logic.
    @returns Ordered section dictionaries containing titles, counts, and issues.

    @par Examples
    @code
    sections = build_digest_sections(filtered_items)
    @endcode
    """

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
    """@fn build_digest_summary(items, today=None)
    @brief Build summary counts used by digest templates.
    @details
    The summary gives recipients a quick sense of urgency before they read the
    individual issue lists.  It counts all matching items, dated and undated
    work, overdue work, and work due today.

    The function prepares items internally so summary counts use the same due
    date interpretation as the rendered sections.  This avoids subtle mismatches
    between the summary and the detailed lists.

    @param items Normalized and filtered Project items.
    @param today Optional date used for deterministic tests and due-date logic.
    @returns Dictionary of summary counts for templates and structured output.

    @par Examples
    @code
    summary = build_digest_summary(filtered_items)
    @endcode
    """

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
    """@fn prepare_issue(item, today)
    @brief Add template-friendly status, due-date, marker, and reference values.
    @details
    Normalized Project items still contain raw field values.  This function adds
    the values templates need directly: status, due date text, parsed due date,
    days remaining, due-state label, due marker, and a concise issue reference.

    The due markers encode the digest's urgency model from the number of days
    remaining before the due date: explosion for overdue work, red alert for
    work due today, yellow warning for work due within two days, calendar for
    work due within seven days, sleepy face for later work, and an empty
    checkbox for work without a due date.

    @param item Normalized Project item.
    @param today Date used to compare due dates.
    @returns Copy of the item with additional digest-specific fields.

    @par Examples
    @code
    prepared = prepare_issue(item, date.today())
    @endcode
    """

    fields = item.get("fields") or {}
    due_date = _first_present_field(fields, "Due Date", "Due", "due_date")
    status = _first_present_field(fields, "Status", "status")
    due_date_obj = _parse_date(due_date)
    days_remaining = (due_date_obj - today).days if due_date_obj else None
    due_marker, due_state = _due_marker_for_days_remaining(days_remaining)

    repository = str(item.get("repository") or "")
    number = item.get("number")
    issue_ref = f"{repository}#{number}" if repository and number is not None else f"#{number}" if number is not None else ""

    return {
        **item,
        "status": status or "",
        "due_date": due_date or "",
        "due_date_obj": due_date_obj,
        "days_remaining": days_remaining,
        "due_marker": due_marker,
        "due_state": due_state,
        "issue_ref": issue_ref,
    }


def classify_issue(item: dict[str, Any]) -> str:
    """@fn classify_issue(item)
    @brief Return the digest section key for one prepared issue.
    @details
    Section classification is based on Project status first and GitHub state
    where appropriate.  A Project status of `Done` and a GitHub state of
    `closed` both map to the closed section, because either signal means the
    item should no longer appear as active work.

    Items without a recognized status remain in the open section.  This default
    keeps untriaged or lightly-managed work visible instead of silently dropping
    it from the daily digest.

    @param item Prepared issue dictionary.
    @returns Section key from `SECTION_DEFINITIONS`.

    @par Examples
    @code
    section_key = classify_issue(prepared_issue)
    @endcode
    """

    status = str(item.get("status") or "").strip().lower()
    state = str(item.get("state") or "").strip().lower()

    if status == "done" or state == "closed":
        return "closed"
    if status == "blocked":
        return "blocked"
    if status == "in progress":
        return "in_progress"
    return "open"


def _due_marker_for_days_remaining(days_remaining: int | None) -> tuple[str, str]:
    """@fn _due_marker_for_days_remaining(days_remaining)
    @brief Return the due marker and due-state label for a relative due date.
    @details
    The digest vocabulary is based on days remaining rather than a raw future
    date check.  That gives recipients more useful urgency signals: immediate
    work remains visually loud, near-term scheduled work stays visible, and
    longer-range work receives a calmer marker.

    @param days_remaining Number of days until the issue is due, or `None` when
        the issue has no due date.
    @returns Tuple containing the user-facing emoji marker and stable due-state
        label consumed by templates and structured output.

    @par Examples
    @code
    marker, state = _due_marker_for_days_remaining(1)
    @endcode
    """

    if days_remaining is None:
        return "☐", "none"
    if days_remaining < 0:
        return "💥", "overdue"
    if days_remaining == 0:
        return "🚨", "today"
    if days_remaining <= UPCOMING_SOON_DAYS:
        return "⚠️", "soon"
    if days_remaining <= UPCOMING_WINDOW_DAYS:
        return "📅", "upcoming"
    return "💤", "later"


def _issue_sort_key(item: dict[str, Any]) -> tuple[int, date, str, int]:
    """@fn _issue_sort_key(item)
    @brief Build a stable sort key for issues within a section.
    @details
    Issues with due dates sort before undated issues, then by due date, title,
    and issue number.  This prioritizes scheduled work while keeping the order
    deterministic when multiple issues share the same due date or no due date.

    @param item Prepared issue dictionary.
    @returns Tuple used by Python's stable sorting logic.

    @par Examples
    @code
    sorted_issues = sorted(section_issues, key=_issue_sort_key)
    @endcode
    """

    due_date = item.get("due_date_obj")
    title = str(item.get("title") or "").lower()
    number = item.get("number") if isinstance(item.get("number"), int) else 0
    if isinstance(due_date, date):
        return (0, due_date, title, number)
    return (1, date.max, title, number)


def _first_present_field(fields: dict[str, Any], *names: str) -> Any:
    """@fn _first_present_field(fields, *names)
    @brief Return the first non-empty Project field value for known aliases.
    @details
    Project boards may use slightly different field names, such as `Due Date`,
    `Due`, or `due_date`.  This helper lets the digest recognize those common
    aliases without forcing every board to use one exact field name.

    @param fields Normalized Project field dictionary.
    @param names Candidate field names in priority order.
    @returns First non-empty field value, or `None`.

    @par Examples
    @code
    due_date = _first_present_field(fields, "Due Date", "Due")
    @endcode
    """

    lowered = {name.lower(): value for name, value in fields.items()}
    for name in names:
        value = lowered.get(name.lower())
        if value not in (None, ""):
            return value
    return None


def _parse_date(value: Any) -> date | None:
    """@fn _parse_date(value)
    @brief Parse a value into a date when possible.
    @details
    GitHub Project date fields normally arrive as ISO-formatted strings, while
    tests may pass actual `date` instances.  Invalid or empty values are treated
    as missing dates so one malformed field does not break an entire digest run.

    @param value Candidate date value.
    @returns Parsed `date`, existing `date`, or `None`.

    @par Examples
    @code
    due_date = _parse_date("2026-06-19")
    @endcode
    """

    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None
