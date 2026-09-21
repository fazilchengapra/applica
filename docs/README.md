# Project Documentation

This is the single source of truth for how the system is built, deployed, and
operated.

> These docs describe the **actual repository state** — a docker-compose
> monorepo with three services behind Kong. Where an AWS/EKS/Terraform stack is
> referenced, it is marked **planned, not implemented**.

## How this is organized

| Folder | What lives here |
|---|---|
| `architecture/` | System-wide design: how services talk to each other, and why key decisions were made (ADRs) |
| `services/` | One folder per microservice. Each service's docs are self-contained and owned by whoever owns that service |
| `infrastructure/` | Docker-compose, Kong gateway config, CI/CD — anything cross-cutting to deployment |
| `api-reference/` | Generated OpenAPI/Swagger specs — not hand-written, produced by CI |
| `runbooks/` | "Something is on fire, what do I do" — incident response, rollback |
| `guides/` | Onboarding, local dev setup, coding standards, testing conventions |
| `changelog/` | Human-readable release history |

## Rule of thumb

- If it's **specific to one service**, it goes in `services/<service-name>/`.
- If it explains **why a service exists or how services interact**, it goes in `architecture/`.
- If it's about **running/deploying anything**, it goes in `infrastructure/` or `runbooks/`.
- If it's **generated from code** (OpenAPI schema, docstrings), it goes in `api-reference/` and is never edited by hand.

## Quick links

- [System overview](./architecture/system-overview.md) — services, request flows, diagrams
- [Service map](./architecture/service-map.md) — apps/modules per service
- [Mock interview system (design, planned)](./architecture/mock-interview.md) — LiveKit + agent design, ADR-0004
- [Architecture decisions](./architecture/decisions/) — ADR-0001 … ADR-0004
- Service docs:
  - [user_service](./services/user-service/README.md)
  - [ai_service](./services/ai-service/README.md)
  - [notification_service](./services/notification-service/README.md)
- [Local development guide](./guides/local-development.md) — `docker compose up` and ports
- [Testing guide](./guides/testing.md)
- [Kong gateway](./infrastructure/kong/README.md) — routing, auth, plugins
- [Incident response](./runbooks/incident-response.md)
- [Deployment rollback](./runbooks/deployment-rollback.md)
- [Changelog](./changelog/CHANGELOG.md)