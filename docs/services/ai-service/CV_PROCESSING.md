# CV Processing Pipeline

Pipeline entry: `POST /api/ai/v1/master-cv/` (upload) or
`PUT /api/ai/v1/master-cv/{cv_id}` (update). Each upload creates a new
`master_cv_versions` row; processing runs as the Celery task `master_cv.process_cv`.

## Upload constraints

- Max file size: 5 MB
- Allowed type: PDF only (magic-byte verified, not just content-type header)
- One master CV per user (`MultipleMasterCVError` if a second is uploaded).
  First upload creates `version = 1`; updates create `version = current + 1`.
- Versioning: partial unique index `one_current_version_per_cv` enforces a
  single `is_current` version per CV. Update flow creates `version = current + 1`
  and marks the old version `is_current = false`.

## Pipeline stages

1. **Download** — PDF pulled from S3 (`s3_key` on `master_cv_versions`).
2. **Text extraction** — PyMuPDF (`fitz`), pages concatenated.
3. **Structured parsing** — LLM via OpenRouter (`ChatOpenAI` on
   `OPENROUTER_BASE_URL`) with `with_structured_output(StructuredCV)`; schema
   covers contact, summary, experience, education, skills, projects.
4. **Embeddings** — Voyage AI `voyage-3.5`, 1024 dims, stored in
   `master_cv_versions.embedding` (pgvector `Vector(1024)`).
5. **Skill extraction** — LLM skill list → `cv_skills` rows
   (`skill_extraction_service`, `app/prompts/skill_extraction_prompt.py`).
6. **Persist** — `raw_text`, `parsed_data` (JSONB), `embedding`,
   `status = completed` (or `failed` with message).
7. **Publish** — SNS events `cv.pending` / `cv.processing` / `cv.completed` /
   `cv.failed`, plus HTTP dispatch to `notification_service`.

## Storage

- `raw_text`: kept indefinitely (source of truth for reprocessing).
- `parsed_data` (JSONB): derived, can be regenerated from `raw_text`.
- `embedding`: derived, regenerated on each new version.
- Rendered/tailored outputs and templates live in S3.

## Note on chunking (see ADR-0002)

The original design (ADR-0002) proposed a `cv_chunks` table so a CV could be
searched at a granular level. **Current implementation stores a single 1024-dim
embedding per `master_cv_versions` row** and, for matching, embeds that CV
vector against per-`job_chunks` embeddings from the jobs pipeline. The granular
chunking ADR remains `Proposed`/not migrated into the DB layer.

## Why not embed raw_text directly

Single-document embeddings are a pragmatic starting point (one vector per CV;
retrieval happens over job chunks). Granular per-section chunking is tracked in
ADR-0002 and would improve semantic recall; it has not been implemented yet.

## Related

- [ADR-0001 master CV versioning](../../architecture/decisions/0001-master-cv-versioning.md)
- [ADR-0002 CV chunking and embeddings](../../architecture/decisions/0002-cv-chunking-and-embeddings.md)