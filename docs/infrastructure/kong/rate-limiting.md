# Rate Limiting

This document explains how rate limiting is implemented in the Applica Backend using Kong Gateway.

---

# Overview

Rate limiting controls how many requests a client can send within a specified time period.

Instead of implementing request throttling inside every backend service, Kong applies rate limits at the gateway before forwarding requests.

```
              Client
                 │
                 ▼
          Kong Gateway
                 │
        Rate Limiting Plugin
          │              │
      Allowed        Rate Limited
          │              │
          ▼              ▼
   Backend Service   HTTP 429
```

---

# Why Rate Limiting Exists

Rate limiting protects the platform from excessive or abusive traffic.

Benefits include:

- Prevents API abuse
- Protects backend services from overload
- Reduces denial-of-service (DoS) attacks
- Prevents accidental request floods
- Ensures fair resource usage
- Improves overall system stability

Without rate limiting, a client could continuously send requests and consume excessive server resources.

---

# Current Implementation

The Applica Backend currently uses Kong's built-in **Rate Limiting** plugin.

Requests are limited based on the **client IP address** before authentication reaches the backend services.

This approach is particularly useful for protecting public endpoints such as:

- Login
- Registration
- Password reset
- Email verification

---

# Plugin Configuration

Example configuration:

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

Configuration options:

| Option | Description |
|---------|-------------|
| `minute` | Maximum requests allowed per minute |
| `policy` | Storage policy for request counters (`redis`) |
| `limit_by` | Limits requests by client IP |
| `hide_client_headers` | Includes rate limit headers in responses when `false` |

---

# IP-Based Limiting

The current implementation identifies clients using their IP address.

Example:

```
Client IP
192.168.1.25
      │
      ▼
10 Requests / Minute
```

Request flow:

```
Request #1
✔ Allowed

Request #5
✔ Allowed

Request #10
✔ Allowed

Request #11
✘ HTTP 429
```

This strategy is simple and effective for protecting unauthenticated endpoints.

---

# Future Consumer-Based Limiting

As the platform evolves, rate limiting can be applied to authenticated users instead of IP addresses.

Possible implementations include:

- Kong Consumers
- User ID extracted from a validated JWT
- Subscription-based limits (Free vs Premium)

Example:

| User Type | Request Limit |
|-----------|--------------:|
| Free User | 100 requests/hour |
| Premium User | 1000 requests/hour |
| Administrator | Custom or unlimited |

Consumer-based limiting ensures that multiple users behind the same IP address do not affect each other's quotas.

---

# Response Headers

When response headers are enabled, Kong includes information about the current rate limit.

Example:

```http
RateLimit-Limit: 10
RateLimit-Remaining: 4
RateLimit-Reset: 35
```

Header descriptions:

| Header | Description |
|---------|-------------|
| `RateLimit-Limit` | Maximum requests allowed during the current window |
| `RateLimit-Remaining` | Remaining requests before the limit is reached |
| `RateLimit-Reset` | Seconds until the current rate limit window resets |

These headers help API clients manage their request rate and avoid unnecessary failures.

---

# HTTP 429 Example

When the configured limit is exceeded, Kong rejects the request before forwarding it to the backend.

Example response:

```http
HTTP/1.1 429 Too Many Requests
Content-Type: application/json

{
    "message": "API rate limit exceeded"
}
```

The backend service is never invoked.

---

# Request Flow

```
               Client
                  │
                  ▼
           Kong Gateway
                  │
        Rate Limiting Plugin
          │              │
      Within Limit    Limit Exceeded
          │              │
          ▼              ▼
   Backend Service   HTTP 429 Response
```

---

# Summary

The Applica Backend currently uses Kong's built-in Rate Limiting plugin to enforce **IP-based request limits**. Requests exceeding the configured threshold receive an **HTTP 429 (Too Many Requests)** response before reaching backend services. The architecture is designed to support future migration to **user- or consumer-based rate limiting** for more granular control.