from celery import shared_task
from celery.utils.log import get_task_logger
from django.contrib.auth import get_user_model
from twilio.base.exceptions import TwilioRestException

from .utils import send_sms

User = get_user_model()
logger = get_task_logger(__name__)

OTP_TTL_MINUTES = 5


@shared_task(bind=True, max_retries=3, default_retry_delay=15)
def send_otp_sms_task(self, user_id, raw_otp):
    print('sending')
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        logger.warning("send_otp_sms_task: user %s no longer exists", user_id)
        return
    
    try:
        send_sms(
            to=str(user.phone_number),
            body=f"Your JobAuto verification code is {raw_otp}. It expires in {OTP_TTL_MINUTES} minutes.",
        )
    except TwilioRestException as exc:
        # Twilio-side failure (bad number, carrier rejection, etc.) — retry with backoff
        raise self.retry(exc=exc)