from django.db import models
from django.utils import timezone

from app.apps.users.models import User

from .auth_method import AuthMethod

# verification type choices
from ..constants.verification_type import VerificationType

class VerificationToken(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="verification_tokens",
    )

    auth_method = models.ForeignKey(
        AuthMethod,
        on_delete=models.CASCADE,
        related_name="verification_tokens",
    )

    type = models.CharField(
        max_length=30,
        choices=VerificationType.choices,
    )

    token_hash = models.CharField(
        max_length=255,
        help_text="SHA-256 or equivalent hash of the token/OTP.",
    )

    expires_at = models.DateTimeField()

    revoked_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    used_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        db_table = "verification_tokens"
        verbose_name = "Verification Token"
        verbose_name_plural = "Verification Tokens"

        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["auth_method"]),
            models.Index(fields=["type"]),
            models.Index(fields=["user", "type"]),
        ]

    def is_expired(self):
        return self.expires_at <= timezone.now()

    def is_used(self):
        return self.used_at is not None

    def is_revoked(self):
        return self.revoked_at is not None

    def is_active(self):
        return not self.is_used() and not self.is_revoked() and not self.is_expired()

    def __str__(self):
        return f"{self.user.email} - {self.type}"
