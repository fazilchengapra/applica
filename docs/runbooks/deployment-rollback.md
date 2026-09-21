# Deployment Rollback

This runbook applies to the **current docker-compose deployment**. There is no
image registry or orchestrator yet, so "rollback" = revert code + rebuild.

## When to roll back vs. fix forward

- **Roll back** if a deploy causes failures in production-like traffic and a
  fix is going to take longer than ~15 minutes.
- **Fix forward** if the issue is confined to dev, or a known quick fix exists.

## Snapshot the current state first

```bash
git log --oneline -5
git status                 # confirm working tree changes match what you deployed
docker compose ps          # what's actually running
```

## Steps

### 1. Revert the code

```bash
# replace N with the safe commit hash from before the bad deploy
git checkout <safe-commit> -- user_service ai_service notification_service kong
# or, for a full revert of the last commit:
# git revert HEAD
```

### 2. Rebuild and restart only what changed

```bash
docker compose up -d --build user-service celery flower \
  ai-service ai-celery ai-celery-beat ai-flower \
  notification_service notification-worker kong
```

### 3. Verify data migrations

- `user_service` runs migrations automatically in `entrypoint.sh`.
- **`ai_service` does not** — if the bad deploy added Alembic migrations, you
  must roll them back or the app may not match the schema:
  ```bash
  docker compose exec ai-service python -m alembic downgrade <prev_revision>
  ```
- If migration was not the problem, leave DB alone.

### 4. Verify the rollback

```bash
docker compose ps                      # all healthy
curl -s http://localhost:8000/health   # notification service responds
curl -s http://localhost:8000/api/health  # kong ok
# exercise a protected route with cookies:
curl -s -b <cookies.txt> http://localhost:8000/api/v1/users/me/
```

Check the services you rolled back in Kong's routing ([routing doc](../infrastructure/kong/routing.md)).

## Post-rollback

- File the incident ([incident-response](./incident-response.md)).
- If you made code changes to roll back, open a PR capturing them so the revert
  isn't lost.
- Rotate any secrets if the bad build logged/leaked them.

## Rollback notes per service

| Service | Rollback mechanism | Special care |
|---|---|---|
| `user_service` | revert code + `--build` | entrypoint auto-migrates; downgrade DB if a bad migration ran |
| `ai_service` | revert code + `--build` | Alembic downgrade required if schema changed |
| `notification_service` | revert code + `--build` | workers + API both restart; queue state in Redis persists |
| `kong` | revert `kong/` + restart | check `kong/.env` still matches Django `SECRET_KEY`, else every JWT fails |