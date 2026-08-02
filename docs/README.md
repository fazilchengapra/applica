# Project Documentation

This is the single source of truth for how the system is built, deployed, and operated.

## How this is organized

| Folder | What lives here |
|---|---|
| `architecture/` | System-wide design: how services talk to each other, and why key decisions were made (ADRs) |
| `services/` | One folder per microservice. Each service's docs are self-contained and owned by whoever owns that service |
| `infrastructure/` | Terraform, EKS, Kong gateway, CI/CD — anything cross-cutting to deployment |
| `api-reference/` | Generated OpenAPI/Swagger specs — not hand-written, produced by CI |
| `runbooks/` | "Something is on fire, what do I do" — incident response, rollback, on-call |
| `guides/` | Onboarding, local dev setup, coding standards, testing conventions |
| `changelog/` | Human-readable release history |

## Rule of thumb

- If it's **specific to one service**, it goes in `services/<service-name>/`.
- If it explains **why a service exists or how services interact**, it goes in `architecture/`.
- If it's about **running/deploying anything**, it goes in `infrastructure/` or `runbooks/`.
- If it's **generated from code** (OpenAPI schema, docstrings), it goes in `api-reference/` and is never edited by hand.

## Quick links

- [System overview](./architecture/system-overview.md)
- [User service docs](./services/user-service/README.md)
- [AI service docs](./services/ai-service/README.md)
- [Local development guide](./guides/local-development.md)
