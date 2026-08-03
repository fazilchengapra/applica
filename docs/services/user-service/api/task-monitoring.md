# Task Monitoring

## Purpose

Tracks status of background/async jobs triggered by this or other services
(e.g. long-running AI jobs from `ai-service`).

## Model

Document task states (pending/running/success/failed), and how status gets
updated (polling? webhook from ai-service? Celery signal?).

## Business rules / edge cases

- Retry policy on failure
- Task result expiry/cleanup

## Dependencies

- `ai-service` (if tasks originate there)
- `notification` for completion alerts
