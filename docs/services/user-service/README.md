# user-service

Django + DRF service handling authentication, users, profiles, task monitoring,
and notifications.

## Apps in this service

- [authentication](./api/authentication.md) — login, JWT, OTP, password reset
- [users](./api/users.md) — core user account CRUD
- [profile](./api/profile.md) — extended profile data
- [task-monitoring](./api/task-monitoring.md) — async job/task status tracking
- [notification](./api/notification.md) — email/push/in-app notifications

## Docs in this service

- [Setup](./setup.md) — run it locally
- [Database](./database/schema.md) — models, relationships, migrations
- [Deployment](./deployment.md) — how this gets to EKS
- [Troubleshooting](./troubleshooting.md) — common issues and fixes

## Tech stack

- Django + Django REST Framework
- PostgreSQL (RDS)
- JWT auth
- Cloudinary for media
- Deployed on AWS EC2/EKS
