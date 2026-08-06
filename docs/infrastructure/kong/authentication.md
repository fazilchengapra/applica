# Authentication

This document explains how authentication is handled by Kong Gateway in the Applica Backend.

---

# Overview

The Applica Backend uses **JWT (JSON Web Token)** for user authentication.

After a successful login, the backend issues a JWT and stores it in a **secure HTTP-only cookie**. Every protected request automatically includes this cookie, allowing Kong to authenticate the user before forwarding the request to the backend services.

```
Browser
    │
    │ Cookie: access_token=<JWT>
    ▼
Kong Gateway
    │
    ▼
Backend Service
```

---

# JWT Validation

Authentication is performed at the gateway layer.

For protected routes, Kong:

1. Reads the JWT from the incoming HTTP cookie.
2. Verifies the token signature.
3. Validates the expiration time.
4. Extracts user claims.
5. Optionally injects trusted user headers.
6. Forwards the request to the backend service.

If validation fails, the request is rejected immediately.

---

# Authentication Cookie

The JWT is transmitted using an HTTP-only cookie.

Example:

```http
Cookie: access_token=<jwt-token>
```

Using HTTP-only cookies provides several benefits:

- JavaScript cannot access the token.
- Reduces the risk of XSS token theft.
- Browsers automatically include the cookie with requests.
- No need to manually attach an Authorization header.

---

# Protected Routes

Protected routes require a valid JWT cookie.

Examples:

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/profile` | Get current profile |
| `PUT /api/v1/profile` | Update profile |
| `GET /api/v1/users/*` |  user identify api|
| `POST, PUT /api/v1/master-cv` | Upload, and Update CV |
| `DELETE /api/v1/master-cv/{id}` | Delete CV |

Example request:

```http
GET /api/v1/profile HTTP/1.1
Cookie: access_token=<jwt-token>
```

---

# Public Routes

Public routes do not require authentication.

Examples:

| Endpoint | Description |
|----------|-------------|
| `POST /api/v1/auth/login` | User login |
| `POST /api/v1/auth/register` | User registration |
| `POST /api/v1/auth/forgot-password` | Request password reset |
| `POST /api/v1/auth/reset-password` | Reset password |

These endpoints are accessible without a JWT cookie.

---

# Failure Responses

If authentication fails, Kong rejects the request before it reaches the backend service.

Common failure scenarios:

| Scenario | Response |
|----------|----------|
| Missing cookie | `401 Unauthorized` |
| Invalid JWT | `401 Unauthorized` |
| Expired JWT | `401 Unauthorized` |
| Invalid signature | `401 Unauthorized` |

Example response:

```http
HTTP/1.1 401 Unauthorized
Content-Type: application/json

{
  "message": "Unauthorized"
}
```

---

# Authentication Flow

```
                User Login
                     │
                     ▼
             User Service
                     │
         Generate JWT Access Token
                     │
                     ▼
     Set HTTP-only Cookie (access_token, refresh_toekn)
                     │
                     ▼
                 Browser
                     │
     Automatic Cookie on Every Request
                     │
                     ▼
              Kong Gateway
                     │
         Read JWT from Cookie
                     │
          Validate Signature
                     │
        Validate Expiration
                     │
      Extract User Information
                     │
                     ▼
            Backend Service
                     │
             Business Logic
                     │
                     ▼
                 Response
```

---

# Security Notes

- JWTs are stored in **HTTP-only cookies**.
- Authentication is performed by Kong before requests reach backend services.
- Backend services only process authenticated requests.
- User information can be propagated to backend services through trusted request headers injected by Kong.

---

# Summary

The Applica Backend uses cookie-based JWT authentication. Kong validates the JWT stored in the HTTP-only cookie for every protected request, rejects invalid requests at the gateway, and forwards only authenticated requests to the appropriate backend service.