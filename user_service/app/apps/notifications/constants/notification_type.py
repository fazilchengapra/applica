from django.db import models


class NotificationType(models.TextChoices):
    # Email
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

    # account
    WELCOME = (
        "account.register",
        "Welcome",
    )
    REGISTRATIONS = ("account.verification_requested", "Account Verification Request")
    REGISTERED = ("account.user_registered", "Account Registered Success")
