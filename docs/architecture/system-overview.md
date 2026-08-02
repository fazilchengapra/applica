# System Overview

## Services

| Service | Responsibility | Stack |
|---|---|---|
| `user-service` | Auth, user accounts, profiles, task monitoring, notifications | Django + DRF, PostgreSQL |
| `ai-service` | Job automation / AI processing | FastAPI, LangGraph |

## High-level flow

Client → Kong API Gateway → `user-service` / `ai-service`

Describe here:
- What Kong routes to what (path prefixes, auth checks at the gateway vs. per-service)
- Which service owns which data (avoid two services writing to the same tables)
- Sync vs async communication between services (REST calls? queue? webhook?)

## Diagram

Put an actual diagram here (draw.io, Mermaid, or exported PNG) showing:
Client → Kong → [user-service, ai-service] → PostgreSQL / other stores

## Related docs

- [Service map](./service-map.md)
- [Architecture decisions](./decisions/)
- [Kong gateway config](../infrastructure/kong-gateway.md)
