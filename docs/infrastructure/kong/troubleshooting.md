# Troubleshooting

This document lists common issues that may occur while developing or deploying the Applica Backend with Kong Gateway.

For each issue, the document describes:

- Symptoms
- Possible causes
- Recommended solutions

---

# 401 Unauthorized

## Symptoms

- Protected endpoints return `401 Unauthorized`
- Request never reaches the backend service

Example:

```http
HTTP/1.1 401 Unauthorized
```

## Possible Causes

- Missing authentication cookie
- Expired JWT
- Invalid JWT signature
- Incorrect JWT secret
- Authentication plugin failure
- Authentication plugin not attached to the route

## Solutions

- Verify the `access_token` cookie is present.
- Check whether the JWT has expired.
- Ensure the authentication plugin is enabled on the protected route.
- Verify the JWT signing secret.
- Inspect Kong logs for authentication plugin errors.

---

# 429 Too Many Requests

## Symptoms

```http
HTTP/1.1 429 Too Many Requests
```

## Possible Causes

- Client exceeded the configured request limit
- Rate limiting plugin configured with a very small limit
- Repeated testing from the same IP address

## Solutions

- Wait until the rate limit window resets.
- Check the plugin configuration.
- Verify response headers:

```http
RateLimit-Limit
RateLimit-Remaining
RateLimit-Reset
```

---

# Plugin Not Loading

## Symptoms

- Kong starts successfully
- Plugin cannot be enabled
- Error:

```
plugin '<plugin-name>' not enabled
```

## Possible Causes

- Plugin directory not mounted
- Plugin missing from `KONG_PLUGINS`
- Lua files missing
- Invalid plugin structure

## Solutions

Verify:

```
kong/plugins/
    plugin-name/
        handler.lua
        schema.lua
```

Ensure the environment variable includes the plugin:

```env
KONG_PLUGINS=bundled,plugin-name
```

Restart Kong after making changes.

---

# Kong Configuration Not Updating

## Symptoms

Changes to `kong.yml` have no effect.

## Possible Causes

- Kong container not restarted
- Incorrect declarative configuration path
- Docker volume not updated
- YAML syntax error

## Solutions

Validate the configuration:

```bash
kong config parse kong.yml
```

Restart the container:

```bash
docker compose restart kong
```

If necessary:

```bash
docker compose down
docker compose up --build
```

---

# Lua Errors

## Symptoms

Kong logs display Lua runtime errors.

Example:

```
attempt to index a nil value
```

or

```
module not found
```

## Possible Causes

- Invalid Lua syntax
- Missing required module
- Nil value access
- Incorrect import path

## Solutions

- Check Kong container logs.
- Verify all required files exist.
- Validate Lua syntax.
- Ensure plugin files are mounted correctly.

---

# JWT Validation Failures

## Symptoms

Protected endpoints consistently return `401 Unauthorized`.

## Possible Causes

- Missing cookie
- Invalid JWT
- Expired token
- Signature mismatch
- Incorrect cookie name

## Solutions

Verify the request contains:

```http
Cookie: access_token=<jwt-token>
```

Confirm:

- Token has not expired
- Signing secret is correct
- Cookie name matches the authentication plugin configuration

---

# Route Not Matched

## Symptoms

```http
HTTP/1.1 404 Not Found
```

## Possible Causes

- Route path not configured
- Incorrect HTTP method
- Typographical error in the request path
- Request sent to the wrong host

## Solutions

Check:

- Route paths in `kong.yml`
- HTTP method
- Service configuration
- Route configuration

Example:

```yaml
routes:
  - paths:
      - /api/v1/auth
```

---

# Service Unreachable

## Symptoms

```http
HTTP/1.1 503 Service Unavailable
```

## Possible Causes

- Backend container stopped
- Incorrect service URL
- Wrong port
- DNS resolution failure

## Solutions

Verify:

```bash
docker compose ps
```

Test connectivity:

```bash
docker compose exec kong ping user-service
```

Confirm the service URL:

```yaml
url: http://user-service:8000
```

---

# Docker Networking Issues

## Symptoms

Kong cannot communicate with backend services.

Example errors:

```
connection refused
```

or

```
host not found
```

## Possible Causes

- Containers are on different Docker networks
- Service name incorrect
- Backend container not running

## Solutions

Verify the network:

```bash
docker network ls
```

Inspect the network:

```bash
docker network inspect <network-name>
```

Confirm all containers are attached to the same network.

---

# Correlation ID Missing

## Symptoms

Backend logs do not include a request identifier.

## Possible Causes

- Correlation ID plugin disabled
- Header not forwarded
- Backend not logging the header

## Solutions

- Verify the correlation ID plugin is enabled.
- Confirm the `X-Request-Id` header reaches the backend.
- Include the header in application logs.

---

# Useful Debug Commands

Check Kong logs:

```bash
docker compose logs kong
```

Follow logs in real time:

```bash
docker compose logs -f kong
```

View running containers:

```bash
docker compose ps
```

Validate Kong configuration:

```bash
kong config parse kong.yml
```

Inspect Docker networks:

```bash
docker network inspect <network-name>
```

---

# Summary

Most gateway issues fall into one of these categories:

| Problem | Typical HTTP Status |
|----------|--------------------:|
| Invalid JWT | 401 |
| Missing Authentication | 401 |
| Rate Limit Exceeded | 429 |
| Route Not Found | 404 |
| Backend Service Unavailable | 503 |
| Plugin Loading Failure | Startup Error |
| Docker Networking Issue | 503 / Connection Error |
| Invalid Kong Configuration | Startup Error |

When troubleshooting, start by checking:

1. Kong logs
2. Plugin configuration
3. Route configuration
4. Backend service availability
5. Docker networking
6. Authentication cookies
7. Rate limiting configuration