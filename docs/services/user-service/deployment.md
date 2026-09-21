# Deployment — user_service

## Current deployment (local / docker-compose)

The service runs as a container built from `user_service/Dockerfile`
(`python:3.12-slim`). `docker-compose.yml` defines:

| Container | Command | Port |
|---|---|---|
| `user-service` | `runserver 0.0.0.0:8000` | internal 8000 (not on host) |
| `celery` | `celery -A app worker -l info` | — |
| `flower` | `celery -A app flower --port=5555` | `5555:5555` |

`entrypoint.sh` waits for the DB with `pg_isready` (unless `SKIP_MIGRATIONS=1`)
and runs `manage.py migrate`.

All external traffic reaches the service **through Kong** (`kong/services/user-service.yml`),
which validates the JWT cookie and rate-limits routes.

## Configuration

- `env_file: ./user_service/.env`
- Compose overrides DB host/port and `REDIS_URL` (`redis://redis:6379/0`)
  inside the container network.

## Pipeline / CI-CD

There is **no automated CI/CD pipeline in the repository yet**. Deploys are
manual: `docker compose up --build <service>` from the repo root. GitHub
Actions is documented as the intended CI tool in
[`docs/infrastructure/ci-cd.md`](../../infrastructure/ci-cd.md); Terraform/K8s
are planned, not in use.

## Environments

| Env | URL | Notes |
|---|---|---|
| local | `http://localhost:8000` (Kong proxy) | `docker compose up` |
| staging | — | not configured |
| production | — | not configured |

## Rollback

There is no image registry yet. Rollback = `git checkout <previous-commit>` on
the service and `docker compose up --build user-service`. See
[deployment rollback runbook](../../runbooks/deployment-rollback.md).

## Infra references

- [Kong routing for this service](../../infrastructure/kong/routing.md)
- [EKS setup (planned)](../../infrastructure/eks-setup.md)
- [Terraform (planned)](../../infrastructure/terraform.md)