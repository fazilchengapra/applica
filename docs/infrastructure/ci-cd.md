# CI/CD

> **Current status: no CI/CD pipeline exists.** All deployment is manual via
> `docker compose`. This document captures the intended design so it can be
> implemented incrementally.

## Intended pipeline overview (GitHub Actions)

| Stage | Runs | Trigger |
|---|---|---|
| Lint & format | flake8/ruff (Python), eslint/tsc (TS) | every PR |
| Tests | `user_service` pytest suite | every PR |
| Build | `docker build` each service image | every PR / merge to main |
| Deploy | `docker compose up --build` on host | merge to main (manual approval for prod) |

## Environments

| Env | How it is deployed | Gates |
|---|---|---|
| local | `docker compose up --build` | none |
| staging | manual SSH + compose (future) | tests passing |
| production | to be defined (K8s/EKS is planned, see [eks-setup](./eks-setup.md)) | manual approval |

## What would need wiring

- A `.github/workflows/` directory (does not exist yet).
- Per-service image build stages and a registry (currently no image is pushed;
  compose builds locally).
- A smoke check against Kong (`curl http://localhost:8000/health`) after deploy.