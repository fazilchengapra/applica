# Authentication API

Base path: `/api/v1/auth/`

Session is cookie-based: successful login/refresh sets **HttpOnly** `access`
and `refresh` cookies on the response. Endpoints marked "No" under Auth are
public (`security: []` in the spec — no cookie required).

## Endpoints

| Method | Path | Summary | Auth required |
|---|---|---|---|
| POST | `/email/login/` | Login with email | No |
| POST | `/email/verify/` | Verify email | No |
| POST | `/email/verify/request/` | Request email verification | No |
| POST | `/email/change/request/` | Request email change | Yes |
| POST | `/email/change/confirm/` | Confirm email change | Yes |
| POST | `/phone/login/request/` | Request login OTP | No |
| POST | `/phone/login/verify/` | Verify login OTP | No |
| POST | `/phone/add/` | Add phone number | Yes |
| POST | `/phone/otp/request/` | Request phone verification OTP | Yes |
| POST | `/phone/otp/verify/` | Verify phone number | Yes |
| POST | `/phone/change/request/` | Request phone number change | Yes |
| POST | `/phone/change/verify/` | Verify phone number change | Yes |
| POST | `/password/change/` | Change password | Yes |
| POST | `/password/forgot/` | Forgot password | No |
| POST | `/password/reset/` | Reset password | No |
| POST | `/token/refresh/` | Refresh access token | No (reads refresh cookie) |
| POST | `/logout/` | Logout | Yes |
| POST | `/google/` | Google auth | No |

---

## Email login

`POST /email/login/`

Authenticates via email/password and sets HttpOnly access/refresh cookies on success.

**Request**
```json
{
  "email": "user@example.com",
  "password": "string (min 4 chars)"
}
```

**Responses**
| Status | Meaning |
|---|---|
| 200 | Login successful. Auth cookies set on the response. |
| 400 | Validation error or invalid credentials. |
| 403 | Account or email is inactive. |

---

## Email verification

`POST /email/verify/`
Confirms email ownership using the token sent to the user's email address.

**Request:** `{ "token": "string" }`

| Status | Meaning |
|---|---|
| 200 | Email verified successfully. |
| 400 | Validation error, or token invalid/expired. |

`POST /email/verify/request/`
Requests a verification email for the given address.

**Request:** `{ "email": "string" }`

| Status | Meaning |
|---|---|
| 200 | Verification email sent. |
| 400 | Validation error, or email already verified. |
| 404 | No user found with this email. |
| 429 | Cooldown in effect — too many requests recently. |
| 500 | Unexpected server error. |

---

## Email change (dual-confirmation)

Both the **old** and **new** email addresses must independently confirm via
their own token before the change is finalized.

`POST /email/change/request/`
Sends a verification token to both current and new addresses.

**Request:** `{ "new_email": "string (email)" }`

| Status | Meaning |
|---|---|
| 200 | Verification codes sent to both addresses. |
| 400 | Request could not be processed. |
| 429 | Cooldown in effect. |

`POST /email/change/confirm/`
Confirms one side of the flow.

**Request:** `{ "token": "string" }`

| Status | Meaning |
|---|---|
| 200 | Accepted — may be fully complete or still awaiting the other side. |
| 400 | Token invalid/expired, or new email already in use. |

---

## Phone login (OTP)

`POST /phone/login/request/`
Sends a login OTP to the given phone number, if registered and verified.

**Request:** `{ "phone_number": "string" }`

| Status | Meaning |
|---|---|
| 200 | Generic success — returned even if number isn't registered. |
| 400 | Number not registered, or phone not yet verified. |
| 429 | Cooldown in effect. |

`POST /phone/login/verify/`
Verifies a phone login OTP and logs the user in (sets auth cookies).

**Request:** `{ "phone_number": "string", "code": "string (6 chars)" }`

| Status | Meaning |
|---|---|
| 200 | OTP verified, login successful, cookies set. |
| 400 | OTP invalid, or account inactive. |
| 429 | Too many failed attempts — OTP locked. |

---

## Phone number management (authenticated)

`POST /phone/add/`
Adds/replaces the authenticated user's phone number, pending verification.

**Request:** `{ "phone_number": "string" }`

| Status | Meaning |
|---|---|
| 200 | Phone number added successfully. |
| 400 | Invalid, already in use, or same as current. |
| 401 | Phone already verified on this account. |

`POST /phone/otp/request/`
Sends an OTP to the authenticated user's registered phone for verification.

| Status | Meaning |
|---|---|
| 200 | OTP sent. |
| 400 | Phone already verified. |
| 429 | Cooldown in effect. |

`POST /phone/otp/verify/`
Verifies the authenticated user's phone using an OTP code.

**Request:** `{ "code": "string (6 chars)" }`

| Status | Meaning |
|---|---|
| 200 | Phone number verified. |
| 400 | OTP invalid or expired. |
| 429 | Too many failed attempts — OTP locked. |

---

## Phone change (dual-confirmation)

`POST /phone/change/request/`
Sends an OTP to both current and new phone numbers.

**Request:** `{ "new_phone_number": "string" }`

| Status | Meaning |
|---|---|
| 200 | Codes sent to both numbers. |
| 400 | Same number, invalid request, or current phone not verified. |
| 409 | New phone number already in use by another account. |
| 429 | Cooldown in effect. |

`POST /phone/change/verify/`
Confirms the change by verifying OTP codes sent to both numbers.

**Request:** `{ "old_code": "string (6 chars)", "new_code": "string (6 chars)" }`

| Status | Meaning |
|---|---|
| 200 | Phone number updated. |
| 400 | One or both codes invalid/expired. |
| 429 | Too many failed attempts — OTP locked. |

---

## Password management

`POST /password/change/` (authenticated)
Requires correct old password and a matching new/confirm pair.

**Request:**
```json
{
  "old_password": "string (min 4)",
  "new_password": "string (min 4)",
  "confirm_password": "string (min 4)"
}
```

| Status | Meaning |
|---|---|
| 200 | Password changed. |
| 400 | Validation error, mismatch, or incorrect old password. |

`POST /password/forgot/`
Requests a password reset link.

**Request:** `{ "email": "string" }`

| Status | Meaning |
|---|---|
| 200 | Generic success — returned even if email doesn't match an account. |
| 400 | Account not found, or email not verified. |

`POST /password/reset/`
Resets password using the token from the forgot-password flow.

**Request:**
```json
{
  "token": "string",
  "new_password": "string (min 4)",
  "confirm_password": "string (min 4)"
}
```

| Status | Meaning |
|---|---|
| 200 | Password reset. |
| 400 | Token invalid/expired, or password fails validation. |

---

## Session

`POST /token/refresh/`
Issues a new access token using the refresh token from the **HttpOnly cookie**
(not the request body).

| Status | Meaning |
|---|---|
| 200 | New access cookie set. |
| 401 | Refresh cookie missing, invalid, or expired. |

`POST /logout/`
Blacklists the refresh token if present/valid, then clears auth cookies.
Always returns 200, even if the refresh token was already expired or missing.

`POST /google/`
Google OAuth login. *(Spec has no request/response schema documented yet —
add once the flow is finalized.)*

---

## Rate limiting / cooldowns

Several endpoints return `429` with a cooldown in effect: email verify
request, email change request, phone login request, phone OTP request, phone
change request. Document the actual cooldown windows and lockout thresholds
here (not present in the OpenAPI spec — pull from the service-layer code).
