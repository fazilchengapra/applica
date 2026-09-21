# Terraform

> **Status: planned, not implemented.** There is no Terraform code in this
> repository; infrastructure is defined in [`docker-compose.yml`](../../docker-compose.yml)
> at the repo root. This page records the intended design.

## Intended module layout

```
infra/
├── modules/
│   ├── networking/       # VPC, subnets
│   ├── eks-cluster/
│   ├── rds-postgres/
│   ├── pgvector-postgres/
│   ├── elasticache/      # Redis
│   ├── s3/               # CV PDFs, templates, rendered CVs
│   ├── sqs-sns/
│   └── iam/
├── envs/
│   ├── dev/
│   ├── staging/
│   └── production/       # per-env state
```

## State management (intended)

- Remote state in S3 with DynamoDB-based state locking.
- Same modules across dev/staging/prod with different variable inputs.

## What is provisioned today (docker-compose)

| Resource | Provisioned by |
|---|---|
| PostgreSQL `applica_db` (:5432) | `db` service in compose |
| PostgreSQL + pgvector `ai_service_db` (:5433) | `ai_postgres` service |
| PostgreSQL `not_service_db` (:5434) | `notification_postgres` service |
| Redis (:6379) | `redis` service |
| S3 (CV assets) | external (ai_service S3 config) |
| API gateway | Kong container (declarative config) |

## Common commands (once Terraform is added)

```bash
terraform plan -var-file=envs/dev.tfvars
terraform apply -var-file=envs/dev.tfvars
```

Until then, the equivalent local command is:

```bash
docker compose up --build
```