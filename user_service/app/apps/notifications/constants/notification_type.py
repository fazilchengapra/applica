from django.db import models


class NotificationType(models.TextChoices):
    # Email
    EMAIL_CHANGE_REQ = (
        "account.email_change_requested",
        "Email Change Request",
    )
    EMAIL_CHANGED = (
        "account.email_changed",
        "Email Changed",
    )
    EMAIL_VERIFIED = (
        "account.email_verified",
        "Email Verified",
    )

    # password
    PASSWORD_CHANGED = (
        "account.password_changed",
        "Password Changed",
    )
    FORGOT_PASSWORD_REQ = (
        "account.forgot_password_req",
        "Request for Forgot Password",
    )
    PASSWORD_RESET_COMPLETED = (
        "account.password_reset_completed",
        "Password Rest Success",
    )

    # phone
    PHONE_CHANGED = (
        "account.phone_changed",
        "Password Changed",
    )
    PHONE_VERIFIED = (
        "account.phone_verified",
        "Password Rest Success",
    )

    SMS_LOGIN_OTP = (
        "account.sms_login_otp",
        "SMS Login OTP",
    )

    CHANGE_PHONE_NUMBER_REQUEST = (
        "account.changed_phone_number_req",
        "Phone number change request",
    )

    # account
    WELCOME = (
        "account.register",
        "Welcome",
    )
    ACCOUNT_VERIFICATION_REQ = (
        "account.verification_requested",
        "Account Verification Request",
    )
    REGISTERED = ("account.user_registered", "Account Registered Success")
