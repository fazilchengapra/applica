# Service Map

A living index of every service, its apps/modules, and who owns it.

## user-service (Django)

| App | Purpose | Owner |
|---|---|---|
| `authentication` | Login, JWT issuing/refresh, OTP, password reset | |
| `users` | Core user model, account CRUD | |
| `profile` | Extended profile data | |
| `task_monitoring` | Background job / task status tracking | |
| `notification` | Email/push/in-app notifications | |

## ai-service (FastAPI)

| Module | Purpose | Owner |
|---|---|---|
| | | |

## Inter-service dependencies

Document who calls whom, and whether it's a hard dependency (blocks a request) or soft (fire-and-forget, e.g. notification events).
