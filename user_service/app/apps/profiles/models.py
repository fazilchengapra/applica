from django.db import models

# model import
from app.apps.users.models import User

from django.db import models


class Profile(models.Model):
    class Gender(models.TextChoices):
        MALE = "male", "Male"
        FEMALE = "female", "Female"
        OTHER = "other", "Other"
        PREFER_NOT_TO_SAY = "prefer_not_to_say", "Prefer not to say"

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
        db_index=True,
    )

    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    display_name = models.CharField(
        max_length=150,
        blank=True,
        help_text="Public-facing name, falls back to first_name",
    )

    avatar_url = models.URLField(max_length=500, blank=True)
    bio = models.CharField(max_length=500, blank=True)

    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(
        max_length=20,
        choices=Gender.choices,
        blank=True,
    )

    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    timezone = models.CharField(max_length=50, blank=True)
    locale = models.CharField(max_length=10, blank=True, help_text="e.g. en-US")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "profiles"
        verbose_name = "Profile"
        verbose_name_plural = "Profiles"

    def __str__(self):
        return self.display_name or self.first_name or str(self.user_id)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def save(self, *args, **kwargs):
        # Auto-fill display_name from first_name if not explicitly set
        if not self.display_name and self.first_name:
            self.display_name = self.first_name
        super().save(*args, **kwargs)
