from __future__ import annotations

import sys
import types

# These tests exercise our wrapper logic without requiring the optional network
# client dependency to be installed in the test environment. A normal installed
# project will use the real gql package.
fake_gql_module = types.ModuleType("gql")
fake_gql_module.Client = lambda *args, **kwargs: None
fake_gql_module.gql = lambda query: query
fake_transport_module = types.ModuleType("gql.transport.requests")
fake_transport_module.RequestsHTTPTransport = lambda *args, **kwargs: None
sys.modules.setdefault("gql", fake_gql_module)
sys.modules.setdefault("gql.transport.requests", fake_transport_module)

from github_project_digest.github import GitHubProjectClient


class FakeGraphQLClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def execute(self, query, variable_values=None):
        self.calls.append(variable_values or {})
        if not self.responses:
            raise AssertionError("No fake GraphQL responses left")
        return self.responses.pop(0)


def test_resolve_user_login_resolves_me() -> None:
    client = GitHubProjectClient.__new__(GitHubProjectClient)
    fake = FakeGraphQLClient([{"viewer": {"login": "wesley-dean"}}])
    client._client = fake

    assert client.resolve_user_login("@me") == "wesley-dean"


def test_resolve_user_login_strips_leading_at_without_query() -> None:
    client = GitHubProjectClient.__new__(GitHubProjectClient)
    fake = FakeGraphQLClient([])
    client._client = fake

    assert client.resolve_user_login("@octocat") == "octocat"
    assert fake.calls == []


def test_fetch_project_items_paginates_user_project() -> None:
    client = GitHubProjectClient.__new__(GitHubProjectClient)
    fake = FakeGraphQLClient(
        [
            {
                "assignee": {"login": "wesley-dean"},
                "user": {
                    "projectV2": {
                        "id": "PVT_1",
                        "title": "Project Tracker",
                        "url": "https://github.com/users/wesley-dean/projects/1",
                        "items": {
                            "nodes": [{"id": "PVTI_1"}],
                            "pageInfo": {"hasNextPage": True, "endCursor": "cursor-1"},
                        },
                    }
                },
            },
            {
                "assignee": {"login": "wesley-dean"},
                "user": {
                    "projectV2": {
                        "id": "PVT_1",
                        "title": "Project Tracker",
                        "url": "https://github.com/users/wesley-dean/projects/1",
                        "items": {
                            "nodes": [{"id": "PVTI_2"}],
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                        },
                    }
                },
            },
        ]
    )
    client._client = fake

    result = client.fetch_project_items(
        owner="wesley-dean",
        project_number=1,
        owner_type="user",
        assignee_login="wesley-dean",
        page_size=50,
        field_value_limit=50,
    )

    assert result["project"]["title"] == "Project Tracker"
    assert result["assignee"] == {"login": "wesley-dean"}
    assert [item["id"] for item in result["items"]] == ["PVTI_1", "PVTI_2"]
    assert fake.calls[0]["cursor"] is None
    assert fake.calls[1]["cursor"] == "cursor-1"
    assert fake.calls[0]["assigneeLogin"] == "wesley-dean"
