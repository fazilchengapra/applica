# ai_service

FastAPI + LangGraph service. Owns all AI/generative work: master CV parsing
and versioning, job ingestion, pgvector-based job matching, CV tailoring
agents, and LaTeX PDF rendering.

## What it does

- **Master CV** — upload/update a PDF, version it, parse with PyMuPDF + an LLM
  (OpenRouter), embed with Voyage AI (1024 dims), extract skills, store in S3.
- **Jobs** — ingest jobs from Adzuna into `raw_jobs` → `jobs`, structure,
  chunk, and embed descriptions for retrieval.
- **Matching** — RAG pipeline: vector retrieval (pgvector `<=>`), lexical
  scoring, reciprocal-rank fusion, LLM rerank → persisted `JobMatch` rows.
- **Tailoring** — LangGraph pipeline of four agents (evidence matcher,
  strategist, writer, critic) that produce a `StructuredCVDraft` + `TailoredCV`,
  then render to PDF via Jinja2 → LaTeX (pdflatex) → S3.
- **Companies** — normalize company names and verify via SerpApi evidence +
  LLM judgement.

## API (mounted at `/api/ai/v1`)

Routers registered in [`app/api/v1/router.py`](../../../ai_service/app/api/v1/router.py).
All requests must carry `X-Gateway-Secret` (verified by `GatewayAuthMiddleware`);
user-scoped endpoints additionally read `X-User-Id` (injected by Kong).

| Router | Prefix | Auth | Purpose |
|---|---|---|---|
| `master_cv.py` | `/master-cv` | `X-User-Id` | Upload/update current CV, stats, list versions, parsed CV, skills |
| `jobs.py` | `/jobs` | `X-User-Id` | Trigger job fetch per source |
| `companies.py` | `/companies/admin` | `X-Admin-Authorized` | Trigger company collect/verify |
| `matching_jobs.py` | `/job-matches` | `X-User-Id` | List/get/update matches, refresh |
| `cv_template.py` | `/admin/cv-templates` | `X-Admin-Authorized` | Admin LaTeX template CRUD |
| `cv_template_public.py` | `/cv-templates` | — | Public active template list/get |
| `admin_master_cv.py` | `/admin/users` | `X-Admin-Authorized` | Admin: user master-CV details |
| `admin_jobs.py` | `/admin/jobs` | `X-Admin-Authorized` | Admin: queue external job fetches |
| `tailoring_cv.py` | `/tailored-cvs` | `X-User-Id` | List tailored CVs (filter/paginate), get one (ownership-enforced), trigger tailoring (idempotent), trigger render |
| `dashboard.py` | `/dashboard`, `/dashboard/stats` | `X-User-Id` | `/dashboard`: single aggregate — CV state/versions/stats/profile, match counts + top cards, tailored-CV counts + cards, cross-source activity feed. `/dashboard/stats`: flat headline counters only |
| `home.py` | `/home` | `X-User-Id` | BFF aggregate for the home screen: account + profile + roles + linked accounts (from user_service) + unread count (from notification_service) composed with the CV onboarding step (local) |

### Dashboard endpoint

`GET /api/ai/v1/dashboard` returns every section of the dashboard in one round
trip set. It is always `200`: an account with no CV, matches or tailored CVs
gets a fully-shaped response of zeros and empty lists, so the client never
null-checks a section or handles a 404.

| Section | Notes |
|---|---|
| `master_cv.state` | `none` when the user has no master CV, else the current version's status with `completed` renamed to `ready` (`ready` is a presentation alias; no such value is stored) |
| `master_cv.current` / `versions` | `is_current` version in full, plus the 5 most recent versions by version number |
| `master_cv.stats` | Delegates to the existing `get_cv_status_counts`, so it agrees with `GET /master-cv/stats` |
| `master_cv.profile` | Summary and section counts from the current version's `parsed_data`; `skills` come from the `cv_skills` join. Zeroed until the version is `ready` |
| `matches.counts` | Per-status buckets plus an unfiltered total, from one `GROUP BY` |
| `matches.top` | 10 highest `final_score` matches at or above `min_score` (0.5) |
| `tailored_cvs.counts` | `approved`/`failed` partition content status (`approved + failed == total`); `rendering`/`rendered` partition render status, so the two axes overlap and do not sum to `total` |
| `activity` | Newest-first merge of tailoring runs, PDF renders and master-CV versions, up to 20 |

Activity items are timestamped by `updated_at`, not `created_at`, so a long
running job does not masquerade as recent work. Render events reuse their
tailoring run's `updated_at` because `tailored_cvs` has no `updated_at` column.

`matches.top` currently inherits a scoring-scale inconsistency: `job_matches.final_score`
is documented as 0–1 (`MatchEvaluation.relevance_score`) and validated as such by
`GET /job-matches?min_score`, but the LLM writes values on a 0–100 scale, so the
0.5 dashboard threshold does not exclude anything and scores render as e.g.
`75.0`. Fixing this properly means constraining the evaluation prompt and
backfilling the column, which is tracked separately.

### Dashboard stats endpoint

`GET /api/ai/v1/dashboard/stats` is the cheap sibling of `/dashboard`: three
aggregates, no cards and no activity feed, so a client can poll the stat tiles
without re-fetching the whole aggregate. Always `200`, and zeroed rather than
null — an account with no matches gets `average_final_score` of `0.0` (SQL
`AVG` over no rows is `NULL`, which the repository converts).

| Field | Notes |
|---|---|
| `match_status_breakdown` | Five pipeline buckets plus `total`, from one conditional aggregate |
| `average_final_score` | `AVG(final_score)` over all of the user's matches, rounded to 1dp. Carries the same 0–1 vs 0–100 scale inconsistency as `matches.top`, so it can exceed 1 |
| `top_n` | Echo of the requested page size (default 10, `1..100`). Sizes no query here — it tells the client what to pass when it fetches the cards from `/dashboard` |
| `tailored_cvs_completed` | `render_status = completed`, i.e. the PDF finished |
| `tailored_cvs_in_progress` | `render_status` `pending` or `processing`. Reuses the `get_tailored_cv_counts` aggregate rather than adding a third variant of that query |

The buckets are a **rollup of `MatchStatus`, not the raw enum.** The coarse
pre-pipeline statuses fold into the bucket that supersedes them:

| Bucket | Stored statuses |
|---|---|
| `new` | `NEW`, `VIEWED` |
| `shortlisted` | `SAVED`, `SHORTLISTED` |
| `applied` | `APPLIED` |
| `interviewing` | `INTERVIEWING` |
| `rejected` | `DISMISSED`, `REJECTED` |

Every `MatchStatus` member appears in exactly one bucket, so the five counts
always sum to `total` — no row is double-counted or dropped. The map lives in
[`repository.py`](../../../ai_service/app/modules/dashboard/repository.py) as
`_MATCH_PIPELINE_BUCKETS` and holds enum *members*, not strings: the column is an
`SAEnum` keyed on the member **name**, so the stored labels are uppercase
(`NEW`, `SHORTLISTED`) while the values are lowercase. `test_pipeline_buckets_partition_match_status`
fails if a new enum member is added without a bucket.

`SHORTLISTED`, `INTERVIEWING` and `REJECTED` were added to the enum by migration
`c3d7e91a4b28` (`ALTER TYPE ... ADD VALUE`, so the `downgrade()` is a no-op —
Postgres cannot safely drop a label that rows hold). Adding them automatically
widens `PATCH /job-matches/{id}/status` and `GET /job-matches?status=`, since both
validate against the enum. No backfill: pre-existing rows keep their status and
are counted through the fold above.

### Home endpoint

`GET /api/ai/v1/home` is a BFF aggregate: one call the client can make to render
the home screen. It composes two sources:

- **user_service** (`GET /internal/v1/users/home/{user_id}/`, fetched through
  Kong with `X-Internal-Secret`) supplies `user` (including `roles` and
  `last_login`), `profile`, `linked_accounts` and four
  of the five onboarding steps. That endpoint lives behind the gateway's
  `internal-secret-auth` plugin and re-verifies the shared secret itself.
- **ai_service** (same database) supplies `upload_cv`, because the master CV is
  not visible to user_service.

`onboarding.percent` is `round(completed / 5 * 100)`, computed here so the ring
and the step list can never disagree. Steps render in a fixed order with labels:
`verify_email`, `verify_phone`, `add_photo`, `complete_profile`, `upload_cv`.

Unlike `/dashboard`, this endpoint does **not** degrade to a zeroed payload when
an upstream is down: the account sections are the point of the endpoint, so a
user_service failure is surfaced as `504` (unreachable/timeout) or `502` (any
other upstream error) rather than a silently empty home page.

### Master CV read endpoints

| Endpoint | Returns | Notes |
|---|---|---|
| `GET /master-cv/parsed` | `StructuredCV` | `parsed_data` of the `is_current` version. `404` when the user has no current version, `409` while it is not `completed` |
| `GET /master-cv/skills` | `[{name, normalized_name, skill_type}]` | `cv_skills ⋈ skills` for the `is_current` version. Same `404`/`409` rules |

Both resolve the current version through `get_current_cv_version`
([`cv_repository.py`](../../../ai_service/app/modules/master_cv/repository/cv_repository.py))
and reject anything not yet `completed`, so clients can poll these endpoints
after an upload instead of guessing from `/master-cv/stats`.

## Data model (PostgreSQL 16 + pgvector)

Tables live under `app/modules/*/models/` (async SQLAlchemy), migrated by
Alembic (35 revisions, head `c3d7e91a4b28`):

- **Master CV:** `master_cvs`, `master_cv_versions` (one current version per CV,
  partial unique index), `cv_skills`
- **Jobs:** `raw_jobs`, `companies`, `jobs`, `skills`, `job_skills`,
  `job_chunks` (has `embedding Vector(1024)`)
- **Matching:** `job_matches` (user_id + job_id unique, `final_score`)
- **Templates:** `cv_templates` (LaTeX source, dedup via `tex_hash`)
- **Tailoring:** `tailoring_runs`, `evidence_matrices` + `evidence_items`,
  `strategy_briefs`, `structured_cv_drafts`, `tailored_cvs`

## Background jobs (Celery)

Celery app [`app/core/celery_app.py`](../../../ai_service/app/core/celery_app.py),
default queue `ai_service_queue`, broker/backend = Redis (compose: db 1 / db 2).

| Task | Trigger |
|---|---|
| `master_cv.process_cv` | CV upload/update |
| `fetch_jobs_task` | `POST /jobs/fetch/{source}` |
| `fetch_promotion_batch_task` | internal promotion flow |
| `match_user_task` | `POST /job-matches/refresh` |
| `daily_job_matching_task` | Celery beat **09:30 UTC daily** |
| `companies.collect_pending` / `verify_company_task` | admin triggers |
| `cv_templates.process_cv_template` | admin template create |
| `cv_render.render_tailored_cv` | `POST /tailored-cvs/{id}/render` |
| `evidence_match_task` → `strategize_task` → `write_task` → `critique_task` | tailoring pipeline chain (with critic-verdict retry loop bounded by `MAX_WRITER_RETRIES`) |

## Tech stack

- FastAPI 0.140, uvicorn, SQLAlchemy 2 async + asyncpg, Alembic
- LangChain 1.x, LangGraph 1.x, pgvector
- OpenRouter (LLM via OpenAI-compatible interface), Voyage AI embeddings,
  LangSmith (optional tracing)
- PyMuPDF (CV text), Jinja2 + TeX Live (PDF render)
- boto3 (S3 + SNS), Adzuna (jobs), SerpApi (company verification)
- Celery + Flower, Redis

## Docs in this service

- [Setup](./setup.md) — run it locally / via docker
- [CV Processing](./CV_PROCESSING.md)
- [Tailoring agents — workflow architecture](./TAILORING_AGENTS.md)

## Related

- [Service map](../../architecture/service-map.md)
- [AH DEC: master CV versioning](../../architecture/decisions/0001-master-cv-versioning.md)
- [AH DEC: CV chunking & embeddings](../../architecture/decisions/0002-cv-chunking-and-embeddings.md)