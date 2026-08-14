from app.apps.notifications.services.create_and_push_notification import create_and_push
from app.apps.notifications.constants.notification_type import NotificationType
from app.apps.notifications.models import NotificationType


def password_change_notification_helper(*, user_id):

    return {
        "user_id": user_id,
        "event": NotificationType.PASSWORD_CHANGED,
        "title": "Your Password Changed Successfully!",
        "body": "Your account password has been changed successfully.",
    }


def password_reset_notification_helper(*, user_id):

    return {
        "user_id": user_id,
        "event": NotificationType.PASSWORD_RESET_COMPLETED,
        "title": "Password Reset Successful!",
        "body": "Your account password has been reset successfully.",
    }