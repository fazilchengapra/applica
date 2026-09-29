# Internal API

Base path: `/internal/v1/users/`

These endpoints are **not** part of the public API. They are mounted on their own
prefix (not under `/api/v1/`) so Kong can keep them behind the
`internal-secret-auth` route without colliding with the admin-gated
`/api/v1/users` route, and they never accept a user session — only the shared
service-to-service secret.

The only caller today is the `ai_service` home BFF (`GET /api/ai/v1/home`).

## Authentication

| Header | Value |
|---|---|
| `X-Internal-Secret` | The platform shared secret (`GATEWAY_INTERNAL_SECRET`) |

Two independent checks run on every request: Kong's `internal-secret-auth`
plugin rejects a bad secret with `401`, and `InternalSecretPermission` re-checks
it inside Django (constant-time compare) so a request that somehow bypasses the
gateway is still refused. The `X-Internal-Service` header Kong stamps is
informational; it is not what the permission trusts.

> Because internal requests do not go through JWT auth, the secret is effectively
> a bearer credential for the whole user table. It must stay in sync with
> `kong/.env` and every calling service, and must never be exposed to a browser.

## Endpoints

| Method | Path | Summary |
|---|---|---|
| GET | `/home/{user_id}/` | Account aggregate for the home screen |

---

## Home account

`GET /home/{user_id}/`

Returns everything about an account that the home screen needs, in one query
batch. The caller passes the user id it already trusts (it comes from Kong's
`X-User-Id`), so there is no id-or-you authorization check here — access control
is the secret plus the gateway.

The payload is intentionally flat and does **not** include a percent or a fifth
step: `ai_service` owns the master CV, so it computes `upload_cv` locally and
composes `onboarding.percent` from the flags below. That keeps the ring and the
step list from ever disagreeing.

**Response `200`**

```json
{
  "user": {
    "id": 1,
    "email": "user@example.com",
    "phone_number": "+15551234567",
    "is_email_verified": true,
    "is_phone_verified": false,
    "date_joined": "2026-01-01T00:00:00Z",
    "last_login": "2026-02-01T10:00:00Z",
    "is_staff": false,
    "roles": ["user"]
  },
  "profile": {
    "display_name": "string",
    "avatar_url": "https://...",
    "bio": "string",
    "country": "string",
    "city": "string",
    "timezone": "string",
    "locale": "string"
  },
  "account_steps": {
    "verify_email": true,
    "verify_phone": false,
    "add_photo": true,
    "complete_profile": false
  },
  "notifications": { "unread": 3 },
  "linked_accounts": [
    {
      "provider": "google",
      "is_verified": true,
      "is_active": true,
      "linked_at": "2026-01-01T00:00:00Z"
    }
  ]
}
```

**Responses**

| Status | Meaning |
|---|---|
| 200 | Account aggregate returned |
| 401 | Missing or invalid `X-Internal-Secret` |
| 404 | No user with that id (the id is the path parameter, so it is a real 404, not a leak) |

### Field notes

- `roles` is derived, not stored. `is_staff` yields `staff`, and a user with no
  other signal is `user`. It comes from the shared `get_user_roles` helper, the
  same one the auth flows use, so the home screen and the token can never report
  different roles.
- `profile` fields are returned as blank strings (not `null`) when unset, so the
  consumer can render directly.
- `complete_profile` is true only when `display_name`, `bio`, `country` and
  `city` are all non-blank.
- `add_photo` is true when `profile.avatar_url` is set.
- `notifications.unread` counts in-app notifications (`Notification` rows with
  `read_at` null). It is computed here because the rows live in this service;
  `notification_service` only dispatches and has nothing to count.
- `linked_accounts` comes from the auth provider links, so a Google-only user
  gets one entry and an email-only user gets an empty list.
