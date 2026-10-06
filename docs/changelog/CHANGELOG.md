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
- `ai_service` top-matches table (`GET /api/ai/v1/dashboard/top-matches`): a
  paginated read model for the highest-scoring matches, each row carrying its
  score breakdown (`vector`/`lexical`/`rrf`, `key_matches`, `key_gaps`), the raw
  `match_status`, and `tailored_cv_status` derived from the job's most recent
  tailoring run (`none`/`in_progress`/`completed`/`failed`). Returns a `count` of
  all qualifying matches alongside the page, and supports `limit`/`offset` plus an
  optional floor-only `min_score`. The latest run is read through a scalar
  subquery rather than a join, because `tailoring_runs` is unique per
  `(user_id, job_id, cv_version_id)` and a join would duplicate a match once a
  user re-tailors against a newer master CV.
- `ai_service` tailoring-runs table (`GET /api/ai/v1/dashboard/tailoring-runs`): a
  paginated, newest-first list of the user's tailoring runs with `job_title`,
  `company_name`, `status`, `current_stage`, `created_at`/`updated_at`,
  `error_message` and `cv_id`, sharing the `{count, results}` envelope of
  `/dashboard/top-matches`. Run-centric rather than CV-centric, so runs that are
  still queued — or that failed before the draft — are listed with `cv_id` null;
  `tailored_cvs` is joined with a `LEFT OUTER JOIN` for exactly that reason, and
  `GET /tailored-cvs` cannot show them because it is keyed off `tailored_cvs`.
  `status` collapses stored `pending`/`processing` to `in_progress`, reusing the
  `TailoredCVProgress` enum so both dashboard tables share one vocabulary, and
  `current_stage` returns display labels (`evidence_matcher`, `strategist`,
  `writer`, `critic`) rather than the stored `evidence_match`/`strategy`/`write`.
- `ai_service` dashboard insights (`GET /api/ai/v1/dashboard/insights`):
  `missing_skills` (skills the user's matched jobs require that their current CV
  does not list, each with the number of jobs wanting it, most wanted first) and
  `score_trend` (weekly mean `job_matches.final_score` over a `weeks`-bounded
  window, Monday-aligned, labelled `'Mon D'`). Gaps require a current *completed*
  CV to diff against — a version still parsing has an incomplete `cv_skills` list
  and would report every skill the user has as missing — so the section is empty
  without one, while the trend still reports. Weeks with no matches are omitted
  rather than emitted as nulls. Backed by migration `b8e4f10c6d92`, which adds a
  nullable `skills.category`; it is **null for every row** because no skill
  taxonomy exists in the codebase to backfill it from, and keyword-matching names
  into invented categories would put unverifiable labels in user-facing output.
- Shared `get_user_roles` helper (`user_service`), replacing the role list that
  was duplicated in email login and Google OAuth.
- `notification_service` notification lifecycle:
  - **Idempotent creation.** `POST /internal/notifications` accepts an optional
    `dedupeKey`; `UNIQUE (user_id, dedupe_key)` makes a replay return the
    existing row with `200` instead of inserting a second one with `201`. Keys
    are derived from the domain object that caused the event (`"{event}:{token_id}"`,
    `"{event}:{user_id}"` for welcome), so a replay of one attempt collapses while
    a legitimate repeat still delivers. Nullable, since btree treats NULLs as
    distinct. Migrations `20261003090000`, `20261003100000`, `20261003110000`.
  - **Archive.** `POST /api/v1/notify/{id}/archive/` and `?archived=true` on the
    list. Archive is separate from `read_at` on purpose — "seen" and "no longer in
    my inbox" are different intents — so dismissing does not overwrite when, and
    archived rows leave both the default inbox and the unread count. `read-all`
    skips them.
  - **Retention.** A repeatable BullMQ scheduler (`notification-retention-sweep`,
    default `17 3 * * *`) deletes rows older than
    `NOTIFICATION_RETENTION_DAYS` (default 30) that are read *or* archived, in
    batches of 500 ids so no single statement holds locks for long. Unread,
    unarchived rows are kept indefinitely.
  - **Account deletion.** `DELETE /internal/users/{user_id}/notifications`
    hard-deletes a user's rows, batched and idempotent. Needed because
    `notifications` has no FK to a user table — separate database, nothing
    cascades. `user_service` now schedules `purge_notifications_task` on
    deactivation.
  - **Realtime fan-out.** New `notification:created` Redis channel, so an inbox
    row created on one replica reaches clients attached to any other; before
    this, a client only received pushes from the replica that served its write.
    A deduplicated insert does not re-publish, so a retry cannot double-push.
    The vestigial pub/sub client duplication was removed at the same time.
  - List indexes rebuilt around the actual queries (`idx_user_archived_created`,
    `idx_user_read_archived_created`, plus `idx_read_created` /
    `idx_archived_created` for retention), replacing the single
    `idx_user_read_created`.
  - 31 new Vitest lifecycle cases (74 total) covering dedupe, archive,
    retention, purge, and Redis fan-out.

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
- `notification_service` image now runs `prisma generate` before compiling.
  `src/generated/prisma` is gitignored, so a clean checkout had no Prisma client
  and `tsc` failed with `TS2307` on `generated/prisma/client`; builds only worked
  when a stale generated client happened to be present in the build context.
- `purge_notifications_task` logged a failed purge and returned, so a
  `notification_service` outage left a deactivated account's rows behind with no
  retry. It now asks for a retry like `revoke_all_tokens_task`, and still gives up
  quietly once the three attempts are spent — the account is already
  deactivated, so a cleanup problem must not surface as a failed deactivation.

## [Earlier revisions]

- `user_service`: cookie-based JWT auth (email/phone/Google), verification
  tokens, profiles, in-app notifications, Celery task monitoring.
- `ai_service`: master CV upload/parse/embed, Adzuna job ingestion, pgvector
  RAG matching with LLM rerank.
- `notification_service`: Gmail SMTP email + Twilio OTP dispatch.

> Note: the repository predates this changelog. Historical entries are high
> level; backfill from `git log` as needed by feature area.