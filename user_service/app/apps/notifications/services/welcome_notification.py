from app.apps.notifications.services.create_and_push_notification import create_and_push
from app.apps.notifications.constants.notification_type import NotificationType


def send_welcome(*, user):

    return create_and_push(
        user=user,
        type=NotificationType.WELCOME,
        title="Welcome to Applica 👋",
        body="Your account is ready. Let's tailor your first resume.",
        # One welcome per account, so the user id is the whole identity here.
        dedupe_key=f"{NotificationType.WELCOME}:{user.id}",
    )