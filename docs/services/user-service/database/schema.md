# Database Schema — user-service

## Overview

One PostgreSQL database (`applica_db`), owned exclusively by `user_service`.
No other service should read/write these tables directly — go through the API.

Cross-service references (e.g. `ai_service`'s `master_cvs.user_id`) are stored as
plain integers/uuids, never as real foreign keys. Each service owns its own database —
see the note on `master_cvs` at the bottom of this doc.

## Core tables

| Table | App | Notes |
|---|---|---|
| `users` | `users` | Custom `AbstractUser`, email as `USERNAME_FIELD`, UUID-free (bigint PK) |
| `auth_methods` | `authentication` | One row per login method linked to a user (email, phone, Google, ...) |
| `verification_tokens` | `authentication` | One-time tokens for email/phone verification, password reset, etc. |
| `profiles` | `profiles` | 1:1 with `users`; all human-facing identity data lives here, not on `users` |
| `master_cvs` | *(external — `ai_service`)* | Shown for reference only; not part of this database |

## Diagram

*[View live diagram on dbdiagram.io](https://dbdiagram.io/d/applica-696086aed6e030a0248899be)*

---

## `users`

The auth identity table. Deliberately thin — no name, avatar, or profile data lives
here. That's a conscious split: `users` is "can this person log in and what can
they do," `profiles` is "who is this person."

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `id` | bigint | PK | Auto-incrementing bigint, not UUID — this is the internal identity anchor other tables FK against directly within this DB. |
| `email` | varchar(254) | NN, unique | `USERNAME_FIELD`. Used for login and as the primary contact channel. |
| `phone_number` | varchar(20) | | Optional. Enables phone OTP login once verified. |
| `is_active` | boolean | NN | Django's standard "can this account authenticate" flag. Distinct from `deactivated_at` — see below. |
| `is_staff` | boolean | NN | Django admin access flag. |
| `is_email_verified` | boolean | NN | Set true once the user completes email verification via `verification_tokens`. |
| `is_phone_verified` | boolean | NN | Set true once the user completes phone OTP verification. |
| `password` | varchar(255) | | Django's salted-hash password field. Null-able because OAuth-only users (Google) never set one. |
| `last_login` | timestamp | | Updated by Django on every successful authentication. |
| `date_joined` | timestamp | NN | Registration timestamp. |
| `updated_at` | timestamp | NN | Bumped on any mutation to the row. |
| `deactivated_at` | timestamp | | Soft-delete / self-deactivation marker. Kept separate from `is_active` so we can distinguish "admin disabled this account" from "user paused their own account" in future logic without overloading one flag. |

**Why no `username`/`first_name`/`last_name`:** the app is email-first and
name display is a profile concern, not an auth concern — keeping it off `users`
means auth logic never has to think about display formatting.

---

## `auth_methods`

Supports multiple login methods per user (email/password, phone OTP, Google OAuth)
without forking the `users` table per provider. One user can have several rows here.

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `id` | bigint | PK | |
| `user` | bigint | NN, FK → `users.id` | Owning user. |
| `provider` | varchar(20) | NN | e.g. `email`, `phone`, `google`. Discriminator for the row. |
| `provider_uid` | varchar(255) | | External identifier from the provider (e.g. Google's `sub` claim). Null for local email/phone methods. |
| `provider_email` | varchar(254) | | Email as reported by the provider — can differ from `users.email` (e.g. Google account uses a different address). Kept separately to avoid silently overwriting the user's primary email. |
| `is_verified` | boolean | NN | Whether this specific method has been verified (mirrors, but is independent of, `users.is_email_verified` / `is_phone_verified`). |
| `is_active` | boolean | NN | Lets a user unlink/relink a method without losing history. |
| `linked_at` | timestamp | NN | When this method was first attached to the account. |
| `last_used_at` | timestamp | | Updated on each successful login via this method. Useful for "last seen via Google" type UI and for identifying stale/unused methods. |

---

## `verification_tokens`

Generic one-time-token table backing email verification, phone OTP, password
reset, email change, and phone change flows. A single `type`-discriminated table
instead of one table per flow.

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `id` | bigint | PK | |
| `user_id` | bigint | NN, FK → `users.id` | |
| `auth_method_id` | bigint | NN, FK → `auth_methods.id` | Ties the token to the specific method being verified/changed (e.g. which phone number, which email). |
| `type` | varchar(30) | NN | Discriminator: `email_verify`, `phone_otp`, `password_reset`, `email_change`, `phone_change`, etc. |
| `token_hash` | varchar(255) | NN | The token itself is never stored raw — only its hash, so a DB read alone can't be used to redeem it. |
| `expires_at` | timestamp | NN | Enforced at the service layer; expired tokens are rejected even if unused. |
| `revoked_at` | timestamp | | Set when a token is explicitly invalidated (e.g. a newer token superseded it, or the user cancelled the flow). |
| `used_at` | timestamp | | Set on successful redemption. Tokens are single-use — checked before honoring a request. |
| `created_at` | timestamp | NN | |

**Pattern:** before issuing a new token, existing unused/unexpired tokens of the
same `type` for that user are invalidated first, so only one live token per flow
exists at a time. Cooldown between requests is enforced via cache (Redis), not
a DB column.

---

## `profiles`

Human-facing identity data. 1:1 with `users`, split out so auth logic never
touches display/personal data and vice versa.

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `id` | bigint | PK | |
| `user_id` | bigint | NN, FK → `users.id`, unique | Enforces the 1:1 relationship. |
| `first_name` | varchar(150) | | |
| `last_name` | varchar(150) | | |
| `display_name` | varchar(150) | | What's actually shown in the UI — lets a user set a nickname independent of legal first/last name. |
| `avatar_url` | varchar(500) | | Points at S3/CDN; the binary itself is never in Postgres. |
| `bio` | varchar(500) | | |
| `date_of_birth` | date | | |
| `gender` | varchar(20) | | |
| `country` | varchar(100) | | |
| `city` | varchar(100) | | |
| `timezone` | varchar(50) | | Used to localize notification timestamps and any scheduled sends. |
| `locale` | varchar(10) | | Language/region preference, e.g. `en-US`. |
| `created_at` | timestamp | NN | |
| `updated_at` | timestamp | NN | |

---

## `notifications` — moved to `notification_service`

The `notifications` table **no longer exists here**. It was migrated (rows
copied with microsecond precision) to `notification_service`'s own Postgres on
2026-09-29, and the table was dropped by migration `notifications.0003`. The
Prisma model, the `(user_id, read_at, created_at DESC)` index, and the
`/api/v1/notify` list/mark-read API are documented in the
[notification_service README](../../../notification-service/README.md).

This service still *produces* notifications: `create_and_push` POSTs to
notification_service over HTTP, and PII (email/phone) inside `metadata` is still
masked here, at this service layer, before the row is written. Failures are
logged rather than raised, so a notification outage cannot roll back a successful
auth transaction.

## Conventions

- **PK strategy:** bigint auto-increment for tables that are purely internal
  and never exposed by ID in a URL (`users`, `auth_methods`, `verification_tokens`,
  `profiles`); UUID for tables whose IDs are referenced externally or client-side
  (the in-app `notifications` table, which now lives in notification_service).
- **Timestamps:** every table has `created_at`; mutable tables also carry
  `updated_at`. Soft-state fields (`revoked_at`, `used_at`, `read_at`,
  `deactivated_at`) are nullable timestamps rather than booleans, so you get
  the "when" for free.
- **No cross-service FKs:** `user_id` fields referencing other services'
  domains (e.g. from `ai_service`) are plain UUID columns, never real foreign
  keys — see [Database isolation] principle.
- **Soft delete / deactivation over hard delete:** e.g. `users.deactivated_at`,
  `auth_methods.is_active` — preserves history and avoids cascading deletes
  across services.