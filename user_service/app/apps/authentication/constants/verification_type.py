from django.db import models

EMAIL_TYPE = "email_verification"
PHONE_TYPE = "phone_verification"
PASSWORD_REST_TYPE = "password_reset"
EMAIL_CHANGE_TYPE = " email_change"
PHONE_CHANGE_TYPE = "phone_change"
MAGIC_LINK_TYPE = "magic_link"


class VerificationType(models.TextChoices):
    EMAIL_VERIFICATION = EMAIL_TYPE, "Email Verification"
    PHONE_VERIFICATION = PHONE_TYPE, "Phone Verification"
    PASSWORD_RESET = PASSWORD_REST_TYPE, "Password Reset"
    EMAIL_CHANGE = EMAIL_CHANGE_TYPE, "Email Change"
    PHONE_CHANGE = PHONE_CHANGE_TYPE, "Phone Change"
    MAGIC_LINK = MAGIC_LINK_TYPE, "Magic Link"
