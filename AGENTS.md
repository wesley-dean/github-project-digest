# AGENTS.md

## Purpose

`github-project-digest` generates personalized digests of GitHub Project
v2 work items.

The tool retrieves Project data from GitHub, filters items for selected
users, organizes the results into meaningful workflow sections, renders
the results using Jinja2 templates, optionally delivers each digest
through SMTP email, and writes the selected output format to STDOUT.

Typical use cases include:

-   Daily task list emails
-   Jenkins scheduled jobs
-   Cron jobs
-   Dockerized automation
-   GitHub Actions
-   Team reporting workflows

The project intentionally favors simplicity, portability, and
transparency over heavy framework usage.

## Contributor Onboarding

Before implementing any feature, fixing a bug, or making documentation
changes, complete the following onboarding steps.

### 1. Read the project documentation

Review these files before making changes:

1.  `README.md`
    -   Understand the project's purpose, user-facing behavior,
        configuration, and supported workflows.
2.  `AGENTS.md`
    -   Understand the architectural design, module responsibilities,
        testing philosophy, documentation standards, and project
        conventions.
3.  `.github/PULL_REQUEST_TEMPLATE.md`
    -   Understand the information expected in pull requests so
        implementation notes, testing, and documentation are collected
        throughout development rather than reconstructed afterward.

These documents are the project's primary sources of truth.

### 2. Review the requested work

When available:

-   Read the associated GitHub Issue.
-   Read any linked discussions.
-   Review related pull requests if the issue references them.

Understand the requested behavior before proposing an implementation.

### 3. Produce a plan before changing code

For non-trivial work:

-   Produce a numbered implementation plan.
-   Separate implementation into logical phases.
-   Wait for approval before beginning implementation when working
    interactively.

Numbered plans make it easy to pause work, resume later, or request
implementation of a specific step.

### 4. Use the GitHub connector when available

When working in an environment that provides a GitHub connector:

-   Read repository files through the connector.
-   Retrieve Issues, Pull Requests, and repository metadata through the
    connector.
-   Commit changes through the connector when practical.

If direct Git access (for example, `git clone`) is unavailable because
the execution environment cannot reach GitHub, continue using the
connector rather than treating the task as blocked.

### 5. Ask questions

If requirements are ambiguous:

-   Ask before implementing.
-   Do not infer product behavior when clarification is inexpensive.
-   Distinguish assumptions from confirmed requirements.

### 6. Keep commits small

Prefer more commits rather than fewer.

Each commit should represent one logical change.

Good examples:

-   One configuration change
-   One implementation change
-   One unit-test update
-   One documentation update

Small commits simplify review, debugging, and regression analysis.

### 7. Update documentation with code

Behavioral changes should normally include corresponding documentation
updates.

Depending on the change, this may include:

-   `README.md`
-   `AGENTS.md`
-   Inline Doxygen documentation
-   Architecture comments
-   Examples

Documentation should evolve with the implementation rather than
afterward.

### 8. Follow the documentation standard

Python modules should follow the repository's Doxygen convention.

Document:

-   Files
-   Modules
-   Classes
-   Dataclasses
-   Global constants
-   Functions
-   Methods

Function documentation should describe:

-   Purpose
-   Design rationale
-   Assumptions
-   Parameters
-   Return values
-   Examples
-   Important implementation decisions

Documentation should explain not only *how* code works, but also *why*
it was implemented that way.

### 9. Test new behavior

New features should include unit tests whenever practical.

When modifying existing behavior:

-   Update affected tests
-   Add new tests covering new functionality
-   Preserve existing behavior unless the change intentionally modifies
    it

Behavior should be verified before opening a pull request.

### 10. Finish with the pull request

Before opening a pull request:

-   Review the implementation
-   Review commit history
-   Ensure documentation is complete
-   Ensure tests pass
-   Complete the repository's PR template

The pull request should clearly explain:

-   What changed
-   Why it changed
-   How it was tested
-   Any known limitations

## Additional Recommendation: Scope Management

If an unrelated defect is discovered while implementing a feature:

-   Fix it immediately if it blocks implementation or causes tests to
    fail.
-   Otherwise, stop and ask before expanding the scope.
-   Document incidental fixes in the pull request.

## Makefile Contributor Workflow

The repository includes a Makefile that provides the preferred local
interface for routine development tasks.

Contributors should start with:

``` text
make help
```

The default Make target is `help`, so running `make` without a target
should display the available commands rather than performing a mutating
operation.

Use the Makefile targets rather than hand-running long command chains
when a target exists.

Common local setup targets:

``` text
make venv
make deps
make dev-deps
```

Dependency target semantics:

-   `deps` installs the project and runtime dependencies into the local
    virtual environment.
-   `dev-deps` installs the project, runtime dependencies, and developer
    checker dependencies into the local virtual environment.
-   `system-deps` installs the project and developer checker dependencies
    with the system Python. It is a Python dependency installation target,
    not an operating-system package installation target.

Common quality targets:

``` text
make format
make check
make test
make all
```

`make all` intentionally runs the local quality workflow only:

1.  Runtime dependency installation
2.  Development dependency installation
3.  Formatting
4.  Checks
5.  Tests

`make all` must not install the console script into either
`~/.local/bin` or `/usr/local/bin`.

Installation targets are explicit:

``` text
make install
make system-install
```

`make install` installs the generated console script into `~/.local/bin`.
`make system-install` installs the generated console script into
`/usr/local/bin`.

When adapting this Makefile pattern to other Python projects, keep the
generic variables (`VENV`, `PYTHON`, `PIP`, `SRC_DIRS`, and related
settings) reusable and isolate project-specific values, such as the
console script name, behind variables.

## High-Level Data Flow

The application follows a linear pipeline:

``` text
Configuration
    ↓
Authentication
    ↓
For each configured user
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

``` text
src/github_project_digest/cli.py
```

## Architecture Overview

### `config.py`

Loads environment variables and `.env` files.

Produces a single immutable `Config` object.

Responsibilities:

-   Parse configuration
-   Validate required values
-   Parse `GITHUB_USER`
-   Build `ConfiguredUser` entries
-   Preserve first-user compatibility fields on `Config`
-   Load due-date marker thresholds
-   Load empty-digest email delivery preferences
-   Build per-user SMTP configuration
-   Select GitHub authentication mode

No other module should directly read environment variables.

### `github_auth.py`

Resolves GitHub authentication.

Supported authentication modes:

1.  Personal Access Token (PAT)
2.  GitHub App installation token

PAT authentication remains supported because it is the simplest
local-development experience.

GitHub App authentication exists for production automation.

Authentication selection occurs before GraphQL access.

### `github.py`

GitHub GraphQL access layer.

Responsibilities:

-   Build the GraphQL client
-   Resolve `@me`
-   Load `.graphql` query files
-   Execute Project queries
-   Handle pagination
-   Validate Project existence

This module should not contain filtering or business logic.

### `normalize.py`

Converts GitHub GraphQL responses into the application's internal
representation.

This layer exists so downstream code never needs to understand GitHub
GraphQL structures.

All filtering, digest generation, and rendering operate on normalized
objects.

If GitHub changes its GraphQL schema, most required updates should be
isolated here.

### `filtering.py`

Implements the digest filter language.

The filter language intentionally supports only a subset of GitHub's
syntax.

Current examples:

``` text
sprint:@current
assignee:@user
is:issue
state:open
```

Filtering occurs after normalization.

This design keeps GraphQL queries focused and allows filter behavior to
evolve independently.

### `digest.py`

Core business logic.

Responsibilities:

-   Issue classification
-   Workflow grouping
-   Due-date interpretation
-   Due-date marker threshold application
-   Assignee display preparation
-   Summary generation
-   Sorting

This module contains most of the product behavior.

Changes here will affect digest output semantics.

### `render.py`

Jinja2 rendering layer.

Responsibilities:

-   Template loading
-   Template rendering
-   Jinja2 configuration

Templates contain presentation logic only.

Business logic belongs elsewhere.

### `emailer.py`

SMTP delivery layer.

Supports:

-   Plain text email
-   Multipart text/HTML email
-   STARTTLS
-   SSL/TLS
-   Optional authentication

Email delivery is optional.

The digest should remain fully usable without SMTP.

### `cli.py`

Application entrypoint.

Coordinates the complete pipeline.

When `GITHUB_USER` contains multiple configured user entries, the CLI
performs fan-out by running the existing digest pipeline once per
configured user. This preserves the product rule that each rendered
digest has one selected GitHub user, one assignee context, one optional
email recipient, and one render pass.

#### Empty Digest Delivery

SMTP delivery is controlled independently from digest generation.

When a configured user has SMTP enabled:

-   `SEND_EMPTY_EMAIL=true` (default) preserves the historical behavior
    by delivering a rendered digest even when no issues match the
    configured filters.
-   `SEND_EMPTY_EMAIL=false` suppresses SMTP delivery when the rendered
    digest contains zero matching issues.

This configuration affects SMTP delivery only.

The application still:

-   Retrieves Project data
-   Applies filtering
-   Renders the digest
-   Produces STDOUT output

This separation preserves local debugging, CI logging, and scheduled-job
visibility while allowing administrators to suppress "nothing to report"
emails.

This module should remain thin.

Avoid placing business logic here.

## Templates

Templates live in:

``` text
templates/
```

Current templates:

``` text
digest.txt.j2
digest.html.j2
```

Templates receive prepared digest data.

Templates should not:

-   Perform filtering
-   Perform sorting
-   Compute due-date state
-   Apply due-date marker thresholds
-   Classify issues

Those responsibilities belong in Python code.

## Digest Semantics

Current workflow sections:

1.  Blocked
2.  In Progress
3.  Open
4.  Closed

Ordering is intentional.

Do not reorder without a strong product reason.

### Due-Date Indicators

Meaning of symbols:

  Symbol   Meaning
  -------- -------------
  💥       Overdue
  🚨       Due today
  ⚠️       Due soon
  📅       Upcoming
  💤       Later
  ☐        No due date

These symbols are part of the user-facing digest vocabulary.

Future due-date thresholds are runtime configuration:

``` text
DUE_SOON_DAYS=2
DUE_UPCOMING_DAYS=7
```

Defaults preserve the original behavior:

-   `DUE_SOON_DAYS=2`: issues due in 1-2 days use ⚠️.
-   `DUE_UPCOMING_DAYS=7`: issues due in 3-7 days use 📅.
-   Issues due after `DUE_UPCOMING_DAYS` use 💤.

Validation rules:

-   `DUE_SOON_DAYS` must be greater than or equal to `0`.
-   `DUE_UPCOMING_DAYS` must be greater than or equal to
    `DUE_SOON_DAYS`.

Configuration loading and validation belong in `config.py`. Marker
selection and due-state semantics belong in `digest.py`. Templates
should render prepared marker and due-state values rather than deriving
urgency themselves.

### Assignee Display Semantics

Assignee presentation is prepared in Python rather than computed in
templates.

Prepared issue data includes:

-   Assignee display metadata
-   Current-user identification
-   Unassigned fallback handling
-   Markdown-safe assignee rendering for text output

Templates should render prepared assignee data and should not determine
ownership semantics themselves.

User-facing behavior:

-   Multiple assignees are rendered as a comma-separated list.
-   Issues with no assignees display `unassigned`.
-   The selected digest user is visually emphasized when present in the
    assignee list.
-   Repository, assignee, and due-date metadata are displayed in that
    order.

Examples:

``` text
repository • assignee • due: YYYY-MM-DD
repository • assignee1, assignee2 • due: YYYY-MM-DD
repository • unassigned • due: YYYY-MM-DD
```

## User Selection

Configured GitHub users are controlled by:

``` text
GITHUB_USER
```

Single-user examples:

``` text
@me

wesley-dean

wesley-dean:wes@example.com
```

Fan-out examples:

``` text
wesley-dean,octocat

wesley-dean:wes@example.com,octocat:octocat@example.com

@me,octocat:octocat@example.com
```

Entry format:

``` text
github-login:email-address
```

When an email address is present on an entry:

-   SMTP delivery is enabled for that configured user.
-   The digest still writes to STDOUT.

Whitespace around commas is ignored.

Empty entries are invalid. For example, `wesley-dean,,octocat` should
raise a configuration error rather than silently skipping an entry.

Fan-out is not a multi-user digest. It is repeated one-user digest
generation:

``` text
load config
    ↓
for configured_user in users
    ↓
run existing digest pipeline
```

The existing first-user compatibility fields on `Config` exist to avoid
breaking older single-user call sites, but new orchestration should
prefer `Config.users`.

Shell fan-out loops still work, but built-in fan-out should be preferred
when one invocation should produce multiple per-user digests.

## GraphQL Queries

GraphQL documents live in:

``` text
graphql/
```

Queries are intentionally stored outside Python.

Benefits:

-   Easier maintenance
-   Easier review
-   Easier experimentation
-   Cleaner separation of concerns

Avoid embedding large GraphQL strings in Python code.

## Testing Philosophy

Tests should validate:

1.  Normalization behavior
2.  Filtering behavior
3.  Digest classification
4.  Due-date handling
5.  Configurable due-date threshold boundaries
6.  Rendering expectations
7.  Configured user parsing
8.  Fan-out STDOUT aggregation
9.  Per-user SMTP delivery behavior
10. Empty-digest SMTP delivery policy (`SEND_EMPTY_EMAIL`)
11. Configuration validation for runtime delivery options
12. Makefile-backed local development workflows when build tooling
    changes

Tests should avoid unnecessary dependency on GitHub APIs.

Mock normalized data whenever possible.

## Documentation Standard

This repository follows a Doxygen-style documentation convention
inspired by the companion project `sync_github_org_team`.

Expected elements:

### Files

``` python
@file
@brief
@details
```

### Classes

``` python
@class
@brief
@details
```

### Functions

``` python
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

``` python
@var
@brief
@details
```

Documentation should explain:

-   What
-   Why
-   How
-   Design rationale

Do not limit comments to implementation details.

## Design Principles

1.  Keep modules focused.
2.  Keep business logic out of templates.
3.  Keep GitHub-specific logic isolated.
4.  Normalize early.
5.  Filter after normalization.
6.  Render from prepared data.
7.  Preserve STDOUT usability even when email delivery is enabled.
8.  Favor readability over cleverness.
9.  Prefer explicit behavior over hidden magic.
10. Document architectural intent, not merely implementation details.
11. Preserve one-user-per-digest semantics when adding fan-out behavior.

## If You Are an AI Coding Agent

AI coding agents should complete the **Contributor Onboarding** process
before making changes.

In particular:

1.  Read the project documentation.
2.  Review the associated issue or pull request.
3.  Produce a numbered implementation plan for non-trivial work.
4.  Keep commits focused and small.
5.  Preserve the documented architecture and separation of concerns.
6.  Update documentation and tests alongside implementation.
