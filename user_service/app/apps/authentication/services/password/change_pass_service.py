from django.db import transaction
from app.apps.notifications.services.helper.password_notification_helper import (
    password_change_notification_helper,
)
from app.apps.notifications.services.password_service import notify_password_changed


def change_password(user, old_password: str, new_password: str) -> None:
    if not user.check_password(old_password):
        raise ValueError("Current password is incorrect.")

    if old_password == new_password:
        raise ValueError("New password must be different from the current password.")

    user.set_password(new_password)
    user.save(update_fields=["password"])

    transaction.on_commit(lambda: notify_password_changed(user.id, user.email))
