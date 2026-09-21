# Testing

## What exists today

| Service | Framework | Status |
|---|---|---|
| `user_service` | pytest + pytest-django + factory_boy | **~123 tests** across 21 files; runnable |
| `ai_service` | none | no tests; needs a suite |
| `notification_service` | none | empty `tests/` dirs; `vitest`/`supertest` deps installed but unused |

## user_service

Tests live alongside the code under `app/apps/<app>/tests/`, using classes like
`test_services/` and `test_views_v1/`. Config in `pytest.ini`:

```ini
DJANGO_SETTINGS_MODULE = app.config.test_settings
addopts = -v --reuse-db --cov=. --cov-report=term-missing --cov-report=html
testpaths = app/apps/
```

`test_settings.py` uses a `test_` DB prefix, `CELERY_TASK_ALWAYS_EAGER=True`
(no broker), locmem email backend, and a fast (MD5) password hasher. Global
fixtures (`api_client`, `user`, `auth_client`) live in `conftest.py`; factories
in `app/apps/*/tests/factories.py`.

### Running

```bash
cd user_service
source venv/bin/activate        # or use docker: docker compose exec user-service bash
pytest                          # requires PostgreSQL reachable (test_applica_db)
```

Run a subset:

```bash
pytest app/apps/authentication/tests/
pytest app/apps/users/tests/test_me_view.py
```

Coverage: terminal report on every run plus `htmlcov/` (open `htmlcov/index.html`).

Conventions to follow when adding tests:

- Name: `test_<thing>.py` (matches `python_files = test_*.py`).
- View tests authenticate with cookie-based JWT (`auth_client` fixture).
- Use `django_assert_max_num_queries` to guard N+1 issues.
- Assert token blacklisting on logout, cooldowns/429s where applicable.

## ai_service / notification_service

No automated suites yet. Before they exist, verify changes manually:

- ai_service: exercise endpoints through Kong (`http://localhost:8000/api/ai/v1/...`)
  and watch Celery/Flower for pipeline tasks.
- notification_service: call the internal dispatch endpoint and confirm the
  BullMQ job lands and the worker sends (check provider logs / inbox).

## CI integration

There is no CI pipeline wired to tests yet (see
[infrastructure/ci-cd.md](../infrastructure/ci-cd.md)). When CI is added,
a minimal job should run `pytest` for `user_service` and add suites for the
other two services.