# Architecture

This document explains how Kong Gateway fits into the Applica Backend architecture, its responsibilities, request flow, and how it is configured.

---

# Overview

Applica Backend follows a **microservice architecture**. Instead of clients communicating directly with each service, every request first reaches **Kong Gateway**.

Kong acts as the single entry point into the system.

![System Architecture](/docs/images/architecture.png)

This approach centralizes networking, security, and traffic management while allowing each service to focus only on business logic.

---

# Gateway Responsibilities

Kong is responsible for handling concerns that should be shared across all services.

Its primary responsibilities include:

## 1. Request Routing

Routes incoming HTTP requests to the appropriate backend service based on the configured routes.

Example:

```
/api/v1/users/*  ─────► User Service
/api/v1/auth/*  ─────► User Service
/api/v1/profile/*  ─────► User Service

/api/v1/ai/*     ─────► AI Service
```

---

## 2. Authentication

Validates incoming authentication tokens before forwarding requests.

Examples include:

- JWT validation

This prevents every microservice from implementing the same authentication logic.

---

## 3. Rate Limiting

Protects backend services from abuse by limiting request rates.

Example:

```
Login API

5 requests / minute / IP
```

---

## 4. Request Transformation

Can modify requests before forwarding them.

Examples:

- Add headers
- Remove headers
- Rewrite paths
- Normalize requests

---

## 5. Response Transformation

Can modify responses returned from backend services.

Examples:

- Remove sensitive headers
- Add security headers
- Standardize response metadata

---

## 6. Logging & Monitoring

Records request information for debugging and observability.

Typical data includes:

- Request path
- Status code
- Latency
- Client IP
- Correlation ID

---

## 7. Plugin Execution

Runs built-in or custom plugins before and after requests reach backend services.

Examples:

- Rate limiting
- CORS
- JWT
- Custom Lua plugins

---

# Which Requests Pass Through Kong

All external client requests should enter the system through Kong.

```
Client
   │
   ▼
Kong Gateway
   │
   ▼
Backend Services
```

Typical requests include:

```
POST /api/v1/auth/token/refresh/

POST /api/v1/auth/logout/

POST /api/v1/auth/email/verify/

POST /api/v1/auth/email/verify/request/

POST /api/v1/auth/email/login/

POST /api/v1/auth/phone/login/request/

POST /api/v1/auth/phone/login/verify/

POST /api/v1/auth/password/forgot/

POST /api/v1/auth/password/reset/

POST /api/v1/auth/google/

POST, GET /api/v1/auth/users/

PATCH, GET /api/v1/auth/profile/
```

---

# Existing Services

Current architecture consists of the following services.

## User Service

Responsible for:

- User registration
- Login
- Profile management
- Account settings
- Authentication-related operations

---

## AI Service

Responsible for:

- CV parsing
- Resume optimization
- AI-powered processing
- Future AI features

---

## Future Services

The architecture is designed to support additional services such as:

- Community Service

Adding a new service generally requires creating a Kong Service and Route configuration without affecting existing services.

---

# DB-less Configuration

This project uses Kong in **DB-less mode**.

Instead of storing configuration in a database, Kong loads everything from a declarative YAML file during startup.

Example:

```
kong.yml
```

This file contains:

- Services
- Routes
- Plugins
- Consumers

Benefits include:

- Configuration stored in Git
- Easy code reviews
- Reproducible environments
- Faster startup
- No external database dependency
- Simple deployments with Docker

Typical startup flow:

```
Docker starts Kong
        │
        ▼
Load kong.yml
        │
        ▼
Create Services
Create Routes
Create Plugins
        │
        ▼
Ready to accept requests
```

---

# Request Lifecycle

A typical request follows this path:

```
Client
   │
   ▼
Kong Gateway
   │
   ├── Match Route
   ├── Execute Plugins
   ├── Forward Request
   ▼
Backend Service
   │
Business Logic
   │
Response
   ▼
Kong Gateway
   │
Execute Response Plugins
   ▼
Client
```

---

# Plugin Execution Order

For every request, Kong executes plugins at different stages of the request lifecycle.

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
Custom Request Plugins
       │
       ▼
Forward Request
       │
       ▼
Backend Service
       │
       ▼
Receive Response
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

Custom Lua plugins participate in this lifecycle by implementing one or more execution phases such as:

- `rewrite`
- `access`
- `header_filter`
- `body_filter`
- `log`

The exact phase(s) depend on the plugin's implementation and determine when it runs during request processing.

---

# Benefits of This Architecture

Using Kong provides several advantages:

- Single entry point for all APIs
- Centralized authentication and authorization
- Consistent rate limiting
- Simplified routing
- Reduced duplication across services
- Easy integration of custom plugins
- Better observability
- Scalable microservice architecture
- Version-controlled gateway configuration

---

# Summary

In the Applica Backend architecture, Kong serves as the API Gateway for all external traffic. It routes requests to the appropriate microservice, applies shared policies through plugins, and uses a declarative DB-less configuration to keep gateway management simple, reproducible, and version-controlled.