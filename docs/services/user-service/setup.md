# Local Setup — user_service

## Prerequisites

- Python 3.12
- PostgreSQL 16 (running, with a database created)
- Redis (running on `REDIS_URL`, default `redis://localhost:6379`)
- Environment variables — copy `.env.example` to `.env` and fill in values

## Steps (standalone, without Docker)

```bash
cd user_service
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in secrets

python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

In a second terminal run the Celery worker (needed for SMS/email tasks):

```bash
celery -A app worker -l info
```

## Environment variables

From [`app/config/settings.py`](../../../user_service/app/config/settings.py)
and `.env.example`:

| Variable | Purpose | Example |
|---|---|---|
| `SECRET_KEY` | Django signing key; also signs JWTs | |
| `DEBUG` | Django debug flag | `True` |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` | PostgreSQL credentials | `applica_db` |
| `DB_HOST` / `DB_PORT` | DB host/port | `localhost` / `5432` |
| `REDIS_URL` | Cache + Celery broker | `redis://localhost:6379/0` |
| `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` / `TWILIO_PHONE_NUMBER` | SMS OTP delivery | |
| `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL` | SMTP (Gmail) | |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Google OAuth | |
| `FRONTEND_URL` | Base URL used in verification/reset links | `http://localhost:3000` |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_REGION` / `SNS_NOTIFICATIONS_TOPIC_ARN` | SNS publishing | |
| `INTERNAL_SHARED_SECRET` | Verified on `/api/v1/notify/push/` | |

## Running tests

```bash
cd user_service
source venv/bin/activate
pytest        # needs PostgreSQL reachable (uses test_applica_db, --reuse-db)
```

See [../guides/testing.md](../../guides/testing.md) for details.

## Running via Docker (recommended)

```bash
docker compose up --build user-service celery flower
```

`entrypoint.sh` waits for Postgres (`pg_isready`), then runs migrations.
The service is **not** exposed on a host port in compose — reach it through
Kong at `http://localhost:8000/api/v1/...`.