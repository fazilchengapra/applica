from django.utils import timezone
from django.db import transaction
from ..exception import InvalidPasswordError
from app.apps.users import tasks


def delete_account(user, password: str):
    if not user.check_password(password):
        raise InvalidPasswordError("Incorrect password.")

    user.is_active = False
    user.deactivated_at = timezone.now()
    user.save(update_fields=["is_active", "deactivated_at"])

    transaction.on_commit(lambda: tasks.revoke_all_tokens_task.delay(user.id))
    # Notifications live in notification_service's own database, so nothing cascades
    # from here and these rows would outlive the account.
    transaction.on_commit(lambda: tasks.purge_notifications_task.delay(user.id))