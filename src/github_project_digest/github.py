"""GitHub GraphQL access for Project v2 items."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport

"""@var GRAPHQL_ENDPOINT
@brief GitHub GraphQL API endpoint used for Project v2 queries.
@details
Project v2 data is retrieved through GitHub's GraphQL API because Projects,
Project fields, field values, and issue content relationships are represented
more naturally through GraphQL than through the REST API.  The endpoint is kept
as a constant because this tool targets GitHub.com rather than GitHub Enterprise
Server at this stage.
"""
GRAPHQL_ENDPOINT = "https://api.github.com/graphql"


class GitHubProjectClient:
    """@class GitHubProjectClient
    @brief Small GitHub GraphQL client focused on Project v2 item retrieval.
    @details
    The client owns the transport-level details for GitHub GraphQL access while
    leaving configuration, authentication selection, filtering, normalization,
    and rendering to their own modules.  This keeps the GitHub boundary narrow:
    callers provide an already-resolved token and receive raw Project item data
    that can be normalized elsewhere.

    The client deliberately loads GraphQL documents from files instead of
    embedding query strings in Python.  That separation makes it easier to
    inspect and revise the GitHub query shape without mixing API structure with
    application control flow.
    """

    def __init__(self, token: str) -> None:
        transport = RequestsHTTPTransport(
            url=GRAPHQL_ENDPOINT,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            },
            timeout=30,
        )
        self._client = Client(transport=transport, fetch_schema_from_transport=False)

    def resolve_user_login(self, user: str) -> str:
        """Resolve @me to the authenticated viewer login; otherwise validate a login."""

        requested = (user or "@me").strip()
        if requested.lower() == "@me":
            result = self._client.execute(gql(_load_query("viewer_login.graphql")))
            login = ((result.get("viewer") or {}).get("login") or "").strip()
            if not login:
                raise RuntimeError("Could not resolve @me to the authenticated GitHub login")
            return login

        return requested.lstrip("@")

    def fetch_project_items(
        self,
        *,
        owner: str,
        project_number: int,
        owner_type: str,
        assignee_login: str,
        page_size: int,
        field_value_limit: int,
    ) -> dict[str, Any]:
        """Fetch all visible items from a GitHub Project v2 board."""

        query_file = "project_items_user.graphql" if owner_type == "user" else "project_items.graphql"
        query_text = _load_query(query_file)
        query = gql(query_text)

        cursor: str | None = None
        nodes: list[dict[str, Any]] = []
        project_info: dict[str, Any] | None = None
        assignee_info: dict[str, Any] | None = None

        while True:
            result = self._client.execute(
                query,
                variable_values={
                    "owner": owner,
                    "projectNumber": project_number,
                    "assigneeLogin": assignee_login,
                    "cursor": cursor,
                    "pageSize": page_size,
                    "fieldValueLimit": field_value_limit,
                },
            )
            owner_node = result.get("user") if owner_type == "user" else result.get("organization")
            if not owner_node:
                raise RuntimeError(f"Could not find {owner_type} owner: {owner}")

            assignee_info = assignee_info or result.get("assignee")
            if not assignee_info:
                raise RuntimeError(f"Could not resolve assignee GitHub user: {assignee_login}")

            project = owner_node.get("projectV2")
            if not project:
                raise RuntimeError(f"Could not find Project v2 number {project_number} for {owner}")

            if project_info is None:
                project_info = {
                    "id": project.get("id"),
                    "title": project.get("title"),
                    "url": project.get("url"),
                    "owner": owner,
                    "number": project_number,
                    "owner_type": owner_type,
                }

            item_connection = project.get("items") or {}
            nodes.extend(item for item in item_connection.get("nodes") or [] if item)

            page_info = item_connection.get("pageInfo") or {}
            if not page_info.get("hasNextPage"):
                break
            cursor = page_info.get("endCursor")

        return {"project": project_info or {}, "assignee": assignee_info or {}, "items": nodes}


def _load_query(filename: str) -> str:
    root = Path(__file__).resolve().parents[2]
    return (root / "graphql" / filename).read_text(encoding="utf-8")
