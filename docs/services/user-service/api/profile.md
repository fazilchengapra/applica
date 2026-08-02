# Profile API

Base path: `/api/v1/profiles/`

Extended profile data for the authenticated user — separate from the core
account fields owned by the `users` app.

## Endpoints

| Method | Path | Summary | Auth required |
|---|---|---|---|
| GET | `/me/` | Get profile | Yes |
| PATCH | `/` | Update profile | Yes |

---

## Get profile

`GET /me/`

Retrieves the authenticated user's profile.

**Response `200`**
```json
{
  "first_name": "string",
  "last_name": "string",
  "display_name": "string",
  "avatar_url": "https://...",
  "bio": "string",
  "date_of_birth": "1999-01-01",
  "gender": "male | female | other | prefer_not_to_say | \"\"",
  "country": "string",
  "city": "string",
  "timezone": "string",
  "locale": "en-US",
  "email": "user@example.com",
  "phone_number": "string",
  "is_email_verified": true,
  "is_phone_verified": false
}
```

`display_name`, `avatar_url`, `email`, `phone_number`, `is_email_verified`,
`is_phone_verified` are **read-only** — set/changed via the `users` or
`authentication` APIs, not here.

| Status | Meaning |
|---|---|
| 200 | Profile returned. |
| 404 | Profile not found for the authenticated user. |

---

## Update profile

`PATCH /`

Partially updates the authenticated user's profile. Only provided fields are
changed.

**Request** (all fields optional)
```json
{
  "first_name": "string (max 150)",
  "last_name": "string (max 150)",
  "bio": "string (max 500)",
  "date_of_birth": "YYYY-MM-DD | null",
  "gender": "male | female | other | prefer_not_to_say | \"\"",
  "country": "string (max 100)",
  "city": "string (max 100)",
  "timezone": "string (max 50)",
  "locale": "string (max 10, e.g. en-US)"
}
```

**Response `200`:** full updated `Profile` object (see [Get profile](#get-profile)).

| Status | Meaning |
|---|---|
| 200 | Profile updated. |
| 404 | Profile not found for the authenticated user. |

> Note: `PATCH /` (no `/me/` suffix) — different path shape from `GET`. Worth
> flagging in a review; if intentional, call it out here so it isn't
> "fixed" by mistake later.

---

## Field notes

- `display_name` — public-facing name, falls back to `first_name` if unset.
- `avatar_url` — read-only here; check whether avatar upload is handled by
  this app or elsewhere (not present in this spec — likely a separate
  endpoint using Cloudinary, per the stack notes).
