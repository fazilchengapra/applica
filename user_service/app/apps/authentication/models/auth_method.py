from django.db import models

# user model
from app.apps.users.models import User


class AuthMethod(models.Model):
    """
    One row per authentication method linked to a user.
    A user can have multiple rows (email + google + mobile),
    but never two rows with the same provider (enforced by unique_together).
    """

    EMAIL = "email"
    MOBILE = "mobile"
    GOOGLE = "google"

    PROVIDER_CHOICES = [
        (EMAIL, "Email & Password"),
        (MOBILE, "Mobile & OTP"),
        (GOOGLE, "Google OAuth"),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE
    )  # references user.User.id

    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)

    # ---- OAuth (google) ----
    provider_uid = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="provider's unique user id, e.g. Google 'sub'",
    )
    provider_email = models.EmailField(null=True, blank=True)

    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    linked_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            # one method per provider per user — no duplicate "google" rows for same user
            models.UniqueConstraint(
                fields=["user_id", "provider"], name="unique_user_provider"
            ),
            # same OAuth account can't be linked to two different users
            models.UniqueConstraint(
                fields=["provider", "provider_uid"], name="unique_provider_account"
            ),
        ]
        indexes = [
            models.Index(fields=["user_id"])
        ]

    def __str__(self):
        return f"{self.user_id} - {self.provider}"
