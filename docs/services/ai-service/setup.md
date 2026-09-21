# Local Setup — ai_service

## Prerequisites

- Python 3.12
- PostgreSQL 16 **with pgvector** (the compose image `pgvector/pgvector:pg16`)
- Redis (Celery broker/backend)
- Environment variables — copy `.env.example` to `.env` and fill in values

> External API keys required for full functionality: `OPENROUTER_API_KEY`,
> `VOYAGE_API_KEY`, `ADZUNA_APP_ID`/`ADZUNA_APP_KEY`, `SERPAPI_KEY`, and AWS
> credentials for S3.

## Steps (standalone, without Docker)

```bash
cd ai_service
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in secrets

# database must already exist (e.g. ai_service_db) and have pgvector installed
alembic upgrade head

uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

In separate terminals, run the worker and beat (needed for pipelines):

```bash
celery -A app.core.celery_app worker -Q ai_service_queue -l info
celery -A app.core.celery_app beat -l info
```

## Environment variables

From [`app/core/config.py`](../../../ai_service/app/core/config.py):

| Variable | Purpose | Example |
|---|---|---|
| `DATABASE_URL` | asyncpg DSN | `postgresql+asyncpg://ai_user:ai_pass@localhost:5432/ai_service_db` |
| `GATEWAY_INTERNAL_SECRET` | Expected `X-Gateway-Secret` header (set by Kong) | |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_REGION` | S3 | |
| `S3_BUCKET_NAME` / `S3_ENDPOINT_URL` | S3 bucket / endpoint (localstack/minio) | |
| `OPENROUTER_MODEL` / `OPENROUTER_API_KEY` / `OPENROUTER_BASE_URL` | LLM | `gpt-4o-mini` |
| `WRITER_MODEL` | CV writer LLM override | |
| `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` | Redis | `redis://localhost:6379/1` / `/2` |
| `VOYAGE_API_KEY` | Embeddings (voyage-3.5, 1024 dims) | |
| `ADZUNA_APP_ID` / `ADZUNA_APP_KEY` / `ADZUNA_BASE_URL` / `ADZUNA_COUNTRY` | Job ingestion | |
| `SERPAPI_KEY` | Company verification search | |
| `VERIFICATION_APPROVE_THRESHOLD` / `CRITIC_QUALITY_THRESHOLD` / `MAX_WRITER_RETRIES` | Pipeline gates | |
| `SNS_NOTIFICATIONS_TOPIC_ARN` / `NOTIFICATION_SERVICE_URL` | Event publishing | |
| `LANGSMITH_TRACING` / `LANGSMITH_API_KEY` / `LANGSMITH_PROJECT` | Optional tracing | |

## Running via Docker (recommended)

```bash
docker compose up --build ai_postgres ai-service ai-celery ai-celery-beat ai-flower
```

`entrypoint.sh` waits for Postgres with `pg_isready`. The service listens on
:8001 inside the compose network; Kong routes `/api/ai/v1` to it. Migrations
are **not** run automatically — run `alembic upgrade head` inside the
container once:

```bash
docker compose exec ai-service python -m alembic upgrade head
```

## Tests

There is **no automated test suite** for `ai_service` yet. See
[testing guide](../../guides/testing.md).