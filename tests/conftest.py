from __future__ import annotations

from datetime import date
from typing import Any

import pytest


@pytest.fixture
def today() -> date:
    return date(2026, 6, 20)


@pytest.fixture
def sample_items() -> list[dict[str, Any]]:
    return [
        {
            "content_type": "Issue",
            "id": "I_open_overdue",
            "number": 1,
            "title": "Pay GEICO insurance",
            "url": "https://github.com/wesley-dean/tasks/issues/1",
            "state": "open",
            "repository": "wesley-dean/tasks",
            "assignees": ["wesley-dean"],
            "fields": {
                "Status": "Open",
                "Due Date": "2026-06-19",
                "Sprint": {
                    "title": "Sprint 1",
                    "start_date": "2026-06-15",
                    "duration": 14,
                    "is_current": True,
                },
            },
        },
        {
            "content_type": "Issue",
            "id": "I_open_today",
            "number": 2,
            "title": "Update E-ZPass",
            "url": "https://github.com/wesley-dean/tasks/issues/2",
            "state": "open",
            "repository": "wesley-dean/tasks",
            "assignees": ["wesley-dean"],
            "fields": {
                "Status": "Open",
                "Due Date": "2026-06-20",
                "Sprint": {"title": "Sprint 1", "is_current": True},
            },
        },
        {
            "content_type": "Issue",
            "id": "I_progress_future",
            "number": 3,
            "title": "Write launch copy",
            "url": "https://github.com/wesley-dean/tasks/issues/3",
            "state": "open",
            "repository": "wesley-dean/tasks",
            "assignees": ["wesley-dean"],
            "fields": {
                "Status": "In Progress",
                "Due Date": "2026-06-25",
                "Sprint": {"title": "Sprint 1", "is_current": True},
            },
        },
        {
            "content_type": "Issue",
            "id": "I_blocked_unscheduled",
            "number": 4,
            "title": "Blocked dependency",
            "url": "https://github.com/wesley-dean/tasks/issues/4",
            "state": "open",
            "repository": "wesley-dean/tasks",
            "assignees": ["wesley-dean"],
            "fields": {
                "Status": "Blocked",
                "Sprint": {"title": "Sprint 1", "is_current": True},
            },
        },
        {
            "content_type": "Issue",
            "id": "I_other_user",
            "number": 5,
            "title": "Someone else's task",
            "url": "https://github.com/wesley-dean/tasks/issues/5",
            "state": "open",
            "repository": "wesley-dean/tasks",
            "assignees": ["someone-else"],
            "fields": {
                "Status": "Open",
                "Sprint": {"title": "Sprint 1", "is_current": True},
            },
        },
        {
            "content_type": "Issue",
            "id": "I_closed",
            "number": 6,
            "title": "Finished work",
            "url": "https://github.com/wesley-dean/tasks/issues/6",
            "state": "closed",
            "repository": "wesley-dean/tasks",
            "assignees": ["wesley-dean"],
            "fields": {
                "Status": "Done",
                "Sprint": {"title": "Sprint 1", "is_current": True},
            },
        },
    ]
