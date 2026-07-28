from app.apps.notifications.services.create_and_push_notification import create_and_push
from app.apps.notifications.constants.notification_type import NotificationType


def password_change_notification(*, user):

    return create_and_push(
        user=user,
        type=NotificationType.PASSWORD_CHANGED,
        title="Your Password Changed Successfully!",
        body="Your account password is changed success",
    )


def password_reset_notification(*, user):

    return create_and_push(
        user=user,
        type=NotificationType.PASSWORD_RESET_COMPLETED,
        title="Password Reset Success!",
        body="Your account password reset success.",
    )