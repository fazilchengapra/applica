# Local Setup — user-service

## Prerequisites

- Python version
- PostgreSQL running locally or via Docker
- Environment variables (list them, or link to `.env.example`)

## Steps

```bash
git clone <repo>
cd user-service
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

## Environment variables

| Variable | Purpose | Example |
|---|---|---|
| `DATABASE_URL` | Postgres connection string | |
| `JWT_SECRET` | Token signing secret | |
| `CLOUDINARY_URL` | Media storage | |

## Running tests

```bash
python manage.py test
```
