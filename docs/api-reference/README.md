# API Reference

This folder holds **generated** OpenAPI/Swagger specs (one per service).
Generated files should not be edited by hand.

## Where the schemas come from

| Service | Tooling | How to generate |
|---|---|---|
| `user_service` | drf-spectacular | `GET /api/schema/` (JSON) — served live by the app; Swagger UI at `GET /api/docs/`, ReDoc at `GET /api/redoc/` |
| `ai_service` | FastAPI built-in OpenAPI | `GET /openapi.json` (or `/docs` Swagger UI) on the running service |
| `notification_service` | none (no OpenAPI middleware wired) | manual; see `docs/services/notification-service/README.md` |

## Exporting a spec to this folder

```bash
# user_service (via Kong: :8000, or directly if the service is port-mapped)
curl -s http://localhost:8000/api/schema/ -o docs/api-reference/openapi/user-service.openapi.json

# ai_service (via Kong)
curl -s http://localhost:8000/api/ai/v1/../openapi.json -o docs/api-reference/openapi/ai-service.openapi.json
```

> The ai_service OpenAPI path depends on the app's mounted router; use
> `curl http://localhost:8000/openapi.json` if the service is reachable
> directly.

## Conventions

- One file per service: `<service>.openapi.json`.
- Regenerate on release; do not hand-edit.
- The `authentication` endpoint tables in
  `docs/services/user-service/api/*.md` are kept in sync manually — treat the
  generated spec as ground truth.