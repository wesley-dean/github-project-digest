from __future__ import annotations

from github_project_digest.digest import build_digest_sections, build_digest_summary, prepare_issue


def test_prepare_issue_due_markers(today) -> None:
    base = {
        "number": 1,
        "title": "Example",
        "state": "open",
        "repository": "owner/repo",
        "fields": {"Status": "Open"},
    }

    overdue = prepare_issue({**base, "fields": {"Status": "Open", "Due Date": "2026-06-19"}}, today)
    due_today = prepare_issue({**base, "fields": {"Status": "Open", "Due Date": "2026-06-20"}}, today)
    future = prepare_issue({**base, "fields": {"Status": "Open", "Due Date": "2026-06-21"}}, today)
    unscheduled = prepare_issue(base, today)

    assert overdue["due_marker"] == "💥"
    assert overdue["due_state"] == "overdue"
    assert due_today["due_marker"] == "🚨"
    assert due_today["due_state"] == "today"
    assert future["due_marker"] == "⚠️"
    assert future["due_state"] == "upcoming"
    assert unscheduled["due_marker"] == "☐"
    assert unscheduled["due_state"] == "none"


def test_build_digest_sections_groups_and_sorts_by_due_date(sample_items, today) -> None:
    sections = build_digest_sections(sample_items, today)
    by_key = {section["key"]: section for section in sections}

    assert [issue["number"] for issue in by_key["blocked"]["issues"]] == [4]
    assert [issue["number"] for issue in by_key["in_progress"]["issues"]] == [3]
    assert [issue["number"] for issue in by_key["open"]["issues"]] == [1, 2, 5]
    assert [issue["number"] for issue in by_key["closed"]["issues"]] == [6]


def test_build_digest_summary_counts_due_date_states(sample_items, today) -> None:
    summary = build_digest_summary(sample_items, today)

    assert summary == {
        "total": 6,
        "due_today": 1,
        "overdue": 1,
        "with_due_date": 3,
        "without_due_date": 3,
    }
