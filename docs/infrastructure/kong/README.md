# Kong Gateway Documentation

explaining the over flow and what is the kong?, why it's used?, and the basic diagram.

## What is Kong?

Kong is an open-source API Gateway built on top of Nginx and OpenResty (Lua). It acts as a single entry point for all client requests before they reach your backend services.

Instead of exposing every microservice directly, Kong sits in front of them and provides centralized API management, security, traffic control, and observability.

Some of its core capabilities include:

- Request routing
- Authentication
- Rate limiting
- Request/response transformation
- Logging & monitoring
- Caching
- Custom plugins
- Load balancing
- SSL termination

---

## Why This Project Uses Kong

The Applica Backend follows a microservice architecture. As the number of services grows, exposing each service individually becomes difficult to manage.

Kong provides a centralized gateway that:

- Routes requests to the correct microservice
- Hides internal service architecture from clients
- Applies authentication consistently
- Enforces rate limits
- Injects common headers (such as User ID ,Correlation ID, and Gateway Secret)
- Collects logs and metrics
- Supports custom plugins written in Lua
- Makes future scaling easier

Without Kong:

```
Client
   │
   ├── User Service
   ├── AI Service
   ├── Payment Service
   └── Notification Service
```

With Kong:

```
                Client
                   │
                   ▼
          ┌─────────────────────┐
          │   Kong Gateway      │
          └─────────────────────┘
           │          │        │   
           ▼          ▼        ▼
    User Service AI Service Payment Service
```

---

## High-Level Architecture

```
                   Internet
                       │
                       ▼
               ┌────────────────┐
               │  Kong Gateway  │
               └────────────────┘
                     │
      ┌──────────────┼──────────────┐
      ▼              ▼              ▼
 User Service    AI Service    Future Services
      │              │
      ▼              ▼
 PostgreSQL      Redis / AI Models
```

Every incoming request passes through Kong before reaching the appropriate backend service.

---

## Documentation Goals

This documentation aims to explain:

- Why Kong is used
- How requests flow through the gateway
- Gateway configuration
- Service routing
- Plugin development
- Authentication flow
- Rate limiting
- Logging and monitoring
- Deployment practices
- Troubleshooting
