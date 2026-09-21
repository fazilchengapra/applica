# Local Development

## Running the whole system locally (recommended)

Everything runs through the monorepo `docker-compose.yml`. From the repo root:

```bash
docker compose up --build          # or `docker compose up -d --build` to detach
```

This starts: `db`, `ai_postgres`, `notification_postgres`, `redis`,
`user-service`, `celery`, `flower`, `ai-service`, `ai-celery`, `ai-celery-beat`,
`ai-flower`, `notification_service`, `notification-worker`, and `kong`.

### Ports

| Service | Host port | Notes |
|---|---|---|
| Kong proxy (all public APIs) | `8000` | route to every backend |
| Kong admin | `8001` | dev only — don't expose in prod |
| PostgreSQL (user_service) | `5432` | db `applica_db` |
| PostgreSQL + pgvector (ai_service) | `5433` | db `ai_service_db` |
| PostgreSQL (notification) | `5434` | db `not_service_db` |
| Redis | `6379` | shared broker/cache |
| Flower (user celery) | `5555` | |
| Flower (ai celery) | `5556` | |

Backend services are **not** mapped to host ports individually — reach them
through Kong at `http://localhost:8000`.

### First-time setup

1. Copy `.env.example` → `.env` for each of `user_service/`, `ai_service/`,
   `notification_service/`, `kong/` and fill in real values (Twilio, Gmail,
   Google, OpenRouter, Voyage, Adzuna, SerpApi, AWS).
2. Kong needs `kong/.env` with `KONG_JWT_SECRET` (must equal the Django
   `SECRET_KEY`) and `GATEWAY_INTERNAL_SECRET`.
3. Apply ai_service migrations once:
   ```bash
   docker compose exec ai-service python -m alembic upgrade head
   ```
4. Verify:
   ```bash
   curl -s http://localhost:8000/health            # notification service
   curl -s http://localhost:8000/api/health        # kong
   ```

## Running services individually (without Docker)

Each service documents its own local setup:

- [user_service](../services/user-service/setup.md) — Django + Postgres + Redis,
  run `manage.py runserver`, Celery worker, runs `pytest`
- [ai_service](../services/ai-service/setup.md) — FastAPI + pgvector,
  run `uvicorn`, Celery worker + beat, Alembic migrations
- [notification_service](../services/notification-service/setup.md) —
  Express + TS, run `npm run dev` and `npm run start:worker`

## Common workflows

### Watch a Celery task / queue depth

- User service tasks: Flower http://localhost:5555
- AI service tasks: Flower http://localhost:5556
- BullMQ jobs: Redis (`redis-cli`), e.g. `LLEN bull:email-dispatch:wait`

### Tail logs for one service

```bash
docker compose logs -f ai-service
docker compose logs -f notification-worker
```

### Rebuild after dependency changes

```bash
docker compose up --build user-service ai-service notification_service kong
```

### Reset a queue (dev)

```bash
docker compose restart ai-celery ai-celery-beat notification-worker
```

## Troubleshooting

- `Kong` fails to start → check `kong/.env` exists; ports 8000/8001 free.
- 401 on protected routes → `access_token` cookie missing/expired; login again.
- 403 from ai_service → `X-Gateway-Secret` mismatch (`GATEWAY_INTERNAL_SECRET`
  must match what Kong injects).
- DB connection refused inside a container → the DB container must be healthy
  (`docker compose ps`); `entrypoint.sh` waits on `pg_isready`.