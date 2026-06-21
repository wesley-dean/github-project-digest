"""Authentication helpers for GitHub API access.

The tool supports two authentication modes:

1. A direct token supplied as GITHUB_TOKEN, usually a PAT.
2. A GitHub App installation token generated from App credentials.

PAT authentication remains the simplest path for local use. GitHub App
authentication is better for scheduled automation because the generated
installation token is short lived and can be scoped to the App installation.
"""

from __future__ import annotations

from dataclasses import dataclass
import time
from pathlib import Path

import jwt
import requests

GITHUB_API_ROOT = "https://api.github.com"
INSTALLATION_TOKEN_URL = f"{GITHUB_API_ROOT}/app/installations/{{installation_id}}/access_tokens"


@dataclass(frozen=True)
class GitHubAppConfig:
    """@class GitHubAppConfig
    @brief Configuration required to mint a GitHub App installation token.
    @details
    This dataclass keeps GitHub App credentials together without forcing GitHub
    App authentication to replace PAT authentication.  The tool can therefore
    remain easy to run locally with `GITHUB_TOKEN` while supporting a stronger
    scheduled-automation model through short-lived installation tokens.

    The private key may be supplied directly or through a file path.  Supporting
    both forms keeps the tool usable in Jenkins, Docker, GitHub Actions, and
    ordinary shell sessions where secret storage mechanisms differ.
    """

    app_id: str | None = None
    installation_id: str | None = None
    private_key: str | None = None
    private_key_file: str | None = None

    @property
    def configured(self) -> bool:
        """Return True when enough GitHub App settings were provided."""

        return bool(
            self.app_id
            and self.installation_id
            and (self.private_key or self.private_key_file)
        )


def resolve_github_token(token: str | None, app: GitHubAppConfig) -> str:
    """Return a usable GitHub API token.

    A direct token wins when GITHUB_TOKEN is set. If no direct token is
    provided, GitHub App credentials are used to mint an installation token.
    """

    if token:
        return token

    if not app.configured:
        raise ValueError(
            "Missing GitHub authentication. Set GITHUB_TOKEN or provide "
            "GITHUB_APP_ID, GITHUB_APP_INSTALLATION_ID, and either "
            "GITHUB_APP_PRIVATE_KEY or GITHUB_APP_PRIVATE_KEY_FILE."
        )

    return create_installation_token(app)


def create_installation_token(app: GitHubAppConfig) -> str:
    """Create a short-lived GitHub App installation access token."""

    if not app.app_id or not app.installation_id:
        raise ValueError("GitHub App ID and installation ID are required")

    private_key = load_private_key(app)
    app_jwt = create_app_jwt(app.app_id, private_key)

    response = requests.post(
        INSTALLATION_TOKEN_URL.format(installation_id=app.installation_id),
        headers={
            "Authorization": f"Bearer {app_jwt}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        timeout=30,
    )

    if response.status_code >= 400:
        body = response.text.strip()
        raise RuntimeError(
            f"Could not create GitHub App installation token "
            f"(HTTP {response.status_code}): {body}"
        )

    data = response.json()
    installation_token = (data.get("token") or "").strip()
    if not installation_token:
        raise RuntimeError("GitHub App installation token response did not include a token")

    return installation_token


def create_app_jwt(app_id: str, private_key: str) -> str:
    """Create the signed JWT GitHub requires for App authentication."""

    now = int(time.time())
    payload = {
        "iat": now - 60,
        "exp": now + 540,
        "iss": app_id,
    }
    token = jwt.encode(payload, private_key, algorithm="RS256")
    if isinstance(token, bytes):
        return token.decode("utf-8")
    return token


def load_private_key(app: GitHubAppConfig) -> str:
    """Load a GitHub App private key from text or a file path."""

    if app.private_key:
        return _normalize_private_key(app.private_key)

    if app.private_key_file:
        return Path(app.private_key_file).read_text(encoding="utf-8")

    raise ValueError("GitHub App private key or private key file is required")


def _normalize_private_key(value: str) -> str:
    """Normalize private-key text supplied through an environment variable.

    Jenkins and other CI systems often store multiline secrets with literal
    backslash-n sequences. Convert those into real newlines so PyJWT can parse
    the PEM document.
    """

    stripped = value.strip()
    if "\\n" in stripped and "\n" not in stripped:
        return stripped.replace("\\n", "\n")
    return stripped
