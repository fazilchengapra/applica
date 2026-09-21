# ADR-0003: API Gateway — Kong (DB-less)

**Status:** Accepted
**Date:** 2026-09-01

## Context

The backend is a set of independently-deployable services (`user_service`,
`ai_service`, `notification_service`) that must share consistent
authentication (JWT cookie verification), rate limiting, and identity
propagation. Without a gateway, every service would re-implement auth and
each admin route would have to be secured service-side.

Constraints:

- JWT cookies are issued by `user_service` and signed with the Django
  `SECRET_KEY` (HS256, issuer `applica-user-service`).
- Services must be able to trust that a request came through the gateway
  (internal secret header).
- Config must be easy to version and change without a gateway database.

## Decision

Use **Kong Gateway OSS** as the single ingress, running in **DB-less
declarative mode** (`KONG_DATABASE: off`).

- Declarative config is assembled at container startup by `kong/start-kong.sh`
  from a base template + one YAML fragment per service (`kong/declarative/`,
  `kong/services/*.yml`), with secrets substituted from `kong/.env`.
- A shared consumer `user-service-issuer` holds the HS256 secret identical to
  the Django `SECRET_KEY`, so the bundled `jwt` plugin validates cookies at the
  edge with `key_claim_name: iss`.
- Three custom Lua plugins add gateway-specific behavior:
  - `header_injector` — decode JWT payload, set `X-User-Id` (from `sub`) and
    `X-Gateway-Secret`, share claims via `kong.ctx.shared`.
  - `internal-secret-auth` — verify `X-Internal-Secret` for service-to-service
    dispatch, inject `X-Internal-Service: notification-dispatcher`.
  - `role-auth` — enforce `allowed_roles` from the JWT `roles` claim on admin
    routes.
- Bundled `rate-limiting` (Redis-backed, `limit_by: ip`) applied per public
  route.

## Consequences

**Easier:**

- Consistent edge auth/rate-limiting/admin-role checks without service-side
  duplication.
- Backend services trust `X-Gateway-Secret` and stay focused on business logic.
- Routing changes are plain YAML diffs, validated by `kong config parse`.

**Harder / trade-offs (accepted for now):**

- Admin routes rely on Kong-gated access; if a backend is reachable directly
  (without Kong), those views are effectively unprotected — must keep ports
  sealed (compose does not map service ports to the host).
- `header_injector` decodes the JWT payload without signature checking; it
  depends on the bundled `jwt` plugin running first (priority ordering).
- The `kong/.env` secrets (JWT secret, internal secret) must stay in sync with
  service envs or every request fails auth.

## Alternatives considered

- **AWS API Gateway / managed gateways** — not used because the deployment is
  local docker-compose; no cloud provider integration yet.
- **Service-side JWT verification only** — rejected because it duplicated auth
  logic in every service and gave no centralized rate limiting.
- **Kong with a backing database** — rejected; DB-less declarative config
  keeps everything reproducible from the repo.

## Related

- [Kong documentation](../../infrastructure/kong/README.md)
- [System overview](../system-overview.md)