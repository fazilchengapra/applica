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

the kong truested seal.

Example:

```http
X-Gateway-Secret: ***
```
this help to services verify the request is valid or not

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

---

# Security Notes

- Backend services should trust user identity only when requests originate through Kong.
- User context headers should not be accepted directly from external clients.
- JWTs remain stored in HTTP-only cookies and are not exposed to frontend JavaScript.

---

# Summary

Kong enriches incoming requests with trusted metadata before forwarding them to backend services. Authentication headers, tracing identifiers, and forwarding headers simplify backend development while improving observability and security.