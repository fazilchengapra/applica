# Headers

This document describes the HTTP headers used throughout the Applica Backend and identifies whether they are provided by the client, Kong Gateway, or custom plugins.

Headers allow Kong and backend services to exchange authentication, tracing, and networking information without modifying the request body.

---

# Overview

During request processing, Kong may:

- Read headers from the client
- Add new headers
- Forward selected headers
- Remove sensitive headers
- Inject user context for backend services

```
Client
   │
   │ Request Headers
   ▼
Kong Gateway
   │
   ├── Read Headers
   ├── Add Headers
   ├── Remove Headers
   ▼
Backend Service
```

---

# Header Reference

| Header | Added By | Purpose |
|----------|----------|---------|
| `Cookie` | Client | Carries the JWT access token in an HTTP-only cookie. |
| `X-User-Id` | Custom Authentication Plugin | Authenticated user's unique identifier. |
| `X-Request-Id` | Correlation ID Plugin | Unique request identifier used for tracing and debugging. |
| `X-Gateway-Secret` | Custom Authentication Plugin | Adding a stamp it's verified the gatway |
| `X-Internal-Secret` | Calling backend service | Shared secret proving a service-to-service call is legitimate. Verified by the `internal-secret-auth` plugin. |
| `X-Internal-Service` | `internal-secret-auth` plugin | Names the caller that presented a valid secret, so the backend can log who is calling. |

---

# Client Headers

These headers originate from the client and are forwarded through Kong.

## Cookie

The browser automatically includes the authentication cookie for protected requests.

Example:

```http
Cookie: access_token=<jwt-token>
```

Kong reads the JWT from this cookie during authentication.

---

## Host

Identifies the requested host.

Example:

```http
Host: api.example.com
```

---

# Headers Added by the Custom Authentication Plugin

After validating the JWT, the authentication plugin may inject trusted headers for downstream services.

## X-User-Id

Contains the authenticated user's identifier extracted from the JWT.

Example:

```http
X-User-Id: 15
```

Backend services can use this value without parsing the JWT again.

---

## X-Gateway-Secret

The Kong trusted seal. Backend services compare it against their own configured
value to confirm a request really came through the gateway.

Example:

```http
X-Gateway-Secret: ***
```

---

# Service-to-Secret Headers

The public flow above is browser → Kong → service. Internal calls skip the
browser entirely: one backend service calls another through Kong with a shared
secret instead of a JWT.

## X-Internal-Secret

Sent by the **calling** service on routes guarded by `internal-secret-auth`. Kong
compares it to the configured secret and returns `401` on a mismatch, so the
request never reaches the backend.

Example:

```http
X-Internal-Secret: ***
```

Because this credential bypasses JWT auth, treat it as a bearer token for the
backend: keep it out of browser code, out of logs, and in sync across Kong and
every calling service.

## X-Internal-Service

Added by the `internal-secret-auth` plugin after the secret is accepted, and set
to the route's configured `internal_service` (e.g. `home-bff`). It is a
diagnostic label only — a backend that also guards the route with a secret check
must not rely on this header in place of verifying the secret.

---

# Correlation Header

## X-Request-Id

Each request receives a unique identifier for tracing.

Example:

```http
X-Request-Id: e6c1c7dd-8c73-4a77-ae84-95cf6c4efb73
```

This value should be included in application logs to trace a request across multiple services.

---

# Request Flow

```
Browser
    │
    │ Cookie: access_token=<JWT>
    ▼
Kong Gateway
    │
    ├── Validate JWT
    ├── Add X-User-Id
    ├── Add X-Gateway-Secret
    ▼
Backend Service
```

Internal calls use a different path — no JWT, no user context, just the secret:

```
Calling Backend Service
    │
    │ X-Internal-Secret: ***
    ▼
Kong Gateway
    │
    ├── Verify secret
    ├── Add X-Internal-Service
    ▼
Target Backend Service
```

---

# Security Notes

- Backend services should trust user identity only when requests originate through Kong.
- User context headers should not be accepted directly from external clients.
- JWTs remain stored in HTTP-only cookies and are not exposed to frontend JavaScript.
- The internal secret is not a user credential. It grants service-level access to internal routes, so it must never be shipped to a client.

---

# Summary

Kong enriches incoming requests with trusted metadata before forwarding them to backend services. Authentication headers, tracing identifiers, and forwarding headers simplify backend development while improving observability and security.