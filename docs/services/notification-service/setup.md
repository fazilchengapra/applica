# Local Setup — notification_service

## Prerequisites

- Node.js 20+ (development image uses Node 22; prod build targets Node 20)
- Redis running (`REDIS_HOST` / `REDIS_PORT`, BullMQ on db 3, realtime on db 4)
- Environment variables — the service validates them with Zod in
  `src/config/env.ts`; copy `.env` and fill in values.

> `.env.example` is a starting point — populate the real values from
> `src/config/env.ts` (see table below). A reachable PostgreSQL
> `DATABASE_URL` is now **required**: it backs the in-app inbox, and
> `src/lib/prisma.ts` connects on boot.

## Steps

```bash
cd notification_service
npm install
npx prisma migrate deploy   # creates the notifications table
npm run dev                 # API server (ts-node-dev, port 8000)
```

`prisma migrate deploy` is not optional: the service connects to Prisma on boot
and every `/api/v1/notify` request queries the `notifications` table, so without
the migration the inbox returns 500s while email/SMS keeps working.

In a second terminal, run the BullMQ workers (required to actually send):

```bash
npm run start:worker
```

## Environment variables

| Variable | Purpose |
|---|---|
| `PORT` | HTTP port (default 3002; `.env` sets 8000) |
| `NODE_ENV` | `development` / `production` |
| `DATABASE_URL` | Prisma DSN for the in-app inbox table (**required**) |
| `GATEWAY_INTERNAL_SECRET` | Shared secret for internal routes and `X-Gateway-Secret` |
| `USER_SERVICE_URL` / `USER_SERVICE_TIMEOUT` | Upstream + timeout for dispatch workers |
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
`http://localhost:8000/api/v1/notify/...` (browser inbox) and
`http://localhost:8000/api/v1/notifications/internal/...` (service-to-service).

Run `npx prisma migrate deploy` once against the database before first use; it
is not part of the container start command.

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