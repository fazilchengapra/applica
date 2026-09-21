# Notifications App

## Purpose

Sends and tracks in-app notifications, pushes them to users in realtime over a
WebSocket, and publishes typed events to AWS SNS for downstream services
(analytics, notification delivery, search indexing).

## Endpoints

| Method | Path | Description | Auth |
|---|---|---|---|
| POST | `/api/v1/notify/push/` | Internal: create an in-app notification + push over WebSocket. Requires `X-Internal-Secret` header | `X-Internal-Secret` (internal) |

> There is no public REST endpoint for listing/marking-notifications read yet —
> reading happens over the WebSocket. The in-process `notifications.services`
> entrypoints (`create_and_push` and per-event wrappers) are the intended
> internal API (see `app/apps/notifications/services/`).

## Realtime / WebSocket

- Path: `ws/notifications/` (via Kong, or directly on Daphne ASGI)
- Consumer: `NotificationConsumer` (`app/apps/notifications/consumers.py`)
- Auth: JWT from the `access_token` cookie (`JWTAuthMiddleware` in
  `app/apps/common/middleware.py`), messages grouped by `user_<id>`
- Payloads carry `type`, `title`, `body`, `metadata`, `created_at`

## Channels

| Channel | Mechanism | Status |
|---|---|---|
| In-app | `notifications` table + WebSocket push | Implemented |
| Email / SMS | Dispatched to `notification_service` via `/api/v1/notify/push/` → Kong → internal dispatch; SNS publishing also exists | Implemented via dispatch + SNS |
| Push (mobile) | Only SNS event publishing; no FCM/APNs provider wired | Partial |

## Business rules / edge cases

- Notification failures are caught at the call site so a failed notification
  never turns a successful business operation into a 500 (per schema docs).
- PII in `metadata` is masked at this service layer.
- Notification IDs are UUIDs (client-referenced, avoid enumeration).

## Model

Table `notifications`: `id` (uuid PK), `user` FK, `type` (dot-namespaced e.g.
`account.password_changed`), `title`, `body`, `metadata` (JSON), `read_at`,
`created_at`. Index on `(user, read_at, created_at)`.

## Publishing to SNS

`app/apps/notifications/publishers/sns_publisher.py` publishes typed events
with `eventType` / `channel` attributes to `SNS_NOTIFICATIONS_TOPIC_ARN`.

## Dependencies

- Called by `authentication` flows (registration, password reset, phone OTP)
- Consumed by `notification_service` (Node) and analytics
- Requires Redis (Channels layer) and AWS SNS config