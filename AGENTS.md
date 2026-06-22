# AGENTS.md

## Purpose

`github-project-digest` generates a personalized digest of GitHub Project v2 work items.

The tool retrieves Project data from GitHub, filters items for a selected user, organizes the results into meaningful workflow sections, renders the results using Jinja2 templates, optionally delivers the digest through SMTP email, and writes the selected output format to STDOUT.

Typical use cases include:

- Daily task list emails
- Jenkins scheduled jobs
- Cron jobs
- Dockerized automation
- GitHub Actions
- Team reporting workflows

The project intentionally favors simplicity, portability, and transparency over heavy framework usage.

## High-Level Data Flow

The application follows a linear pipeline:

```text
Configuration
    ↓
Authentication
    ↓
GitHub GraphQL Query
    ↓
Normalization
    ↓
Filtering
    ↓
Digest Preparation
    ↓
Template Rendering
    ↓
SMTP Delivery (optional)
    ↓
STDOUT Output
```

The orchestration entrypoint is:

```text
src/github_project_digest/cli.py
```

## Architecture Overview

### `config.py`

Loads environment variables and `.env` files.

Produces a single immutable `Config` object.

Responsibilities:

- Parse configuration
- Validate required values
- Parse `GITHUB_USER`
- Build SMTP configuration
- Select GitHub authentication mode

No other module should directly read environment variables.

### `github_auth.py`

Resolves GitHub authentication.

Supported authentication modes:

1. Personal Access Token (PAT)
2. GitHub App installation token

PAT authentication remains supported because it is the simplest local-development experience.

GitHub App authentication exists for production automation.

Authentication selection occurs before GraphQL access.

### `github.py`

GitHub GraphQL access layer.

Responsibilities:

- Build the GraphQL client
- Resolve `@me`
- Load `.graphql` query files
- Execute Project queries
- Handle pagination
- Validate Project existence

This module should not contain filtering or business logic.

### `normalize.py`

Converts GitHub GraphQL responses into the application's internal representation.

This layer exists so downstream code never needs to understand GitHub GraphQL structures.

All filtering, digest generation, and rendering operate on normalized objects.

If GitHub changes its GraphQL schema, most required updates should be isolated here.

### `filtering.py`

Implements the digest filter language.

The filter language intentionally supports only a subset of GitHub's syntax.

Current examples:

```text
sprint:@current
assignee:@user
is:issue
state:open
```

Filtering occurs after normalization.

This design keeps GraphQL queries focused and allows filter behavior to evolve independently.

### `digest.py`

Core business logic.

Responsibilities:

- Issue classification
- Workflow grouping
- Due-date interpretation
- Summary generation
- Sorting

This module contains most of the product behavior.

Changes here will affect digest output semantics.

### `render.py`

Jinja2 rendering layer.

Responsibilities:

- Template loading
- Template rendering
- Jinja2 configuration

Templates contain presentation logic only.

Business logic belongs elsewhere.

### `emailer.py`

SMTP delivery layer.

Supports:

- Plain text email
- Multipart text/HTML email
- STARTTLS
- SSL/TLS
- Optional authentication

Email delivery is optional.

The digest should remain fully usable without SMTP.

### `cli.py`

Application entrypoint.

Coordinates the complete pipeline.

This module should remain thin.

Avoid placing business logic here.

## Templates

Templates live in:

```text
templates/
```

Current templates:

```text
digest.txt.j2
digest.html.j2
```

Templates receive prepared digest data.

Templates should not:

- Perform filtering
- Perform sorting
- Compute due-date state
- Classify issues

Those responsibilities belong in Python code.

## Digest Semantics

Current workflow sections:

1. Blocked
2. In Progress
3. Open
4. Closed

Ordering is intentional.

Do not reorder without a strong product reason.

### Due-Date Indicators

Meaning of symbols:

| Symbol | Meaning |
| --- | --- |
| 💥 | Overdue |
| 🚨 | Due today |
| ⚠️ | Due in 1-2 days |
| 📅 | Due in 3-7 days |
| 💤 | Due in more than 7 days |
| ☐ | No due date |

These symbols are part of the user-facing digest vocabulary.

## User Selection

The selected GitHub user is controlled by:

```text
GITHUB_USER
```

Examples:

```text
@me

wesley-dean

wesley-dean:wes@example.com
```

Format:

```text
github-login:email-address
```

When an email address is present:

- SMTP delivery is enabled
- The digest still writes to STDOUT

This design enables shell fan-out loops such as:

```bash
for GITHUB_USER in \
    wesley-dean:wes@example.com \
    octocat:octocat@example.com
do
    github-project-digest
done
```

## GraphQL Queries

GraphQL documents live in:

```text
graphql/
```

Queries are intentionally stored outside Python.

Benefits:

- Easier maintenance
- Easier review
- Easier experimentation
- Cleaner separation of concerns

Avoid embedding large GraphQL strings in Python code.

## Testing Philosophy

Tests should validate:

1. Normalization behavior
2. Filtering behavior
3. Digest classification
4. Due-date handling
5. Rendering expectations

Tests should avoid unnecessary dependency on GitHub APIs.

Mock normalized data whenever possible.

## Documentation Standard

This repository follows a Doxygen-style documentation convention inspired by the companion project `sync_github_org_team`.

Expected elements:

### Files

```python
@file
@brief
@details
```

### Classes

```python
@class
@brief
@details
```

### Functions

```python
@fn
@brief
@details
@param
@returns
@par Examples
@code
@endcode
```

### Constants

```python
@var
@brief
@details
```

Documentation should explain:

- What
- Why
- How
- Design rationale

Do not limit comments to implementation details.

## Design Principles

1. Keep modules focused.
2. Keep business logic out of templates.
3. Keep GitHub-specific logic isolated.
4. Normalize early.
5. Filter after normalization.
6. Render from prepared data.
7. Preserve STDOUT usability even when email delivery is enabled.
8. Favor readability over cleverness.
9. Prefer explicit behavior over hidden magic.
10. Document architectural intent, not merely implementation details.

## If You Are an AI Coding Agent

Before making changes:

1. Read this file.
2. Read `cli.py` to understand application flow.
3. Read `digest.py` to understand business behavior.
4. Read `normalize.py` before modifying GraphQL handling.
5. Read existing Doxygen comments before introducing new functionality.
6. Preserve separation of concerns.
7. Update documentation alongside code changes.

If a change requires modifying both templates and Python logic, prefer implementing behavior in Python and exposing prepared data to templates.
