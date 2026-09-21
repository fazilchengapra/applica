# Task Monitoring

## Purpose

Logs every Celery task execution (send OTP SMS, send emails, revoke tokens)
so background work is observable and debuggable without digging through
Redis/Celery internals.

## Model

Table `TaskExecution` (`app/apps/task_monitoring/models.py`):

| Field | Type | Notes |
|---|---|---|
| `task_id` | unique | Celery task UUID |
| `root_task_id` / `parent_task_id` | | task tree |
| `task_name` | | e.g. `app.apps.authentication.tasks.send_otp_sms_task` |
| `queue`, `worker` | | where it ran |
| `status` | enum | `PENDING / STARTED / SUCCESS / FAILURE / RETRY / REVOKED` |
| `retries` | int | |
| `args` / `kwargs` / `result` | JSON | payload snapshots |
| `exception`, `traceback` | text | on failure |
| timing fields | | created / started / completed timestamps |

Indexes exist on `status`, `task_name`, `created_at`.

## How status gets updated

`app/apps/task_monitoring/signals.py` registers Celery **signals**
(`task_success`, `task_failure`) and upserts the `TaskExecution` row. There is
no polling and no webhook from `ai_service` — the recording is entirely
signal-driven on the same worker process.

## Business rules / edge cases

- One row per `task_id` (upsert, not append).
- Failed tasks keep `exception` + `traceback` for diagnosis.
- Retry policy lives in each task definition (e.g. OTP SMS: 3 retries, 15s
  delay; emails: 3 retries, 30s delay).

## Celery tasks currently monitored (`app/apps/authentication/tasks.py`, `app/apps/users/tasks.py`)

| Task | Purpose |
|---|---|
| `send_otp_sms_task` | Twilio SMS delivery |
| `send_password_reset_email_task` | Reset-link email |
| `send_email_verification_task` | Verification email (incl. email change) |
| `revoke_all_tokens_task` | Blacklist tokens on account deletion |

## Dependencies

- Celery broker/backend: Redis (`REDIS_URL`)
- Monitoring UI: Flower on `:5555`
- `task_monitoring` app must be installed for signals to load (it is).