from django.db import models

class VerificationType(models.TextChoices):
        EMAIL_VERIFICATION = "email_verification", "Email Verification"
        PHONE_VERIFICATION = "phone_verification", "Phone Verification"
        PASSWORD_RESET = "password_reset", "Password Reset"
        EMAIL_CHANGE = "email_change", "Email Change"
        PHONE_CHANGE = "phone_change", "Phone Change"
        MAGIC_LINK = "magic_link", "Magic Link"