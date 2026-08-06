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
| Rate Limiting | Protect APIs by limiting requests per client IP |