# Users API

Base path: `/api/v1/users/`

Core user account: registration, and the authenticated user's own account
details/deletion.

## Endpoints

| Method | Path | Summary | Auth required |
|---|---|---|---|
| POST | `/` | Register user | No |
| GET | `/me/` | Get current user | Yes |
| DELETE | `/me/` | Delete account | Yes |

---

## Register user

`POST /`

Registers a new user account and sends an email verification link.

**Request**
```json
{
  "first_name": "string (max 150)",
  "last_name": "string (max 150, optional)",
  "email": "string (email)",
  "phone_number": "string (max 20)",
  "password": "string (min 4)",
  "confirm_password": "string"
}
```

**Responses**
| Status | Meaning |
|---|---|
| 201 | User registered. Verification link sent to email. |
| 400 | Validation error in submitted data. |
| 409 | A user with this email or phone number already exists. |

---

## Get current user

`GET /me/`

Retrieves the authenticated user's own account details.

**Response `200`**
```json
{
  "id": 1,
  "email": "user@example.com",
  "phone_number": "string | null",
  "is_email_verified": true,
  "is_phone_verified": false,
  "date_joined": "2026-01-01T00:00:00Z",
  "profile": {
    "first_name": "string",
    "last_name": "string",
    "avatar_url": "https://..."
  }
}
```

---

## Delete account (soft-delete)

`DELETE /me/`

Soft-deletes the authenticated user's account: requires password confirmation,
sets `deactivated_at`, blacklists outstanding refresh tokens (`revoke_all_tokens_task`),
and clears auth cookies.

| Status | Meaning |
|---|---|
| 204 | Account deactivated (soft-delete). Auth cookies cleared. |
| 400 | Validation error, or incorrect password. |

> `DeactivatedAt` distinguishes "user paused their account" from Django's
> `is_active` (admin disabled). The row is not hard-deleted.

---

## Relationship to other apps

- `authentication` — registration triggers the email verification flow owned
  by that app.
- `profile` — every user has a 1:1 `profile`, exposed nested under `me.profile`
  here and managed independently via the [profile API](./profile.md).
