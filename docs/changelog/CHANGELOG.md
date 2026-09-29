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
  `user_service` account payload (user, profile, roles, linked accounts, unread
  notifications) with the locally-computed `upload_cv` onboarding step.
- `user_service` internal account endpoint `GET /internal/v1/users/home/{user_id}/`,
  guarded by the shared secret and exposed through a new `user-service-internal`
  Kong route.
- `ai_service` dashboard aggregate (`GET /api/ai/v1/dashboard`).
- Shared `get_user_roles` helper (`user_service`), replacing the role list that
  was duplicated in email login and Google OAuth.

### Changed

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