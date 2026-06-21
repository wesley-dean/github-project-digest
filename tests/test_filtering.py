from __future__ import annotations

from github_project_digest.filtering import apply_filter, parse_filter


def test_parse_filter_resolves_user_aliases() -> None:
    parsed = parse_filter("sprint:@current user:@me is:issue status:open", "wesley-dean")

    assert parsed.assignee == "wesley-dean"
    assert parsed.content_type == "Issue"
    assert parsed.state == "open"
    assert parsed.current_sprint is True


def test_parse_filter_accepts_user_variable_alias() -> None:
    parsed = parse_filter("assignee:@user is:issue state:open", "octocat")

    assert parsed.assignee == "octocat"
    assert parsed.content_type == "Issue"
    assert parsed.state == "open"


def test_apply_filter_keeps_only_current_open_assigned_issues(sample_items) -> None:
    parsed = parse_filter("sprint:@current assignee:@user is:issue state:open", "wesley-dean")

    filtered = apply_filter(sample_items, parsed)

    assert [item["number"] for item in filtered] == [1, 2, 3, 4]
