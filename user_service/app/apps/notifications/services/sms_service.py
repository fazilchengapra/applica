from app.apps.notifications.events.schemas import SMSCommon
from app.apps.notifications.constants.channel_type import ChannelChoice
from app.apps.notifications.publishers.sns_publisher import publish_to_sns
from app.apps.notifications.constants.notification_type import NotificationType


def request_login_otp_sms(user_id: str, phone_number: int, raw_otp: str):
    payload = SMSCommon(phone_number=phone_number, raw_otp=raw_otp)
    publish_to_sns(
        NotificationType.SMS_LOGIN_OTP, user_id, payload, channel=ChannelChoice.SMS
    )


def change_phone_otp_sms(user_id: str, phone_number: int, raw_otp: str):
    payload = SMSCommon(phone_number=phone_number, raw_otp=raw_otp)
    publish_to_sns(
        NotificationType.CHANGE_PHONE_NUMBER_REQUEST,
        user_id,
        payload,
        channel=ChannelChoice.SMS,
    )
