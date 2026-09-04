from app.apps.notifications.publishers.sns_publisher import publish_to_sns
from app.apps.notifications.constants.notification_type import NotificationType
from app.apps.notifications.constants.channel_type import ChannelChoice
from app.apps.notifications.events.schemas import PasswordChangedPayload

def notify_password_changed(user_id: str, email: str):
    payload = PasswordChangedPayload(email=email)
    publish_to_sns(
        NotificationType.PASSWORD_CHANGED, user_id, payload, channel=ChannelChoice.EMAIL
    )
