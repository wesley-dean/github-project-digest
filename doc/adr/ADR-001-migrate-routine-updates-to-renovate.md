# ADR-001: Migrate Routine Dependency Updates to Centrally Managed Renovate

Date: 2026-11-26

## Status

Accepted

## Decision

Routine dependency version updates SHALL be managed through the existing
Jenkins-hosted Renovate service, with explicit enrollment through a minimal
root `renovate.json`. Both configured Dependabot ecosystems, GitHub Actions
and pip, SHALL set `open-pull-requests-limit: 0`. All other Dependabot
metadata is retained to preserve the distinction between routine version
updates and independent vulnerability-driven security updates.

Existing `dependabot[bot]`-specific non-major auto-merge behavior, GitHub
required checks, code-owner approvals, and branch protections SHALL remain
independent of Renovate. The migration authorizes neither automatic
approval nor weakened review protection.

## Context and Constraints

Maintaining regular version updates through both Dependabot and the
centrally configured Jenkins Renovate instance would produce duplicate PRs
and repeat review effort. This repository generates GitHub Project reports
and may deliver them over SMTP; dependency maintenance must not change
GraphQL access, email credentials, Jinja2 rendering, CLI behavior, or its
existing CI and publishing authority.

## Assumptions

- Jenkins already discovers `wesley-dean/*` and uses explicit repository
  enrollment to select work.
- The maintainer grants the Renovate machine account access at PR approval.
- GitHub vulnerability alerts and Dependabot security-update settings are
  administered separately from routine version-update YAML.
- Required checks and code-owner approval continue to gate native auto-merge.
- Configuration merge is not evidence of subsequent successful Renovate runs.

## Options Considered

1. Continue scheduled Dependabot updates. Rejected as redundant with Renovate.
2. Delete Dependabot configuration entirely. Rejected to preserve metadata
   and independent security-response handling.
3. Add a per-repository Renovate workflow, secrets, or Jenkins job. Rejected
   because central orchestration already exists.
4. Extend the Dependabot auto-merge workflow to Renovate. Rejected to keep
   the separate identities and human approval boundary intact.
5. Replace all immutable action SHAs with mutable tags. Rejected except when
   a SHA cannot be mapped to an upstream release after investigation.

## Consequences, Threats, and Rollout

The migration adds Renovate enrollment, disables scheduled routine
Dependabot version PRs in each existing ecosystem, and normalizes
incompatible action version comments only when exact upstream release
provenance is verified. Any unverified action SHA may be replaced by a
valid moving `@version` reference without the obsolete `# pin@` comment,
so Renovate can resolve and pin it in a follow-up proposal. Such a reference
temporarily reduces supply-chain immutability and must be prominently
documented and reviewed before it is relied upon in privileged publishing.

Once a migration PR exists, conclusively routine Dependabot PRs may be
closed with an explanatory migration link. Security or ambiguous PRs
must remain open. None of these configuration changes proves that a
Renovate update was created or validated; existing checks, approval gates,
signed-commit policy, and review of privileged releases remain required.

## Related Decisions

ADR-000 governs capability honesty and separation of concerns. This ADR
does not change application architecture, credential boundaries, or
published runtime behavior.
