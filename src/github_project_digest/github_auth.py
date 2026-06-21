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
        """@fn configured(self)
        @brief Report whether GitHub App authentication can be attempted.
        @details
        GitHub App authentication requires an App ID, an installation ID, and a
        private key source.  This property performs only a completeness check;
        it does not validate that the credentials are correct or authorized.
        That distinction keeps configuration selection separate from network
        authentication failures.

        @returns `True` when the required GitHub App fields are present.

        @par Examples
        @code
        if app_config.configured:
            token = create_installation_token(app_config)
        @endcode
        """

        return bool(
            self.app_id
            and self.installation_id
            and (self.private_key or self.private_key_file)
        )


def resolve_github_token(token: str | None, app: GitHubAppConfig) -> str:
    """@fn resolve_github_token(token, app)
    @brief Return the token used for GitHub API calls.
    @details
    Direct tokens intentionally take precedence over GitHub App credentials.
    This preserves the simplest local workflow while allowing scheduled jobs to
    switch to GitHub App authentication by omitting `GITHUB_TOKEN` and supplying
    App credentials instead.

    @param token Direct GitHub token, usually from `GITHUB_TOKEN`.
    @param app GitHub App configuration used when no direct token is supplied.
    @returns GitHub API token suitable for REST or GraphQL requests.

    @par Examples
    @code
    github_token = resolve_github_token(config.github_token, config.github_app)
    @endcode
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
    """@fn create_installation_token(app)
    @brief Create a short-lived GitHub App installation access token.
    @details
    GitHub Apps authenticate in two steps: first by signing a JWT as the App,
    then by exchanging that JWT for an installation token.  This function owns
    the exchange step and returns the token used by the rest of the application.

    The returned token is intentionally short-lived, making it a better fit for
    scheduled automation than a long-lived PAT when the deployment environment
    can safely store the App private key.

    @param app GitHub App configuration containing App ID, installation ID, and
               a private key source.
    @returns Installation access token returned by GitHub.

    @par Examples
    @code
    token = create_installation_token(app_config)
    @endcode
    """

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
    """@fn create_app_jwt(app_id, private_key)
    @brief Create the signed JWT GitHub requires for App authentication.
    @details
    GitHub requires the App JWT to identify the App and expire quickly.  The
    issued-at time is backdated slightly to tolerate small clock differences
    between the runner and GitHub, while the expiration stays within GitHub's
    short validity window.

    @param app_id GitHub App identifier.
    @param private_key PEM-formatted private key used to sign the JWT.
    @returns Encoded JWT string.

    @par Examples
    @code
    app_jwt = create_app_jwt(app_id, private_key)
    @endcode
    """

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
    """@fn load_private_key(app)
    @brief Load a GitHub App private key from text or a file path.
    @details
    Deployment environments handle multiline secrets differently.  Inline text
    is convenient for some secret stores, while file paths are safer and easier
    for systems such as Jenkins secret files or mounted Docker secrets.  This
    helper supports both without changing the authentication flow.

    @param app GitHub App configuration containing one private key source.
    @returns PEM-formatted private key text.

    @par Examples
    @code
    private_key = load_private_key(app_config)
    @endcode
    """

    if app.private_key:
        return _normalize_private_key(app.private_key)

    if app.private_key_file:
        return Path(app.private_key_file).read_text(encoding="utf-8")

    raise ValueError("GitHub App private key or private key file is required")


def _normalize_private_key(value: str) -> str:
    """@fn _normalize_private_key(value)
    @brief Normalize private-key text supplied through an environment variable.
    @details
    Some CI systems preserve multiline secrets as literal backslash-n sequences.
    PyJWT expects real newline characters in PEM material, so this helper turns
    that escaped representation back into a usable private key while leaving
    already-multiline values unchanged.

    @param value Raw private key value from configuration.
    @returns Normalized private key text.

    @par Examples
    @code
    private_key = _normalize_private_key(raw_private_key)
    @endcode
    """

    stripped = value.strip()
    if "\\n" in stripped and "\n" not in stripped:
        return stripped.replace("\\n", "\n")
    return stripped
