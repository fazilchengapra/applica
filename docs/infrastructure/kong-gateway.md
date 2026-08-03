# Kong API Gateway

## Config

Declarative config (`kong:3.9`) — link to the actual config file location in
the repo.

## Routes

| Path prefix | Upstream service |
|---|---|
| `/api/auth/*`, `/api/users/*`, etc | user-service |
| `/api/ai/*` | ai-service |

## Plugins enabled

- CORS
- correlation-id

Document config specifics for each (limits, allowed origins) here.