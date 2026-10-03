# Changelog

All notable changes to this project. Format: [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added

- `ai_service` tailoring pipeline: evidence matcher, strategist, writer, critic
  LangGraph agents; `tailoring_runs`, `strategy_briefs`, `structured_cv_drafts`,
  `tailored_cvs` tables; critic-verdict retry loop.
- Tailored CV PDF rendering (Jinja2 → LaTeX → pdflatex → S3).
- `notification_service`: realtime WebSocket push (`ws/notifications`) with
  Redis pub/sub CV-status events; BullMQ email/OTP queues + workers.
- Kong API gateway: JWT verification, Redis-backed rate limiting, custom Lua
  plugins (`header_injector`, `internal-secret-auth`, `role-auth`).
- Master CV versioning and pgvector embedding (ADR-0001, ADR-0002).
- Documentation rewrite in `docs/` reflecting actual implementation.
- Mock interview system design docs + decision record
  (`docs/architecture/mock-interview.md`, `docs/architecture/decisions/0004-mock-interview-livekit.md`).
  **Design only — not yet implemented**: self-hosted LiveKit SFU + free local
  speech stack (faster-whisper, Kokoro-82M), `ai_service.interviews` module,
  `interview-agent` worker, realtime `interview.*` events.
- `ai_service` home aggregate: `GET /api/ai/v1/home` BFF combining the
  `user_service` account payload (user, profile, roles, linked accounts) with the
  locally-computed `upload_cv` onboarding step, and with the unread notification
  count read from `notification_service`.
- `user_service` internal account endpoint `GET /internal/v1/users/home/{user_id}/`,
  guarded by the shared secret and exposed through a new `user-service-internal`
  Kong route.
- `notification_service` in-app inbox: `GET /api/v1/notify/`,
  `GET /api/v1/notify/unread-count/`, `POST /api/v1/notify/{id}/read/`,
  `POST /api/v1/notify/read-all/`, `DELETE /api/v1/notify/{id}/`, plus the
  service-to-service `POST /api/v1/notifications/internal/notifications` and
  `GET /api/v1/notifications/internal/users/{user_id}/unread-count/`. Backed by a
  new Prisma `Notification` model with a `user_id, read_at, created_at DESC`
  composite index; 43 Vitest integration tests run against the real database.
- `ai_service` dashboard aggregate (`GET /api/ai/v1/dashboard`).
- `ai_service` dashboard stat tiles (`GET /api/ai/v1/dashboard/stats`): a flat,
  cheap read model — `match_status_breakdown` (new/shortlisted/applied/
  interviewing/rejected plus a total that the five always sum to),
  `average_final_score`, an echoed `top_n`, and the tailored-CV
  completed/in-progress render counters. Backed by a new `match_status` enum
  migration (`c3d7e91a4b28`) adding `SHORTLISTED`, `INTERVIEWING` and
  `REJECTED`; the pre-existing `VIEWED`/`SAVED`/`DISMISSED` statuses fold into
  the corresponding buckets rather than being backfilled, and are still
  accepted by `PATCH /job-matches/{id}/status` and `GET /job-matches?status=`.
- Shared `get_user_roles` helper (`user_service`), replacing the role list that
  was duplicated in email login and Google OAuth.

### Changed

- **In-app notifications moved from `user_service` to `notification_service`.**
  The `notifications` table, the five read/write endpoints, and the realtime
  fan-out now live in `notification_service`, which has its own Postgres. Rows
  were migrated with microsecond precision; `user_service` is now only a
  producer, calling over HTTP via `create_and_push` (failures are logged, never
  raised, so a notification outage cannot roll back an auth transaction).
  `POST /api/v1/notify/push/`, the Django `Notification` model (table dropped via
  migration `notifications.0003`), the Channels consumer and the ASGI websocket
  route were all removed from `user_service`.
- The unread count in `GET /api/ai/v1/home` is now read from
  `notification_service`; `user_service`'s internal home payload no longer has a
  `notifications` key. An unreachable inbox surfaces as an error rather than a
  silent `0`.
- The browser inbox is mounted on `/api/v1/notify`, deliberately separate from
  the internal `/api/v1/notifications/*` routes, so the user-authenticated Kong
  surface can't be widened by adding an internal path. All internal routes are
  now secret-checked in the service as well as at Kong.
- `notification_service` delivery path corrected to direct HTTP dispatch →
  BullMQ (the docs previously described an unimplemented SNS/SQS/Lambda flow).
- The internal secret is now consistently named `GATEWAY_INTERNAL_SECRET` across
  Kong, `ai_service` and `user_service`.

### Fixed

- Documentation drift: root README and service readmes now match the real
  docker-compose/Kong architecture instead of the planned AWS/EKS stack.
- Kong `role-auth` read roles from a non-existent `x.roles` claim instead of the
  JWT's `roles` claim, so every role-gated route returned `500` and admin access
  was unusable.
- Kong `internal-secret-auth` hardcoded `notification-dispatcher` as the
  forwarded `X-Internal-Service` value; the caller name is now configurable.

## [Earlier revisions]

- `user_service`: cookie-based JWT auth (email/phone/Google), verification
  tokens, profiles, in-app notifications, Celery task monitoring.
- `ai_service`: master CV upload/parse/embed, Adzuna job ingestion, pgvector
  RAG matching with LLM rerank.
- `notification_service`: Gmail SMTP email + Twilio OTP dispatch.

> Note: the repository predates this changelog. Historical entries are high
> level; backfill from `git log` as needed by feature area.