# Architecture Decisions

## ADR-001: Migrate Routine Dependency Updates to Centrally Managed Renovate

Routine GitHub Actions and pip version updates move from scheduled Dependabot
proposals to the centrally operated Jenkins Renovate runner, enrolled with
root `renovate.json`. Dependabot security responses remain independent;
required checks, code-owner approval, and verified immutable SHA pins remain
review controls. Any unverified SHA temporarily converted to a moving
version ref is documented for Renovate re-pinning and manual review.
This decision leaves GraphQL, SMTP, and application behavior unchanged.

See [ADR-001](adr/ADR-001-migrate-routine-updates-to-renovate.md).
