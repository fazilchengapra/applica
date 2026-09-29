# Plugins

This document describes the Kong plugins currently used in the Applica Backend.

Plugins allow Kong to apply cross-cutting concerns such as authentication, rate limiting, logging, and request transformation without requiring implementation inside every backend service.

---

# Plugin Execution Lifecycle

For every incoming request, Kong executes plugins during different phases of the request lifecycle.

```
Incoming Request
        │
        ▼
Route Matching
        │
        ▼
Authentication Plugins
        │
        ▼
Rate Limiting Plugins
        │
        ▼
Custom Plugins
        │
        ▼
Backend Service
        │
        ▼
Response Plugins
        │
        ▼
Logging Plugins
        │
        ▼
Client
```

---

# JWT Authentication Plugin

## Purpose

The Applica Backend uses a custom JWT authentication plugin to authenticate users before requests reach backend services.

Unlike the default Kong JWT plugin, this implementation validates JWTs stored inside secure HTTP-only cookies.

Responsibilities include:

- Read JWT from the authentication cookie
- Validate the JWT signature
- Verify token expiration
- Extract user claims
- Reject unauthorized requests
- Inject trusted user headers for downstream services

---

## Configuration

Example:

```yaml
plugins:
  - name: jwt
    config:
      claims_to_verify:
        - exp
      key_claim_name: iss
      cookie_names:
        - access_token
  - name: header_injector
      config:
        gateway_secret: "__GATEWAY_INTERNAL_SECRET__"
```
---

## Execution Order

The authentication plugin executes before protected requests are forwarded to backend services.

```
Client
    │
    ▼
Read JWT Cookie
    │
Validate JWT
    │
Extract User Claims
    │
Inject Headers
    │
    ▼
Backend Service
```

If authentication fails, Kong immediately returns an HTTP `401 Unauthorized` response.

---

## Example

Incoming request:

```http
GET /api/v1/profile HTTP/1.1
Cookie: access_token=<jwt-token>
```

Headers forwarded to the backend (example):

```http
X-User-Id: 15
X-Gateway-Secret: ***
```

---

# Rate Limiting Plugin

## Purpose

The Rate Limiting plugin protects backend services by limiting how many requests a client can make within a configured time window.

Benefits include:

- Preventing API abuse
- Protecting backend services
- Reducing denial-of-service attacks
- Ensuring fair resource usage

---

## Configuration

Example:

```yaml
plugins:
  - name: rate-limiting
    config:
      minute: 10
      policy: redis
      redis_host: redis
      redis_port: 6379
      limit_by: ip
      hide_client_headers: false
```

Configuration summary:

| Option | Description |
|---------|-------------|
| `minute` | Maximum requests per minute |
| `policy` | Counter storage policy |
| `limit_by` | Client identifier (`ip`) |
| `hide_client_headers` | Controls whether rate limit headers are returned |

---

## Example

Client requests:

```
Request 1
✔ Allowed

...

Request 10
✔ Allowed

Request 11
✘ HTTP 429 Too Many Requests
```

Example response:

```http
HTTP/1.1 429 Too Many Requests

{
    "message": "API rate limit exceeded"
}
```

---

# Role Auth Plugin

## Purpose

`role-auth` decides whether a caller may use the admin routes of a service, and
marks approved requests with `X-Admin-Authorized` so backends (for example
`require_admin` in `ai_service`) can trust the gateway rather than re-checking
roles.

Two rules govern its behaviour:

1. It **always strips** a client-supplied `X-Admin-Authorized` header. Only the
   plugin itself sets that header, after a successful role check — a client can
   never spoof admin access by sending the header directly.
2. `allowed_roles` is **optional**. When it is omitted or empty the route runs in
   pass-through mode: any authenticated caller is allowed (a token without a
   `roles` claim is treated as the default `user` role) and no admin header is
   injected. Use this when a route is shared between admins and ordinary users.

Without a valid JWT (`401` precedes the role check) or without a matching role
(`403`) the request never reaches the backend.

## Configuration

Admin route:

```yaml
plugins:
  - name: role-auth
    config:
      allowed_roles:
        - admin
        - staff
```

Shared route (every authenticated user allowed, spoofed admin header removed):

```yaml
plugins:
  - name: role-auth
    config:
      allowed_roles: []
```

| Option | Description |
|--------|-------------|
| `allowed_roles` | Roles permitted on the route, read from the JWT `roles` claim. Empty means pass-through |

## Example

```http
GET /api/ai/v1/admin/users/15/master-cv HTTP/1.1
Cookie: access_token=<jwt with roles ["user","staff","admin"]>
```

Headers forwarded to `ai-service` (example):

```http
X-User-Id: 15
X-Gateway-Secret: ***
X-Admin-Authorized: true
```

A caller whose token only carries `roles: ["user"]` gets an HTTP `403` from Kong,
and the backend never receives `X-Admin-Authorized`.

---

# Internal Secret Auth Plugin

## Purpose

`internal-secret-auth` guards routes that are only meant to be called by another
backend service, not by an end user. The caller presents a shared secret in the
`X-Internal-Secret` header and Kong compares it to the configured
`gateway_secret`; a missing or mismatched value gets an HTTP `401` before the
request reaches the service. No JWT is involved, so these routes stay off the
public authentication path.

On success the plugin stamps `X-Internal-Service` with the configured caller
name. Backends can re-verify the same secret (user_service's
`InternalSecretPermission` does, as defence in depth) rather than trusting the
stamp alone.

`gateway_secret` is the platform-wide `GATEWAY_INTERNAL_SECRET`; it must be kept
in sync between `kong/.env` and every calling/consuming service.

## Configuration

```yaml
plugins:
  - name: internal-secret-auth
    config:
      gateway_secret: <GATEWAY_INTERNAL_SECRET>
      internal_service: home-bff
```

| Option | Description |
|--------|-------------|
| `gateway_secret` | Shared secret a caller must present in `X-Internal-Secret` |
| `internal_service` | Value written to the forwarded `X-Internal-Service` header, naming the caller. Defaults to `notification-dispatcher` |

---

# Future Plugins

As the platform grows, additional plugins may be introduced, including:

- Correlation ID
- Request Logging
- Response Transformation
- Metrics and Monitoring
- Consumer-based Rate Limiting

---

# Summary

Plugins allow Kong to centralize common API functionality outside of backend services. The Applica Backend currently uses:

| Plugin | Purpose |
|--------|---------|
| JWT Authentication | Authenticate users using JWT stored in HTTP-only cookies |
| Role Auth | Enforce roles on admin routes and inject `X-Admin-Authorized` |
| Rate Limiting | Protect APIs by limiting requests per client IP |