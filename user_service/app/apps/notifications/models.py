# The in-app notification table is owned by notification_service (Prisma
# `Notification` model in notification_service/prisma/schema/models/). It used to
# live here; the rows were migrated and this model was removed on 2026-09-29.
#
# user_service still *creates* notifications, but only by calling
# notification_service over HTTP via
# app.apps.notifications.services.create_and_push_notification.create_and_push.
#
# `NotificationType` is intentionally kept here: it is the canonical list of
# notification types this service is allowed to emit, and lives in
# .constants.notification_type.

