# Request Flow

This document describes how an HTTP request travels through the Applica Backend, from the client to the backend service and back.

Understanding this flow makes it easier to debug issues, develop new plugins, and understand how Kong processes requests.

---

# Overview

Every external request enters the system through Kong Gateway.

Kong is responsible for:

- Matching the request to a route
- Applying rate limiting
- Authenticating the user
- Executing custom plugins
- Forwarding the request to the appropriate backend service

```

```
                Client
                   │
                   ▼
          ┌─────────────────┐
          │   Kong Gateway  │
          └─────────────────┘
                   │
          ┌────────┴────────┐
          │                 │
     User Service      AI Service
          │                 │
          ▼                 ▼
      PostgreSQL        AI Processing
```

---

# Complete Request Flow

```
                Client
                   │
                   ▼
          Kong Gateway
                   │
        Route Matching
                   │
          Rate Limiting
                   │
      JWT Authentication
     (Read Cookie & Validate)
                   │
         Custom Plugins
                   │
                   ▼
          Backend Service
                   │
           Business Logic
                   │
              Database
                   │
                   ▼
          Backend Response
                   │
                   ▼
          Kong Gateway
                   │
                   ▼
                Client
```

---

# Step-by-Step Processing

## 1. Client Sends Request

The client sends an HTTP request to the API.

Example:

```http
GET /api/v1/profile HTTP/1.1
Cookie: access_token=<jwt-token>
```

The browser automatically includes the authentication cookie.

---

## 2. Route Matching

Kong compares the incoming request against its configured routes.

Example:

```
/api/v1/auth/*
        │
        ▼
User Service
```

If no matching route exists:

```
HTTP 404 Not Found
```

---

## 3. Rate Limiting

Before authentication, Kong checks whether the client has exceeded the configured request limit.

Current implementation:

- IP-based limiting
- Configured using the Rate Limiting plugin

If the limit has been exceeded:

```
HTTP 429 Too Many Requests
```

The request stops here and is **not** forwarded to the backend service.

---

## 4. JWT Authentication

For protected routes, the authentication plugin:

- Reads the JWT from the HTTP-only cookie
- Verifies the token signature
- Checks the expiration time
- Extracts user claims
- Injects trusted user headers

Example:

```
Cookie
     │
     ▼
Read JWT
     │
Validate
     │
Extract Claims
     │
Inject Headers
```

If authentication succeeds:

```
X-User-Id: 15
X-Gateway-Secret: ***
```

These headers are forwarded to the backend service.

---

## 5. Custom Plugins

Additional plugins may perform operations such as:

- Header injection
- Correlation ID generation
- Request transformation
- Logging

Each plugin executes before the request reaches the backend service.

---

## 6. Backend Service

The request is forwarded to the appropriate microservice.

Examples:

- User Service
- AI Service

The backend performs business logic and communicates with the database or other internal services.

---

## 7. Response

The backend returns a response to Kong.

Kong forwards the response back to the client.

```
Backend
    │
    ▼
Kong
    │
    ▼
Client
```

---

# Failure Scenarios

## Invalid JWT

If the JWT is:

- Missing
- Expired
- Invalid
- Incorrectly signed

The authentication plugin immediately rejects the request.

Flow:

```
Client
   │
   ▼
Kong
   │
Read JWT
   │
Invalid
   │
   ▼
HTTP 401 Unauthorized
```

The backend service is **never called**.

---

## Rate Limit Exceeded

If the client exceeds the configured request limit:

```
Client
   │
   ▼
Kong
   │
Rate Limit Check
   │
Exceeded
   │
   ▼
HTTP 429 Too Many Requests
```

The request is rejected before authentication or backend processing.

---

## Service Unavailable

If Kong successfully processes the request but cannot reach the backend service:

```
Client
   │
   ▼
Kong
   │
Authentication ✓
Rate Limit ✓
   │
Backend Unavailable
   │
   ▼
HTTP 503 Service Unavailable
```

Possible causes include:

- Service container is stopped
- Network connectivity issues
- Backend timeout
- DNS resolution failure

---

# Response Summary

| Situation | HTTP Status | Process Stops At |
|-----------|------------:|------------------|
| Route not found | 404 | Route matching |
| Rate limit exceeded | 429 | Rate limiting |
| Invalid or expired JWT | 401 | Authentication |
| Backend unavailable | 503 | Service forwarding |
| Successful request | 200–299 | Backend response |

---

# Summary

Every external request follows the same processing pipeline:

```
Client
    │
    ▼
Route Match
    │
Rate Limit
    │
JWT Authentication
    │
Custom Plugins
    │
Backend Service
    │
Database
    │
Response
    ▼
Client
```

By handling routing, authentication, rate limiting, and plugin execution at the gateway, Kong keeps backend services focused on business logic while providing centralized security, traffic management, and observability.