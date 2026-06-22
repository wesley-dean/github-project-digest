# github-project-digest

MVP Python project that fetches GitHub Project v2 items with GraphQL, applies a small local filter, renders the results through Jinja2, writes the output to STDOUT, and can optionally send a single email through SMTP.

## What it does

1. Loads configuration from environment variables or `.env`.
2. Uses `gql` with the requests transport to call the GitHub GraphQL API.
3. Fetches visible items from a GitHub Project v2 board.
4. Normalizes issue and Project field data.
5. Applies a small MVP filter locally.
6. Renders either plain text or HTML with Jinja2.
7. Writes the result to STDOUT.
8. Optionally sends a multipart plain-text/HTML email through SMTP when `GITHUB_USER` includes an email address.

## Requirements

- Python 3.11+
- A GitHub token with access to the Project, or GitHub App credentials capable of minting an installation token.
- For GitHub Project reads, GitHub documents `read:project` for queries. Depending on token type, App permissions, and org policy, you may also need repository read access for private issue repositories.

## Setup

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .
cp .env.example .env
```

Edit `.env`.

```dotenv
# Option 1: direct token/PAT. This takes precedence when set.
GITHUB_TOKEN=replace_me

# Option 2: GitHub App authentication. Used only when GITHUB_TOKEN is empty.
GITHUB_APP_ID=
GITHUB_APP_INSTALLATION_ID=
GITHUB_APP_PRIVATE_KEY=
GITHUB_APP_PRIVATE_KEY_FILE=

GITHUB_PROJECT_OWNER=octo-org
GITHUB_PROJECT_NUMBER=5
GITHUB_PROJECT_OWNER_TYPE=organization
GITHUB_USER=@me
GITHUB_PROJECT_FILTER=sprint:@current assignee:@user is:issue state:open
DIGEST_OUTPUT_FORMAT=text
DUE_SOON_DAYS=2
DUE_UPCOMING_DAYS=7
```

For a user-owned Project, set:

```dotenv
GITHUB_PROJECT_OWNER_TYPE=user
```

## Run

```bash
github-project-digest
```

Or:

```bash
python -m github_project_digest.cli
```

## Output formats

Set `DIGEST_OUTPUT_FORMAT` to one of:

- `text`
- `html`
- `json`
- `yaml`

`text` and `html` use these templates:

```text
templates/digest.txt.j2
templates/digest.html.j2
```

## Authentication modes

The tool supports two GitHub authentication modes.

The simplest mode is a direct token/PAT:

```dotenv
GITHUB_TOKEN=replace_me
```

For scheduled automation, you can instead use a GitHub App installation. Leave `GITHUB_TOKEN` empty and provide App credentials:

```dotenv
GITHUB_TOKEN=
GITHUB_APP_ID=123456
GITHUB_APP_INSTALLATION_ID=98765432
GITHUB_APP_PRIVATE_KEY_FILE=/run/secrets/github-app.pem
```

You may also provide the PEM text directly through `GITHUB_APP_PRIVATE_KEY`, which is useful for CI systems that store secrets as text. Literal `\n` sequences are converted to real newlines before signing the JWT.

If both are set, `GITHUB_TOKEN` wins. The GitHub App mode generates a short-lived installation token and then uses the same GraphQL code path as PAT mode.

## SMTP email delivery

By default, the digest is written to STDOUT only. To also send the digest by email, set `GITHUB_USER` to `username:email@example.com` and provide the required SMTP settings. The script currently supports a single destination address per run.

The email is sent as a multipart message using both templates:

- `templates/digest.txt.j2` for `text/plain`
- `templates/digest.html.j2` for `text/html`

For Gmail SMTP, use `smtp.gmail.com`, port `587`, `SMTP_USE_TLS=true`, and a Gmail app password. Do not use your normal Google account password.

If `GITHUB_USER` does not include an email address, no email is sent. STDOUT output still follows `DIGEST_OUTPUT_FORMAT`, which keeps local testing and GitHub Actions logging useful.

## Selecting the assignee

Set `GITHUB_USER` to the GitHub login whose assigned issues should be included. It defaults to `@me`, which resolves to the authenticated token owner through GraphQL. To send email, append a destination address after a colon.

```dotenv
GITHUB_USER=@me
# or
GITHUB_USER=octocat
# or
GITHUB_USER=octocat:octocat@example.com
```

This makes shell iteration straightforward:

```bash
for GITHUB_USER in wesley-dean:wesley-dean@example.com joe-dean:joe-dean@example.com; do
  github-project-digest
done
```

The ordinary shell `USER` variable is intentionally ignored so local shells and GitHub Actions runners cannot accidentally change the digest assignee.

The Project item query accepts the resolved assignee login as the GraphQL variable `$assigneeLogin`. GitHub Project v2 does not expose the same full filter syntax as the Project UI through this query, so this script still applies the supported MVP filter locally after fetching the Project items.

## Supported MVP filter terms

This is not a full clone of GitHub Project UI search syntax. It supports only:

- `sprint:@current`
- `iteration:@current`
- `assignee:@user` or `assignee:@me`, both resolving to the configured `GITHUB_USER` value
- `assignee:<login>`
- `user:@user` or `user:@me` as aliases for `assignee:@user`
- `user:<login>` as an alias for `assignee:<login>`
- `is:issue`
- `is:pr`
- `is:pullrequest`
- `state:open`
- `state:closed`
- `status:open` as an alias for `state:open`
- `status:closed` as an alias for `state:closed`

The default is:

```text
sprint:@current assignee:@user is:issue state:open
```

## Notes and limitations

The GitHub Projects UI filter syntax is not passed directly to GraphQL. This project fetches Project items and applies the supported subset locally.

The `sprint:@current` filter checks Project iteration fields named `Sprint` or `Iteration`. It treats an iteration as current when today's date falls between `startDate` inclusive and `startDate + duration` exclusive.

## Digest sections

Rendered digests group matching issues into these sections:

- Blocked: Project field `Status` is `Blocked`
- In Progress: Project field `Status` is `In Progress`
- Open: Project field `Status` is `Open`, or no more specific section applies
- Closed: Project field `Status` is `Done`, or the GitHub issue state is `closed`

Within each section, issues with a `Due Date` field sort before issues without one. Issues are then sorted by due date, followed by title.

Date markers:

- 💥 overdue
- 🚨 due today
- ⚠️ due in 1-2 days by default
- 📅 due in 3-7 days by default
- 💤 due in more than 7 days by default
- ☐ no due date

### Configuring due-date thresholds

The future due-date marker thresholds are configurable at runtime:

```dotenv
DUE_SOON_DAYS=2
DUE_UPCOMING_DAYS=7
```

`DUE_SOON_DAYS` controls the final day that uses the warning marker.  With the default value of `2`, issues due in 1 or 2 days use ⚠️.

`DUE_UPCOMING_DAYS` controls the final day that uses the calendar marker.  With the default value of `7`, issues due in 3 through 7 days use 📅, and issues due in more than 7 days use 💤.

For example, this configuration widens the warning and upcoming windows:

```dotenv
DUE_SOON_DAYS=5
DUE_UPCOMING_DAYS=14
```

With that configuration, issues due in 1-5 days use ⚠️, issues due in 6-14 days use 📅, and issues due in more than 14 days use 💤.

`DUE_SOON_DAYS` must be greater than or equal to `0`, and `DUE_UPCOMING_DAYS` must be greater than or equal to `DUE_SOON_DAYS`.

If your filter includes `state:open` or `status:open`, closed issues will normally be excluded before the Closed section is built. Remove that filter term if you want the digest to include closed/completed items.

## Running tests

Install the project with the development extras and run pytest:

```bash
python -m pip install -e '.[dev]'
PYTHONPATH=src pytest -q
```

The tests cover configuration loading, GitHub App token generation, filter parsing, local filtering, Project item normalization, digest grouping/sorting, text and HTML rendering, SMTP message construction, and GitHub client pagination behavior using mocked GraphQL responses.


## Container usage

Build the image:

```bash
podman build -t github-project-digest .
# or
# docker build -t github-project-digest .
```

Run with environment variables from a local `.env` file:

```bash
podman run --rm --env-file .env github-project-digest
# or
# docker run --rm --env-file .env github-project-digest
```

Run for a specific GitHub assignee and destination email:

```bash
podman run --rm \
  --env-file .env \
  -e GITHUB_USER='wesley-dean:wesley-dean@example.com' \
  github-project-digest
```

Iterate across multiple users from the shell:

```bash
for GITHUB_USER in \
  wesley-dean:wesley-dean@example.com \
  joe-dean:joe-dean@example.com
do
  podman run --rm \
    --env-file .env \
    -e GITHUB_USER="$GITHUB_USER" \
    github-project-digest
done
```

The image entrypoint is `github-project-digest`, so command-line arguments are not required. The container intentionally does not include your `.env` file; pass secrets at runtime with `--env-file`, individual `-e` values, or your CI/CD secret mechanism.

## GitHub Actions unit tests

This repository includes a workflow at `.github/workflows/tests.yml` that runs the pytest suite on pushes, pull requests, and manual dispatches. The workflow tests against Python 3.11 and 3.12.
