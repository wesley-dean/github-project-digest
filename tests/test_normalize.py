from __future__ import annotations

from datetime import date

from github_project_digest import normalize as normalize_module
from github_project_digest.normalize import normalize_project


class FixedDate(date):
    @classmethod
    def today(cls) -> date:
        return cls(2026, 6, 20)


def test_normalize_project_extracts_content_and_project_fields(monkeypatch) -> None:
    monkeypatch.setattr(normalize_module, "date", FixedDate)
    raw = {
        "project": {"title": "Project Tracker"},
        "assignee": {"login": "wesley-dean"},
        "items": [
            {
                "id": "PVTI_1",
                "content": {
                    "__typename": "Issue",
                    "id": "I_1",
                    "number": 42,
                    "title": "Example issue",
                    "url": "https://github.com/owner/repo/issues/42",
                    "state": "OPEN",
                    "repository": {
                        "nameWithOwner": "owner/repo",
                        "url": "https://github.com/owner/repo",
                    },
                    "assignees": {"nodes": [{"login": "wesley-dean"}]},
                },
                "fieldValues": {
                    "nodes": [
                        {
                            "__typename": "ProjectV2ItemFieldSingleSelectValue",
                            "name": "In Progress",
                            "field": {"name": "Status"},
                        },
                        {
                            "__typename": "ProjectV2ItemFieldDateValue",
                            "date": "2026-06-20",
                            "field": {"name": "Due Date"},
                        },
                        {
                            "__typename": "ProjectV2ItemFieldIterationValue",
                            "title": "Sprint 1",
                            "startDate": "2026-06-15",
                            "duration": 14,
                            "field": {"name": "Sprint"},
                        },
                    ]
                },
            }
        ],
    }

    normalized = normalize_project(raw)
    item = normalized["items"][0]

    assert normalized["project"] == {"title": "Project Tracker"}
    assert normalized["assignee"] == {"login": "wesley-dean"}
    assert item["project_item_id"] == "PVTI_1"
    assert item["content_type"] == "Issue"
    assert item["state"] == "open"
    assert item["repository"] == "owner/repo"
    assert item["assignees"] == ["wesley-dean"]
    assert item["fields"]["Status"] == "In Progress"
    assert item["fields"]["Due Date"] == "2026-06-20"
    assert item["fields"]["Sprint"]["is_current"] is True
