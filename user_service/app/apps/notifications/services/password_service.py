from app.apps.notifications.publishers.sns_publisher import publish_to_sns
from app.apps.notifications.constants.notification_type import NotificationType
from app.apps.notifications.constants.channel_type import ChannelChoice
from app.apps.notifications.events.schemas import PasswordChangedPayload
from app.apps.notifications.events.schemas import ForgotPasswordPayload
from app.apps.notifications.events.schemas import CommonPayload


def notify_password_changed(user_id: str, email: str):
    payload = PasswordChangedPayload(email=email)
    publish_to_sns(
        NotificationType.PASSWORD_CHANGED, user_id, payload, channel=ChannelChoice.EMAIL
    )


def notify_forgot_password(user_id: str, email: str, raw_token: str):
    payload = ForgotPasswordPayload(raw_token=raw_token, email=email)
    publish_to_sns(
        NotificationType.FORGOT_PASSWORD_REQ,
        user_id,
        payload,
        channel=ChannelChoice.EMAIL,
    )


def notify_password_rest(user_id: str, email: str):
    payload = CommonPayload(email=email)

    publish_to_sns(
        NotificationType.PASSWORD_RESET_COMPLETED,
        user_id,
        payload,
        channel=ChannelChoice.EMAIL,
    )
