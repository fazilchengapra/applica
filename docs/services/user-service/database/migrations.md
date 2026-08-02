# Migrations — user-service

## Conventions

- One migration per PR when possible — keep them reviewable
- Never edit a migration that's already been merged/deployed
- Data migrations vs schema migrations: keep separate when the data migration
  is slow or risky

## Running migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

## Rollback

Document how to roll back a bad migration in each environment (staging/prod).
