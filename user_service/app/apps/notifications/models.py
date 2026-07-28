import uuid

from django.db import models
from django.conf import settings

# constants
from .constants.notification_type import NotificationType


class Notification(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    type = models.CharField(
        max_length=64,
        choices=NotificationType.choices,
        db_index=True,
    )

    title = models.CharField(max_length=255)

    body = models.TextField(
        blank=True,
    )

    metadata = models.JSONField(
        default=dict,
    )

    read_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        db_table = "notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["type"],
                name="idx_notification_type",
            ),
            models.Index(
                fields=["user", "read_at", "-created_at"],
                name="idx_user_read_created",
            ),
        ]

    def __str__(self):
        return f"{self.title} ({self.user})"
