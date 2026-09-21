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
| `master_cv.py` | `/master-cv` | `X-User-Id` | Upload/update current CV, stats |
| `jobs.py` | `/jobs` | — | Trigger job fetch per source |
| `companies.py` | `/companies/admin` | — (TODO admin mw) | Trigger company collect/verify |
| `matching_jobs.py` | `/job-matches` | `X-User-Id` | List/get/update matches, refresh |
| `cv_template.py` | `/admin/cv-templates` | `X-Admin-Authorized` | Admin LaTeX template CRUD |
| `cv_template_public.py` | `/cv-templates` | — | Public active template list/get |
| `admin_master_cv.py` | `/admin/users` | — (TODO admin mw) | Admin: user master-CV details |
| `tailoring_cv.py` | `/tailored-cvs` | `X-User-Id` | Get tailored CV (ownership-enforced), trigger render |

## Data model (PostgreSQL 16 + pgvector)

Tables live under `app/modules/*/models/` (async SQLAlchemy), migrated by
Alembic (31 revisions, head `b8e4f2a6c9d0`):

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

## Related

- [Service map](../../architecture/service-map.md)
- [AH DEC: master CV versioning](../../architecture/decisions/0001-master-cv-versioning.md)
- [AH DEC: CV chunking & embeddings](../../architecture/decisions/0002-cv-chunking-and-embeddings.md)