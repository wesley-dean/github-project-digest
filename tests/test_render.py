from __future__ import annotations

from github_project_digest.digest import build_digest_sections, build_digest_summary
from github_project_digest.render import render_digest


def _context(sample_items, today):
    items = sample_items[:4]
    return {
        "project": {
            "title": "Project Tracker",
            "url": "https://github.com/users/wesley-dean/projects/1",
        },
        "assignee": {"login": "wesley-dean"},
        "requested_user": "@me",
        "filter_query": "sprint:@current assignee:@user is:issue state:open",
        "issues": items,
        "sections": build_digest_sections(items, today),
        "count": len(items),
        "summary": build_digest_summary(items, today),
    }


def test_text_template_renders_each_issue_on_separate_line(sample_items, today) -> None:
    output = render_digest("digest.txt.j2", _context(sample_items, today))

    assert "Open (2)" in output
    assert "- 💥 wesley-dean/tasks#1 Pay GEICO insurance Due: 2026-06-19" in output
    assert "\n- 🚨 wesley-dean/tasks#2 Update E-ZPass Due: 2026-06-20" in output
    assert "2026-06-19- 🚨" not in output
    assert "Closed" not in output


def test_html_template_links_issue_titles_and_suppresses_empty_sections(sample_items, today) -> None:
    output = render_digest("digest.html.j2", _context(sample_items, today))

    assert '<a href="https://github.com/wesley-dean/tasks/issues/1"' in output
    assert "Pay GEICO insurance" in output
    assert "Blocked" in output
    assert "In Progress" in output
    assert "Closed" not in output
    assert "No matching issues found." not in output
