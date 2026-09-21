# Applica — AI-Powered Job Application Automation Platform

Monorepo containing the **Applica backend**: an AI platform that automates job
applications — resume tailoring, cover-letter generation, job matching, and AI
interview practice — behind a single API gateway.

> Full documentation lives in [`docs/`](./docs/README.md). This README is the
> quick orientation.

---

## Repository layout

| Path | What it is |
|---|---|
| [`user_service/`](./user_service/) | Django 6 + DRF service: accounts, auth (JWT cookies, email/phone/Google), profiles, in-app notifications, Celery task monitoring. PostgreSQL. |
| [`ai_service/`](./ai_service/) | FastAPI + LangGraph service: master CV parsing & versioning, job ingestion, pgvector RAG job matching, CV tailoring agents, LaTeX PDF rendering. PostgreSQL + pgvector. |
| [`notification_service/`](./notification_service/) | Node.js (Express 5 + TypeScript) service: email (Gmail SMTP via Nodemailer), SMS OTP (Twilio), realtime WebSocket push (Redis pub/sub). BullMQ workers. |
| [`kong/`](./kong/) | Kong Gateway OSS (DB-less) config: routing, JWT verification, rate limiting, and three custom Lua plugins (`header_injector`, `internal-secret-auth`, `role-auth`). |
| [`docker-compose.yml`](./docker-compose.yml) | Single-command local stack: all services + 3 Postgres instances + Redis + Kong + Celery workers/beat + Flower. |
| [`docs/`](./docs/README.md) | Architecture, service, infrastructure, guide and runbook documentation. |

## Architecture at a glance

```
                 ┌─────────────────────────┐
   Web / Mobile  │  Kong API Gateway :8000 │
      Client ───▶│  JWT • rate-limit       │
                 │  custom Lua plugins     │
                 └──────┬─────────┬────────┘
                        │         │
        ┌───────────────▼──┐   ┌──▼──────────────────┐
        │ user_service     │   │ ai_service          │
        │ Django + DRF     │   │ FastAPI + LangGraph │
        │ PostgreSQL :5432 │   │ pgvector   :5433    │
        └───────┬──────────┘   └───┬─────────────────┘
                │                  │
                │      ┌───────────▼─────────────┐
                └─────▶│ notification_service    │
                       │ email + SMS + WebSocket │
                       └─────────────────────────┘
```

- **Auth:** services issue/accept JWT cookies signed with `SECRET_KEY`; Kong
  shares that secret to validate at the edge, then injects `X-User-Id` /
  `X-Gateway-Secret` / `X-Admin-Authorized` headers. Services trust the gateway
  secret as proof the request passed through Kong.
- **Data:** each service owns its own PostgreSQL database (no cross-service
  FKs; users are referenced by plain ID). `ai_service` uses a
  `pgvector/pgvector:pg16` image for vector search.
- **Async:** Celery (Python services) and BullMQ (notification service) on a
  shared Redis. `ai_service` runs a daily 09:30 UTC job-matching beat.
- **Inter-service calls:** `ai_service` → SNS (AWS) and HTTP → `notification_service`
  for events; both services call the notification dispatch endpoint through Kong.

## Quick start

```bash
# from repo root — builds and starts the whole stack
docker compose up --build

# public APIs
Kong proxy    http://localhost:8000
user service  http://localhost:8000/api/v1/...   (via Kong)
ai service    http://localhost:8000/api/ai/v1/... (via Kong)
Kong admin    http://localhost:8001  (dev only)

# dashboards
Flower (user celery) http://localhost:5555
Flower (ai celery)   http://localhost:5556

# databases (host ports)
user_service       postgres :5432
ai_service+pgvector   postgres :5433
notification_service  postgres :5434
Redis              :6379
```

See [`docs/guides/local-development.md`](./docs/guides/local-development.md)
for full setup, per-service setup pages, and troubleshooting.

## Technology stack

| Layer | Tech |
|---|---|
| Auth / identity | Django, DRF, SimpleJWT (cookie-based), Django Channels (WebSocket), Google OAuth |
| AI / processing | FastAPI, LangChain/LangGraph, SQLAlchemy async, pgvector, OpenRouter (LLM), Voyage AI (embeddings) |
| Notifications | Express 5, TypeScript, Nodemailer/Gmail, Twilio, `ws` + Redis pub/sub, BullMQ |
| Gateway | Kong OSS (DB-less declarative config) + custom Lua plugins |
| Data | PostgreSQL 16, pgvector, Redis 7 |
| Workers | Celery (+ beat), BullMQ |
| Infra | `docker-compose.yml` (local); Terraform/K8s not yet in use |

## Documentation index

- [`docs/README.md`](./docs/README.md) — documentation map
- [`docs/architecture/system-overview.md`](./docs/architecture/system-overview.md) — services, request flows
- [`docs/services/user-service/README.md`](./docs/services/user-service/README.md)
- [`docs/services/ai-service/README.md`](./docs/services/ai-service/README.md)
- [`docs/services/notification-service/README.md`](./docs/services/notification-service/README.md)
- [`docs/infrastructure/kong/README.md`](./docs/infrastructure/kong/README.md) — gateway config