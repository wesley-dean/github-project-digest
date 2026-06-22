from __future__ import annotations

from github_project_digest.digest import build_digest_sections, build_digest_summary
from github_project_digest.render import render_digest


def _context(sample_items, today):
    items = [
        sample_items[0],
        sample_items[1],
        sample_items[2],
        sample_items[3],
        {
            **sample_items[0],
            "id": "I_multi_assignee",
            "number": 7,
            "title": "Coordinate shared work",
            "url": "https://github.com/wesley-dean/tasks/issues/7",
            "assignees": ["wesley-dean", "joe-dean"],
            "fields": {"Status": "Open", "Due Date": "2026-06-24"},
        },
        {
            **sample_items[0],
            "id": "I_unassigned",
            "number": 8,
            "title": "Triage unowned work",
            "url": "https://github.com/wesley-dean/tasks/issues/8",
            "assignees": [],
            "fields": {"Status": "Open", "Due Date": "2026-06-26"},
        },
    ]
    current_assignee = "wesley-dean"
    return {
        "project": {
            "title": "Project Tracker",
            "url": "https://github.com/users/wesley-dean/projects/1",
        },
        "assignee": {"login": current_assignee},
        "requested_user": "@me",
        "filter_query": "sprint:@current is:issue state:open",
        "issues": items,
        "sections": build_digest_sections(items, today, current_assignee=current_assignee),
        "count": len(items),
        "summary": build_digest_summary(items, today),
    }


def test_text_template_renders_each_issue_on_separate_line(sample_items, today) -> None:
    output = render_digest("digest.txt.j2", _context(sample_items, today))

    assert "Open (4)" in output
    assert "- 💥 wesley-dean/tasks#1 Pay GEICO insurance • **wesley-dean** • due: 2026-06-19" in output
    assert "\n- 🚨 wesley-dean/tasks#2 Update E-ZPass • **wesley-dean** • due: 2026-06-20" in output
    assert "Coordinate shared work • **wesley-dean**, joe-dean • due: 2026-06-24" in output
    assert "Triage unowned work • unassigned • due: 2026-06-26" in output
    assert "Due:" not in output
    assert "2026-06-19- 🚨" not in output
    assert "Closed" not in output


def test_html_template_links_issue_titles_and_suppresses_empty_sections(sample_items, today) -> None:
    output = render_digest("digest.html.j2", _context(sample_items, today))

    assert '<a href="https://github.com/wesley-dean/tasks/issues/1"' in output
    assert "Pay GEICO insurance" in output
    assert "wesley-dean/tasks</span><span>&nbsp;&bull;&nbsp;</span><span><strong" in output
    assert "Coordinate shared work" in output
    assert "<strong style=&#34;color:#24292f;&#34;>wesley-dean</strong>, joe-dean" in output
    assert "Triage unowned work" in output
    assert "unassigned</span><span>&nbsp;&bull;&nbsp;</span><span" in output
    assert "due: 2026-06-19" in output
    assert "Due:" not in output
    assert "Blocked" in output
    assert "In Progress" in output
    assert "Closed" not in output
    assert "No matching issues found." not in output
