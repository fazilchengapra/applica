# Service Map

A living index of every service, its Django apps / modules, and who owns it.

## user_service (Django + DRF)

Root URLs: [`app/config/urls.py`](../../user_service/app/config/urls.py). All
API routes are under `/api/v1/`.

| App | Purpose | Key files |
|---|---|---|
| `users` | Custom `User` model (email login-id), registration, `/me`, admin user list/overview/toggle | `app/apps/users/` |
| `authentication` | Email/password login, phone OTP login, Google OAuth, verification tokens, password flows, JWT refresh/logout, admin auth overview | `app/apps/authentication/` |
| `profiles` | 1:1 profile data (names, DOB, location, bio, gender) | `app/apps/profiles/` |
| `notifications` | In-app notification model, WebSocket push, SNS publisher, internal dispatch endpoint | `app/apps/notifications/` |
| `task_monitoring` | Celery task execution logging via signals (`TaskExecution`) | `app/apps/task_monitoring/` |
| `common` | WebSocket `JWTAuthMiddleware` | `app/apps/common/` |

## ai_service (FastAPI + LangGraph)

Routers registered in [`app/api/v1/router.py`](../../ai_service/app/api/v1/router.py)
under the `/api/ai/v1` prefix. Each router maps to a domain module.

| Module | Purpose | Routers / key files |
|---|---|---|
| `master_cv` | CV upload/update, versioning, parsing, embeddings, skills, stats | `api/v1/master_cv.py`, `modules/master_cv/` |
| `jobs` | Adzuna job ingestion, structuring, chunking, embedding | `api/v1/jobs.py`, `modules/jobs/` |
| `companies` | Company normalization + SerpApi verification | `api/v1/companies.py`, `modules/companies/` |
| `matching` | pgvector RAG retrieval, RRF fusion, LLM rerank, persistence | `api/v1/matching_jobs.py`, `modules/matching/` |
| `cv_template` | LaTeX CV templates (admin CRUD + public list) | `api/v1/cv_template.py`, `api/v1/cv_template_public.py`, `modules/cv_template/` |
| `tailoring` | LangGraph evidence matcher → strategist → writer → critic pipeline | `api/v1/tailoring_cv.py`, `api/v1/admin_master_cv.py`, `modules/tailoring/` |
| `cv_render` | Tailored CV → Jinja2 LaTeX → pdf (pdflatex) → S3 | `modules/cv_render/` |
| `notifications` | SNS + notification_service publisher | `modules/notifications/` |

## notification_service (Express 5 + TypeScript)

App composition in `src/`. API under `/api/v1/notifications`.

| Module | Purpose | Key files |
|---|---|---|
| `notifications` | Event dispatch, Zod schemas, email/phone templates, service (BullMQ enqueue) | `src/modules/notifications/` |
| `realtime` | WebSocket server (`ws`), Redis pub/sub, user→socket registry, CV-status events | `src/modules/realtime/` |
| `queues` / `workers` | BullMQ queue definitions and email/OTP workers | `src/queues/`, `src/workers/` |
| `providers` | Gmail SMTP (Nodemailer), Twilio phone | `src/providers/` |
| `middleware` | `requireInternalService` (X-Internal-Service header) | `src/middleware/` |

## kong (API Gateway)

| Area | Purpose | Key files |
|---|---|---|
| Declarative config | Base template: consumer, global CORS + correlation-id plugins | `kong/declarative/kong.yml.template` (`../kong/declarative/`) |
| Services | One fragment per backend: `user-service`, `ai-service`, `notification-service` | `kong/services/*.yml` |
| Plugins | `header_injector`, `internal-secret-auth`, `role-auth` | `kong/plugins/*/` |
| Startup | Compose fragments + substitute secrets → `/tmp/kong.yml` | `kong/start-kong.sh` |

## Inter-service dependencies

| Caller | Callee | Mechanism | Hard/Soft |
|---|---|---|---|
| `user_service` | `notification_service` | HTTP `POST /api/v1/notifications/internal/dispatch` via Kong (header `X-Internal-Secret`) | Hard (fire-and-forget, failures logged) |
| `ai_service` | `notification_service` | HTTP dispatch via Kong + AWS SNS (`cv.*` events) | Soft (event-driven) |
| `notification_service` | Redis | BullMQ queues + realtime pub/sub | Hard at runtime |
| `ai_service` | S3 | CV PDFs, templates, rendered PDFs | Hard during pipelines |
| `ai_service` | OpenRouter / Voyage / Adzuna / SerpApi | External APIs | Hard during pipelines |

## Related docs

- [System overview](./system-overview.md)
- [Architecture decisions](./decisions/)
- [Mock interview system (design, planned)](./mock-interview.md) — planned
  `ai_service.interviews` module, `interview-agent` + `livekit` compose services