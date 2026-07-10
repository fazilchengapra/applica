from django.db import models

EMAIL_TYPE = "email_verification"
PASSWORD_REST_TYPE = "password_reset"
EMAIL_CHANGE_TYPE = " email_change"
PHONE_TYPE = "phone_verification"
MAGIC_LINK_TYPE = "magic_link"
PHONE_CHANGE_OLD_TYPE = "phone_change_old"
PHONE_CHANGE_NEW_TYPE = "phone_change_new"


class VerificationType(models.TextChoices):
    EMAIL_VERIFICATION = EMAIL_TYPE, "Email Verification"
    PHONE_CHANGE_OLD = PHONE_CHANGE_OLD_TYPE, "Change old Phone"
    PHONE_CHANGE_NEW = PHONE_CHANGE_NEW_TYPE, "Change new Phone"
    PASSWORD_RESET = PASSWORD_REST_TYPE, "Password Reset"
    EMAIL_CHANGE = EMAIL_CHANGE_TYPE, "Email Change"
    PHONE_VERIFICATION = PHONE_TYPE, "Phone Change"
    MAGIC_LINK = MAGIC_LINK_TYPE, "Magic Link"
