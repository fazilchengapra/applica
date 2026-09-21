# Troubleshooting — user_service

Common issues, symptoms, and fixes. Add to this every time you debug something
non-obvious.

## Auth / JWT

### Symptom: JWT refresh returns 401

- **Cause:** refresh cookie missing/expired, or token was blacklisted on logout.
  The refresh endpoint reads the `refresh_token` cookie (path `/`), not a body.
- **Fix:** re-login to get fresh cookies, or check the cookie is set on path `/`
  (a known gotcha: `clear_auth_cookies` deletes at `/api/v1/auth/` but cookies
  are set at `/`).
- **Related:** [authentication docs](./api/authentication.md)

### Symptom: All requests 401 via Kong but work hitting the service directly

- **Cause:** Kong can't verify the JWT — `kong/.env` `KONG_JWT_SECRET` must
  equal the Django `SECRET_KEY` (HS256), and JWT `iss` must be
  `applica-user-service`.
- **Fix:** align the secrets and restart kong.

### Symptom: `403` on admin endpoints through Kong

- **Cause:** JWT `roles` claim missing/not in `[admin, staff]`, or request
  didn't go through Kong (admin views have no service-side permission).
- **Fix:** log in as an admin user (token must carry `roles`), route through
  Kong only.

## Emails / OTP

### Symptom: Verification emails not sent

- **Cause:** Celery worker down, or SMTP/Gmail app-password wrong.
- **Fix:** check `celery` container (`docker compose logs -f celery`), verify
  `EMAIL_HOST_USER`/`EMAIL_HOST_PASSWORD`, and look at `TaskExecution` rows
  (see [task-monitoring](./api/task-monitoring.md)).

### Symptom: OTP SMS not arriving

- **Cause:** Twilio credentials invalid, number unverified in Twilio trial
  mode, or `send_otp_sms_task` failing (3 retries).
- **Fix:** verify `TWILIO_*` env values and that the destination number is
  verified; watch `docker compose logs -f celery`.

## Database

- **Migrations not applied:** `docker compose up --build user-service` runs
  them via `entrypoint.sh`; if you see relation-not-found errors, run
  `docker compose exec user-service python manage.py migrate`.
- **`pytest` cannot create test DB:** the test run needs a reachable Postgres
  (`DB_HOST`/credentials from `.env`).

## Related

- [Deployment](./deployment.md)
- [Incident response runbook](../../runbooks/incident-response.md)