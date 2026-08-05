# Routing

This document explains how Kong routes incoming requests to backend services and how public and protected endpoints are organized.

---

# Overview

Kong acts as the single entry point for all external API requests.

Instead of clients communicating directly with backend services, every request first reaches Kong, which determines the correct destination based on the configured routes.

```
                Client
                   │
                   ▼
          ┌─────────────────┐
          │   Kong Gateway  │
          └─────────────────┘
            │            │
            ▼            ▼
     User Service    AI Service
```

---

# Services

A **Service** in Kong represents a backend application that receives forwarded requests.

Each service defines where Kong should send traffic after a route has been matched.

Current services:

| Service | Purpose | Backend URL |
|----------|---------|-------------|
| User Service | Authentication, profile management, user operations | `http://user-service:8000` |
| AI Service | Resume parsing, AI processing, CV optimization | `http://ai-service:8000` |

Example configuration:

```yaml
services:
  - name: user-service
    url: http://user-service:8000

  - name: ai-service
    url: http://ai-service:8000
```

---

# Routes

A **Route** defines which incoming requests belong to a particular service.

Kong matches the request path, method, host, or other criteria and forwards the request to the associated service.

Example:

| Request | Destination |
|----------|-------------|
| `/api/v1/auth/*` | User Service |
| `/api/v1/profile/*` | User Service |
| `/api/v1/master-cv/*` | AI Service |
| `/api/v1/job/*` | AI Service |

Example route configuration:

```yaml
services:
  - name: user-service
    url: http://user-service:8000
    routes:
      - name: user-public
        paths:
          - /api/v1/auth

  - name: ai-service
    url: http://ai-service:8000
    routes:
      - name: ai-service-route
        paths:
          - /api/v1
```

---

# Public vs Protected Endpoints

Routes can be categorized as either **public** or **protected**.

## Public Endpoints

Public endpoints do not require user authentication.

Typical examples include:

| Endpoint | Description |
|----------|-------------|
| `POST /api/v1/auth/login` | User login |
| `POST /api/v1/auth/register` | User registration |
| `POST /api/v1/auth/forgot-password` | Password reset request |
| `POST /api/v1/auth/reset-password` | Reset password |

These endpoints are accessible without a JWT token.

---

## Protected Endpoints

Protected endpoints require a valid JWT access token.

Examples:

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/profile` | Get current profile |
| `PUT /api/v1/profile` | Update profile |
| `POST /api/v1/master-cv` | Upload resume |
| `DELETE /api/v1/master-cv/{id}` | Delete resume |

Request example:

```http
GET /api/v1/profile HTTP/1.1
Cookie: access_token=<jwt-access-token>
```

Kong extracts the JWT from the incoming HTTP cookie, validates the token, and forwards the request only if authentication succeeds. If the cookie is missing, expired, or contains an invalid token, Kong returns an authentication error without forwarding the request to the backend service.

---

# Routing Flow

The request lifecycle is as follows:

![System Architecture](/docs/images/routing-flow.png)

---

# Summary

- **Services** define backend applications.
- **Routes** determine which requests belong to each service.
- **Public endpoints** are accessible without authentication.
- **Protected endpoints** require a valid JWT and are authenticated by Kong before requests reach the backend.