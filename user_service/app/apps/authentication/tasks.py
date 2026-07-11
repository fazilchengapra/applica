import os

from celery.utils.log import get_task_logger
from django.contrib.auth import get_user_model
from twilio.base.exceptions import TwilioRestException
from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
import time

from app.apps.authentication.utils import sms

User = get_user_model()

logger = get_task_logger(__name__)

OTP_TTL_MINUTES = 5


@shared_task(bind=True, max_retries=3, default_retry_delay=15)
def send_otp_sms_task(self, user_id, raw_otp, **kwargs):
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        logger.warning("send_otp_sms_task: user %s no longer exists", user_id)
        return

    try:
        sms.send_sms(
            to=str(
                user.phone_number
                if "override_phone_number" not in kwargs
                else kwargs["override_phone_number"]
            ),
            body=f"Your JobAuto verification code is {raw_otp}. It expires in {OTP_TTL_MINUTES} minutes.",
        )
    except TwilioRestException as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_password_reset_email_task(self, user_id, raw_token):
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return

    reset_link = f"{os.getenv('FRONTEND_URL')}/password/reset?token={raw_token}"

    subject = "Reset your JobAuto password"
    message = (
        f"We received a request to reset your password.\n\n"
        f"Click the link below to set a new password (valid for 30 minutes):\n"
        f"{reset_link}\n\n"
        f"If you didn't request this, you can safely ignore this email."
    )

    try:
        start = time.perf_counter()
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        print(
            f"mail send func take time almost {time.perf_counter() - start:.2f} seconds"
        )
    except Exception as exc:
        raise self.retry(exc=exc)
    
@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_email_verification_task(self, user_id, raw_token):
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return

    verify_link = f"{settings.FRONTEND_URL}/verify-email?token={raw_token}"

    subject = "Verify your JobAuto email address"
    message = (
        f"Please verify your email address by clicking the link below "
        f"(valid for 30 minutes):\n\n{verify_link}\n\n"
        f"If you didn't create a JobAuto account, you can ignore this email."
    )

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
    except Exception as exc:
        raise self.retry(exc=exc)
