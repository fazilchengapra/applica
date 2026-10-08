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
| `dashboard.py` | `/dashboard`, `/dashboard/stats`, `/dashboard/top-matches`, `/dashboard/tailoring-runs`, `/dashboard/insights` | `X-User-Id` | `/dashboard`: single aggregate — CV state/versions/stats/profile, match counts + top cards, tailored-CV counts + cards, cross-source activity feed. `/dashboard/stats`: flat headline counters only. `/dashboard/top-matches`: paginated top-matches table with score breakdown + tailoring progress. `/dashboard/tailoring-runs`: paginated tailoring-runs table with stage labels and `cv_id`. `/dashboard/insights`: skill gaps + weekly score trend |
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

### Top matches endpoint

`GET /api/ai/v1/dashboard/top-matches` backs the "Top Matches" table: one page of
the user's highest-scoring matches, each row carrying its score breakdown and
tailoring progress. Always `200`; an account with no matches gets
`{"count": 0, "results": []}`.

| Param | Default | Range | Notes |
|---|---|---|---|
| `limit` | `20` | `1..100` | Page size |
| `offset` | `0` | `>= 0` | Rows to skip |
| `min_score` | none | `>= 0`, **no upper bound** | Floor on `final_score` |

| Field | Notes |
|---|---|
| `count` | Total qualifying matches, *not* the page length — so a client can render "1–20 of 137". Counted in a separate `COUNT` over the same filter |
| `results[]` | Each entry has `id`, `job_title`, `company_name`, `match_status`, `final_score`, `vector_score`, `lexical_score`, `rrf_score`, `key_matches`, `key_gaps`, `tailored_cv_status` |
| `company_name` | `companies.display_name`, falling back to `normalized_name` when no display name is set |
| `match_status` | The **raw** `MatchStatus`, serialized lowercase. Unlike `/dashboard/stats` there is no bucket rollup here: the table filters on individual statuses |
| `tailored_cv_status` | Progress of the most recent tailoring run for that job: `none`, `in_progress`, `completed`, `failed` |

Ordering is `final_score DESC, matched_at DESC`. The `matched_at` tie-breaker is
load-bearing: the five seeded matches include three at exactly `3.0`, and paging
over a non-total order can repeat or drop rows at a page boundary.

`min_score` has **no upper bound** on purpose. `final_score` carries the same
0–1 vs 0–100 inconsistency described above, so a `le=1` would hide every real row
while still admitting the 0–1 ones. The bound is therefore only a floor; the
client scales the control to whatever the data looks like.

`tailored_cv_status` reads the latest run per job through a **scalar subquery**
(`ORDER BY created_at DESC, id DESC LIMIT 1`), not a join. This matters:
`tailoring_runs` is unique on `(user_id, job_id, cv_version_id)`, not
`(user_id, job_id)`, so a user re-tailoring after a new master CV legitimately has
several runs for one job. Joining would emit one row per run and inflate both
`count` and the page. `test_top_matches_reads_the_run_through_a_scalar_subquery`
asserts this on the generated SQL, since the response cannot show it.

Mapping is lossy in one direction only: `pending` and `processing` both render as
`in_progress`, because the column shows step count rather than pipeline stage. The
other three pass through, and a job with no run at all is `none`.

### Tailoring runs endpoint

`GET /api/ai/v1/dashboard/tailoring-runs` backs the dashboard's tailoring section:
the user's tailoring runs, newest first. Always `200`; an account that has never
tailored anything gets `{"count": 0, "results": []}`.

| Param | Default | Range |
|---|---|---|
| `limit` | `20` | `1..100` |
| `offset` | `0` | `>= 0` |

Unlike `/dashboard/top-matches` (a top-N widget capped at 3), this is a table, so
it pages normally.

| Field | Notes |
|---|---|
| `count` | Total runs, not the page length |
| `id` | `tailoring_runs.id` (a UUID) |
| `status` | Run outcome: `in_progress` (stored `pending` or `processing`), `completed` or `failed`. Reuses the `TailoredCVProgress` enum so this table and top-matches share one vocabulary |
| `current_stage` | Display **label**: `evidence_matcher`, `strategist`, `writer` or `critic`. Never null |
| `error_message` | Verbatim and untruncated |
| `cv_id` | `tailored_cvs.id`, or null while the run has not produced one |
| `company_name` | `companies.display_name`, falling back to `normalized_name` |

Two deliberate departures from the stored values, both because the stored values
read as implementation identifiers:

- **`current_stage` is a label, not the enum.** `tailoring_runs.stage` holds
  `evidence_match`/`strategy`/`write`; the response returns
  `evidence_matcher`/`strategist`/`writer` so the client needs no mapping table.
  The map is `_STAGE_TO_LABEL` in `dashboard_service.py` and
  `test_stage_labels_cover_every_stage` fails if a stage is added without one.
  `current_stage` is also non-nullable in the response: the column is `NOT NULL`
  with default `evidence_match`, so even a freshly queued run reports the first
  step rather than nothing.
- **`status` collapses the early pipeline.** Stored `pending` and `processing`
  both render as `in_progress`, matching what `GET /dashboard/top-matches` reports
  for the same run.

`cv_id` is why this endpoint is run-centric rather than CV-centric. A run exists
from the moment tailoring is queued, so runs still queued — or failed before the
draft — have no `tailored_cvs` row and **must** appear with `cv_id` null. The
`tailored_cvs` join is therefore a `LEFT OUTER JOIN`; an inner join would drop
exactly the runs a user most wants to see. `GET /tailored-cvs` is keyed off
`tailored_cvs` and cannot show them at all.
`test_tailoring_runs_outer_joins_tailored_cvs` asserts this on the generated SQL,
because the surviving rows look identical either way.

Ordering is `created_at DESC, id DESC`. The `id` tie-breaker matters because
`created_at` defaults to `now()` per statement, so two runs queued in one
transaction share a timestamp and would otherwise be able to repeat or drop
across a page boundary.

### Insights endpoint

`GET /api/ai/v1/dashboard/insights` backs the dashboard's insights section: which
skills the user's applications want that their CV does not list, and whether
their match scores are improving. Always `200`, and both keys are always present
— an account with no CV or no matches gets two empty lists rather than nulls.

| Param | Default | Range | Notes |
|---|---|---|---|
| `weeks` | `8` | `1..52` | How far back `score_trend` reaches |
| `limit` | `10` | `1..50` | Maximum `missing_skills` returned |

| Field | Notes |
|---|---|
| `missing_skills[].skill` | `skills.name` |
| `missing_skills[].count` | How many of the user's **matched** jobs require it, so a high count means the gap is worth closing across many applications |
| `missing_skills[].category` | From `skills.category`. **Always null today** — see below |
| `score_trend[].date` | Week start (Monday), formatted `'%b %-d'` — e.g. `Oct 6`. A label, not an ISO date, to match the chart axis |
| `score_trend[].score` | Mean `job_matches.final_score` for that week. Carries the same 0–1 vs 0–100 scale inconsistency as `matches.top`, so a point may exceed 1 |

`missing_skills` is computed as `job_skills` for the user's *matched* jobs minus
the skills on their current CV — not every ingested job, since the insight is
about the applications they are actually pursuing.

**`category` is null for every skill.** Migration `b8e4f10c6d92` adds a nullable
`skills.category` so the contract is stable, but there is no taxonomy anywhere in
the codebase to backfill it from, and keyword-matching skill names into invented
categories would put unverifiable labels in user-facing output. Backfill it from a
curated source when one exists.

Two behaviours worth knowing:

- **No completed CV means no skill gaps.** The comparison needs a current
  *completed* CV version. A version still parsing has a partially populated
  `cv_skills` table, so every skill the user *does* have would look like a gap.
  `get_current_completed_cv_id` therefore filters on both `is_current` and
  `status = completed`, and the service skips the query entirely when there is
  none. `score_trend` is unaffected and still reports.
- **Weeks with no matches are omitted, not sent as null.** A chart can therefore
  plot every point it receives, but it cannot infer gaps from the spacing — if it
  needs to show that a week was empty, the client must detect the jump.

The trend cutoff is computed in Python as a **naive** UTC datetime and bound
naive-to-naive, because `job_matches.matched_at` is `timestamp without time zone`
— passing a tz-aware value would be cast to `timestamptz` and shift the window
boundary by the session offset.

Ordering for `missing_skills` is `count DESC, name ASC` for a deterministic page.
Note the `name` tie-break resolves under the *database* collation (case-insensitive
in this deployment), so `integration solution` sorts before `Java` — unlike Python's
byte ordering.

The week bucket is a raw `literal_column`, not `func.date_trunc`. `func.date_trunc`
binds its `'week'` argument as a parameter, and Postgres matches GROUP BY against
the select list by comparing expression trees — a parameter there is not the same
expression, so the query fails with *"column must appear in the GROUP BY clause"*.
Inlining the text makes all three occurrences (select/group/order) identical;
`test_score_trend_inlines_the_week_bucket` guards it.

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
- [RAG module](./RAG_MODULE.md) — file-by-file responsibilities
- [RAG ingestion & change-detection workflow](./RAG_WORKFLOW.md) — pipeline, arguments/prompts, change detection, cost reduction

## Related

- [Service map](../../architecture/service-map.md)
- [AH DEC: master CV versioning](../../architecture/decisions/0001-master-cv-versioning.md)
- [AH DEC: CV chunking & embeddings](../../architecture/decisions/0002-cv-chunking-and-embeddings.md)