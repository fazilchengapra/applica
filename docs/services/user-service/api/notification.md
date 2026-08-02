# Notification

## Purpose

Sends and tracks email / push / in-app notifications triggered by other apps.

## Endpoints

| Method | Path | Description | Auth required |
|---|---|---|---|
| GET | `/api/notifications/` | List current user's notifications | Yes |
| PATCH | `/api/notifications/{id}/read/` | Mark as read | Yes |
| POST | `/api/notifications/preferences/` | Update notification preferences | Yes |

## Channels supported

- Email
- Push
- In-app

## Business rules / edge cases

- Rate limiting / batching (don't spam users)
- Preference opt-outs per channel

## Dependencies

- Called internally by `authentication` (OTP), `task_monitoring` (completion),
  and potentially `ai-service`
