# user_service

Django 6 + Django REST Framework service. Owns accounts, authentication,
profiles, in-app notifications, and Celery task monitoring.

## What it does

- **Auth** — email/password login, phone OTP login, Google OAuth, verification
  tokens, password reset/change, dual-confirmation email & phone change.
  Sessions are **cookie-based JWTs** (HttpOnly `access_token` + `refresh_token`).
- **Users** — custom `User` model (email as login id), registration, `/me`,
  soft-delete, admin list/overview/toggle.
- **Profiles** — 1:1 extended identity data (`profiles` app).
- **Notifications** — persisted notification log + WebSocket push
  (`ws/notifications/`), plus an internal dispatch endpoint used by other
  services and SNS publishing.
- **Task monitoring** — every Celery task writes a `TaskExecution` row.

## Apps in this service

| App | Purpose | API docs |
|---|---|---|
| `authentication` | Login, JWT issuing/refresh, OTP, password, Google OAuth | [authentication](./api/authentication.md) |
| `users` | Core user model, registration, `/me`, admin | [users](./api/users.md) |
| `profiles` | Extended profile data | [profile](./api/profile.md) |
| `notifications` | In-app notifications, WebSocket, SNS publisher | [notification](./api/notification.md) |
| `task_monitoring` | Celery task status tracking (`TaskExecution`) | [task-monitoring](./api/task-monitoring.md) |

## Docs in this service

- [Setup](./setup.md) — run it locally / via docker
- [Database](./database/schema.md) — models and relationships
- [Deployment](./deployment.md) — how the service is run & configured
- [Troubleshooting](./troubleshooting.md) — common issues and fixes

## Tech stack

- Django 6.0 + Django REST Framework 3.17
- djangorestframework-simplejwt (cookie-based JWT)
- Django Channels 4 / Daphne (WebSocket: `/ws/notifications/`)
- Celery 5 + Redis (broker), Flower for monitoring
- PostgreSQL 16, django-redis
- Twilio (SMS/OTP), Django SMTP backend (Gmail), Google OAuth (`google-auth`)
- AWS SNS (`boto3`) for event publishing
- drf-spectacular: OpenAPI schema at `/api/schema/`, Swagger at `/api/docs/`

## Configuration

Environment variables are loaded from `.env` via `python-dotenv`. See
[`user_service/.env.example`](../../../user_service/.env.example) for the full
list (secrets: `SECRET_KEY`, Twilio, SMTP, Google OAuth, AWS SNS).

Key settings in [`app/config/settings.py`](../../../user_service/app/config/settings.py):
- JWT: access 15 min, refresh 7 days, issuer `applica-user-service`
- `AUTH_USER_MODEL = "users.User"`
- CORS: `http://localhost:3000` with credentials

## Related

- [Service map](../../architecture/service-map.md)
- [Kong routing for this service](../../infrastructure/kong/routing.md)