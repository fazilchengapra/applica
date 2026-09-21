# Coding Standards

## Python / Django (user_service, ai_service)

### Style

- Follow **flake8 / ruff** conventions; black-style formatting (4-space indent).
- **Import ordering:** stdlib → third-party → local (one block each).
- Type hints on new functions; keep annotations meaningful.

### Django app structure (user_service)

Each app follows a layered layout — thin views, fat services:

```
app/apps/<name>/
├── api/v1/
│   ├── urls.py                  # URL routing
│   ├── serializers/             # DRF serializers
│   ├── views/                   # APIView classes (dispatch only)
│   └── pagination/              # PageNumberPagination subclasses
├── services/                    # business logic (most logic lives here)
├── models.py (or models/)       # DB models
├── tasks.py                     # Celery shared tasks
├── exceptions/                  # domain exceptions
├── constants/                   # enums / cooldown / TTL values
└── tests/                       # pytest + factory_boy
```

- Keep domain exceptions in `exceptions/`, enums in `constants/`.
- Celery tasks in `tasks.py`; monitor them via the `task_monitoring` signals.

### FastAPI structure (ai_service)

Feature-per-module under `app/modules/<feature>/` with `models/`,
`services/`, `tasks.py`, `repositories/` where applicable. Routers are thin,
registered centrally in `app/api/v1/router.py` and mounted under
`/api/ai/v1/<prefix>`.

## API conventions

- **Versioning:** all REST endpoints live under `/api/v1/<service>/...`
  (`user_service` uses `/api/v1/<app>/`; `ai_service` uses `/api/ai/v1/`).
- **Internal headers** (injected by Kong — never accepted as-is from clients
  at the edge):
  - `X-User-Id` — authenticated user id (from JWT `sub`), required by
    user-scoped ai_service routes.
  - `X-Gateway-Secret` — proves the request passed through Kong; verified by
    ai_service middleware and used for service-to-service dispatch.
  - `X-Admin-Authorized` — set by Kong for admin routes (with `role-auth`).
  - `X-Internal-Secret` / `X-Internal-Service` — internal dispatch auth.
- **Auth:** cookie-based JWTs (`access_token` / `refresh_token`, HttpOnly).
  Backends must trust gateway headers only when the request entered via Kong.
- **Errors:** DRF uses standard `{"detail": ...}` / validation shapes; ai_service
  returns FastAPI `{"detail": ...}` with mapped status codes (400 validation,
  404 missing, 502 provider failures).
- **IDs across services** are plain integers/uuid — never cross-DB FKs.

## Node / TypeScript (notification_service)

- Strict TypeScript (`tsconfig` strict), CommonJS, `nodenext` resolution.
- Validate all inbound event payloads with **Zod** schemas.
- Log with **Pino** (JSON in prod); never `console.log` in production paths.
- Providers wrapped so failures are logged and rethrown for BullMQ retry —
  do not silently swallow provider errors.
- Queue/worker definitions stay in `src/queues` / `src/workers`.

## General

- **No secrets in source.** `.env` is gitignored; commit `.env.example` only.
  (Historical `.env` files are committed in some services — rotate them.)
- One migration per PR where possible; never edit a merged migration.
- New endpoints require tests in `user_service`; add suites in the other two
  services as they are built out.