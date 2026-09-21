# Incident Response

Runbook for the docker-compose deployment. There is no hosted dashboards stack
yet (Prometheus/Grafana are planned), so detection is manual.

## Severity levels

| Level | Definition | Response time |
|---|---|---|
| P0 | Full outage — 400/500 on all APIs, Kong down, DB down | engage immediately |
| P1 | Major feature broken / one service down (e.g. all tailoring fails) | < 1 hour |
| P2 | Minor issue, degraded but usable (e.g. one email template broken) | same day |
| P3 | Cosmetic / non-urgent | backlog |

## Steps

1. **Acknowledge** — say you're on it; note start time.
2. **Assess severity** — confirm scope (all routes vs one service vs one feature).
3. **Mitigate first** — restart the affected container / revert bad config; get
   traffic flowing again before root-causing.
4. **Root cause after** — use the logs checklist below.
5. **Post-incident writeup** — add an entry to the
   [CHANGELOG](../changelog/CHANGELOG.md) and update
   [Troubleshooting](../services/user-service/troubleshooting.md) if a new
   failure mode was found.

## Logs & diagnostics

```bash
# all services
docker compose logs -f --tail=200

# a specific service / worker
docker compose logs -f ai-service
docker compose logs -f ai-celery
docker compose logs -f notification-worker

# health checks
curl -s http://localhost:8000/health            # notification_service
docker compose ps                               # container states
docker compose exec redis redis-cli ping        # redis alive

# task visibility
curl -s localhost:5555  # user celery Flower
curl -s localhost:5556  # ai celery Flower
docker compose exec redis redis-cli -n 1 LLEN ai_service_queue   # ai queue depth
docker compose exec redis redis-cli LLEN bull:email-dispatch:wait # email queue depth
```

## Common failure patterns

| Symptom | Likely cause | First action |
|---|---|---|
| All APIs 401/403 | Kong can't validate JWTs — `kong/.env` secret mismatch with Django `SECRET_KEY` | check `kong` container logs; align secrets |
| ai_service 403 on every route | `X-Gateway-Secret` mismatch | compare `GATEWAY_INTERNAL_SECRET` across `kong/.env` + `ai_service/.env` |
| DB connection refused in a service | DB container down / wrong host env | `docker compose ps`; hosts are `db`/`ai_postgres`/`notification_postgres` |
| Tailored CVs stuck in `processing` | Celery worker down or a pipeline task failing | check `ai-celery` logs + Flower; inspect `tailoring_runs`/`task_execution` |
| Emails/OTPs not arriving | `notification-worker` down, or provider credentials | check worker logs; BullMQ retry attempts in Redis; verify Twilio/Gmail creds |
| Kong not starting | `kong/.env` missing or ports in use | `docker compose logs kong`; free 8000/8001 |

## Escalation

- Single voice drives the incident; loop in the service owner whose subsystem
  is affected.
- If a fix requires a DB migration on `ai_service`, run it explicitly:
  `docker compose exec ai-service python -m alembic upgrade head`.

## After the incident

- Write the postmortem: timeline, root cause, blast radius, action items.
- Add anything non-obvious to the per-service Troubleshooting pages.
- If config drift caused it (secrets, ports), add a check to CI (see
  [ci-cd](../infrastructure/ci-cd.md)).