# Local Setup — notification_service

## Prerequisites

- Node.js 20+ (development image uses Node 22; prod build targets Node 20)
- Redis running (`REDIS_HOST` / `REDIS_PORT`, BullMQ on db 3, realtime on db 4)
- Environment variables — the service validates them with Zod in
  `src/config/env.ts`; copy `.env` and fill in values.

> `.env.example` is currently **empty** — populate from `src/config/env.ts`
> (see table below). A PostgreSQL `DATABASE_URL` is required by the Prisma
> schema but is **not used at runtime** (no `PrismaClient` is imported).

## Steps

```bash
cd notification_service
npm install
npm run dev          # API server (ts-node-dev, port 8000)
```

In a second terminal, run the BullMQ workers (required to actually send):

```bash
npm run start:worker
```

## Environment variables

| Variable | Purpose |
|---|---|
| `PORT` | HTTP port (default 3002; `.env` sets 8000) |
| `NODE_ENV` | `development` / `production` |
| `DATABASE_URL` | Prisma DSN (configured only; unused at runtime) |
| `GMAIL_USER` / `GMAIL_APP_PASSWORD` | Nodemailer Gmail credentials |
| `REDIS_HOST` / `REDIS_PORT` | Redis connection |
| `TWILIO_FROM_NUMBER` / `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` | SMS delivery |
| `FRONTEND_URL` | Used to build forgot-password links |

## Running via Docker

```bash
docker compose up --build notification_service notification-worker
```

`target: development` in compose runs `npm run dev`; the worker container runs
`npm run start:worker`. The API is reachable through Kong at
`http://localhost:8000/api/v1/notifications/...`.

## Sending a test dispatch

```bash
curl -s http://localhost:8000/health   # expect {"status":"ok too help"}

# dispatch (through Kong) — needs the internal service header Kong injects
curl -s -X POST http://localhost:8000/api/v1/notifications/internal/dispatch \
  -H 'Content-Type: application/json' \
  -H 'X-Internal-Service: notification-dispatcher' \
  -d '{"eventType":"account.user_registered","email":"...","firstName":"Test"}'
```

## Tests

None exist yet (`tests/` is empty). Test libraries (`vitest`, `supertest`,
`chai`, `fast-check`) are installed but not wired — see the
[testing guide](../../guides/testing.md).