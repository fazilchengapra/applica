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

### Changed

- `notification_service` delivery path corrected to direct HTTP dispatch →
  BullMQ (the docs previously described an unimplemented SNS/SQS/Lambda flow).

### Fixed

- Documentation drift: root README and service readmes now match the real
  docker-compose/Kong architecture instead of the planned AWS/EKS stack.

## [Earlier revisions]

- `user_service`: cookie-based JWT auth (email/phone/Google), verification
  tokens, profiles, in-app notifications, Celery task monitoring.
- `ai_service`: master CV upload/parse/embed, Adzuna job ingestion, pgvector
  RAG matching with LLM rerank.
- `notification_service`: Gmail SMTP email + Twilio OTP dispatch.

> Note: the repository predates this changelog. Historical entries are high
> level; backfill from `git log` as needed by feature area.