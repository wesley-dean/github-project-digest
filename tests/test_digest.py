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
    soon_one_day = prepare_issue({**base, "fields": {"Status": "Open", "Due Date": "2026-06-21"}}, today)
    soon_two_days = prepare_issue({**base, "fields": {"Status": "Open", "Due Date": "2026-06-22"}}, today)
    upcoming_three_days = prepare_issue({**base, "fields": {"Status": "Open", "Due Date": "2026-06-23"}}, today)
    upcoming_seven_days = prepare_issue({**base, "fields": {"Status": "Open", "Due Date": "2026-06-27"}}, today)
    later = prepare_issue({**base, "fields": {"Status": "Open", "Due Date": "2026-06-28"}}, today)
    unscheduled = prepare_issue(base, today)

    assert overdue["days_remaining"] == -1
    assert overdue["due_marker"] == "💥"
    assert overdue["due_state"] == "overdue"
    assert due_today["days_remaining"] == 0
    assert due_today["due_marker"] == "🚨"
    assert due_today["due_state"] == "today"
    assert soon_one_day["days_remaining"] == 1
    assert soon_one_day["due_marker"] == "⚠️"
    assert soon_one_day["due_state"] == "soon"
    assert soon_two_days["days_remaining"] == 2
    assert soon_two_days["due_marker"] == "⚠️"
    assert soon_two_days["due_state"] == "soon"
    assert upcoming_three_days["days_remaining"] == 3
    assert upcoming_three_days["due_marker"] == "📅"
    assert upcoming_three_days["due_state"] == "upcoming"
    assert upcoming_seven_days["days_remaining"] == 7
    assert upcoming_seven_days["due_marker"] == "📅"
    assert upcoming_seven_days["due_state"] == "upcoming"
    assert later["days_remaining"] == 8
    assert later["due_marker"] == "💤"
    assert later["due_state"] == "later"
    assert unscheduled["days_remaining"] is None
    assert unscheduled["due_marker"] == "☐"
    assert unscheduled["due_state"] == "none"


def test_prepare_issue_uses_custom_due_marker_thresholds(today) -> None:
    base = {
        "number": 1,
        "title": "Example",
        "state": "open",
        "repository": "owner/repo",
        "fields": {"Status": "Open"},
    }

    soon_boundary = prepare_issue(
        {**base, "fields": {"Status": "Open", "Due Date": "2026-06-25"}},
        today,
        due_soon_days=5,
        due_upcoming_days=10,
    )
    upcoming_start = prepare_issue(
        {**base, "fields": {"Status": "Open", "Due Date": "2026-06-26"}},
        today,
        due_soon_days=5,
        due_upcoming_days=10,
    )
    upcoming_boundary = prepare_issue(
        {**base, "fields": {"Status": "Open", "Due Date": "2026-06-30"}},
        today,
        due_soon_days=5,
        due_upcoming_days=10,
    )
    later_start = prepare_issue(
        {**base, "fields": {"Status": "Open", "Due Date": "2026-07-01"}},
        today,
        due_soon_days=5,
        due_upcoming_days=10,
    )

    assert soon_boundary["days_remaining"] == 5
    assert soon_boundary["due_marker"] == "⚠️"
    assert soon_boundary["due_state"] == "soon"
    assert upcoming_start["days_remaining"] == 6
    assert upcoming_start["due_marker"] == "📅"
    assert upcoming_start["due_state"] == "upcoming"
    assert upcoming_boundary["days_remaining"] == 10
    assert upcoming_boundary["due_marker"] == "📅"
    assert upcoming_boundary["due_state"] == "upcoming"
    assert later_start["days_remaining"] == 11
    assert later_start["due_marker"] == "💤"
    assert later_start["due_state"] == "later"


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
