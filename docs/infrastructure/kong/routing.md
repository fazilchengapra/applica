# Routing

How Kong routes incoming requests to backend services, and how public vs
protected endpoints are organized.

---

# Services

A **Service** in Kong represents a backend application that receives forwarded
requests. Each service defines where Kong sends traffic after a route matches.
Defined in [`kong/services/*.yml`](../../../kong/services/):

| Service | Purpose | Backend URL |
|---|---|---|
| `user-service` | Accounts, auth, profiles, notify dispatch | `http://user-service:8000` |
| `ai-service` | CV processing, matching, tailoring | `http://ai-service:8001` |
| `notification-service` | Email/SMS/realtime dispatch, WS | `http://notification_service:8000` |

> All services run with `strip_path: false` and `preserve_host: true`, so the
> path prefix is forwarded unchanged and the original host header is kept.

---

# Routes (21 total)

## user-service (17 routes) — `kong/services/user-service.yml`

| Route | Paths | Plugins |
|---|---|---|
| `user-service-v1-session` | `/api/v1/auth/token/refresh/`, `/api/v1/auth/logout/` | rate-limit 60/min |
| `user-service-v1-email-verify` | `/api/v1/auth/email/verify/` | rate-limit 10/hour |
| `user-service-v1-email-verify-req` | `/api/v1/auth/email/verify/request/` | rate-limit 5/hour |
| `user-service-v1-email-login` | `/api/v1/auth/email/login/` | rate-limit 10/min |
| `user-service-v1-phone-login-req` | `/api/v1/auth/phone/login/request/` | rate-limit 5/hour |
| `user-service-v1-phone-login` | `/api/v1/auth/phone/login/verify/` | rate-limit 10/min |
| `user-service-v1-password-forgot` | `/api/v1/auth/password/forgot/` | rate-limit 5/hour |
| `user-service-v1-password-reset` | `/api/v1/auth/password/reset/` | rate-limit 10/hour |
| `user-service-v1-google` | `/api/v1/auth/google/` | rate-limit 10/min |
| `user-service-v1-users-public` | `/api/v1/users/`, `/api/v1/notify/push/` (POST only) | — |
| `user-service-admin` | `/api/admin/` | — |
| `user-service-static` | `/static/` | — |
| `user-service-v1-protected` | `/api/v1/auth`, `/api/v1/user`, `/api/v1/profile` | jwt + header_injector |
| `admin-routes` | `/api/v1/users/admin` | jwt + header_injector + role-auth (admin, staff) |
| `user-profile-view` | `/api/v1/users/me` | jwt + header_injector |
| `admin-route-user` | `/api/v1/users` | jwt + header_injector + role-auth |
| `admin-route-auth-details` | `/api/v1/auth/admin/` | jwt + header_injector + role-auth |

## ai-service (1 route) — `kong/services/ai-service.yml`

| Route | Paths | Plugins |
|---|---|---|
| `ai-service-v1-protected` | `/api/ai/v1` | jwt + header_injector |

## notification-service (3 routes) — `kong/services/notification-service.yml`

| Route | Paths | Plugins |
|---|---|---|
| `realtime-cv-status` | `/api/v1/notifications/realtime/cv-status` | — |
| `notification-dispatch-secure` | `/api/v1/notifications` | internal-secret-auth |
| `websocket-connection` | `/ws/notifications/` | jwt + header_injector |

---

# Public vs Protected Endpoints

## Public endpoints (no JWT)

| Endpoint | Notes |
|---|---|
| `POST /api/v1/auth/email/login/` | rate-limited |
| `POST /api/v1/auth/google/` | rate-limited |
| `POST /api/v1/auth/phone/login/request/` and `/verify/` | rate-limited |
| `POST /api/v1/auth/password/forgot/` and `/reset/` | rate-limited |
| `POST /api/v1/auth/email/verify/` and `/request/` | rate-limited |
| `POST /api/v1/users/` | registration |
| `POST /api/v1/notify/push/` | internal dispatch (service-side secret check) |
| `POST /api/v1/notifications/realtime/cv-status` | realtime status ingest |
| `/api/admin/`, `/static/` | Django admin/static (no gateway plugins) |
| `/health` | health check |

## Protected endpoints (JWT required)

Protected routes validate the JWT **at Kong** from the `access_token` cookie:

```http
GET /api/v1/users/me HTTP/1.1
Cookie: access_token=<jwt>
```

On success Kong injects `X-User-Id`, `X-Gateway-Secret` (and on admin routes
`X-Admin-Authorized` via `role-auth`) before forwarding. On failure Kong
returns `401` without reaching the backend — see
[authentication](./authentication.md) and [headers](./headers.md).

| Endpoint | Notes |
|---|---|
| `/api/v1/auth/*`, `/api/v1/user/*`, `/api/v1/profile*` | jwt + header_injector |
| `/api/v1/users/me` | jwt + header_injector |
| `/api/v1/users/admin`, `/api/v1/users`, `/api/v1/auth/admin/` | + role-auth (admin, staff) |
| `/api/ai/v1` | jwt + header_injector |

---

# Routing flow

Request lifecycle:

```
Client → Kong (proxy :8000)
   → route match (path prefix → service)
   → execute plugins (jwt → header_injector → role-auth → rate-limiting)
   → forward to backend with injected headers
   → response back through Kong → client
```

---

# Summary

- **Services** define backend applications (3 in this repo).
- **Routes** determine which requests belong to each service.
- **Public endpoints** are accessible without authentication (but often
  rate-limited).
- **Protected endpoints** require a valid JWT cookie; Kong authenticates before
  requests reach the backend and injects identity/gateway headers.