# EKS Setup

> **Status: planned, not implemented.** The repository runs everything with
> `docker-compose` today. There is no Kubernetes cluster, no `k8s/` manifests,
> and no Terraform in the repo. This page records the target design.

## Intended cluster overview

- EKS cluster with node groups separating `core-services` / `ai-engine` /
  `observability` namespaces (per environment: dev / staging / prod).
- Deployments: one per service with liveness/readiness probes and resource
  requests/limits; HPA on CPU + custom metrics (queue depth for AI workers,
  active interview sessions).
- Secrets from AWS Secrets Manager / Sealed Secrets; ConfigMaps for config.

## What exists today (instead of EKS)

| Concern | Current implementation |
|---|---|
| Container orchestration | `docker-compose.yml` at repo root |
| Networking | Docker bridge network (service hostnames: `user-service`, `ai-service`, `notification_service`, `kong`, `redis`, `db`, `ai_postgres`, `notification_postgres`) |
| Scaling | manual (`docker compose up -d --scale ...`,` redis`/workers are single-instance) |
| Secrets | `.env` files per service (currently committed in places — should move to a secrets manager) |

## Path to EKS (future)

1. Add per-service `k8s/` manifests (Deployment, Service, Ingress via Kong).
2. Push images to a registry (GHCR/ECR).
3. Wire CI/CD (see [ci-cd](./ci-cd.md)) to `kubectl apply` on merge.
4. Add Prometheus/Grafana for observability once on the cluster.

## kubectl access (once cluster exists)

```bash
aws eks update-kubeconfig --name applica --region <region>
kubectl get pods -n core-services
kubectl logs -f deploy/user-service -n core-services
```