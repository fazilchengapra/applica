# ADR-0001: Record Architecture Decisions

**Status:** Accepted
**Date:** 2026-08-02

## Context

As the system grows to multiple services, decisions about structure, tech choices,
and tradeoffs get made in Slack/standups and forgotten. New engineers can't tell
*why* something is the way it is.

## Decision

We will keep a lightweight Architecture Decision Record (ADR) for any decision
that's expensive to reverse: choice of gateway, database, service boundaries,
auth strategy, etc. One file per decision, numbered sequentially, using
[template.md](./template.md).

## Consequences

Small overhead per decision, but decisions become traceable and onboarding gets
faster since new engineers can read the "why," not just the "what."
