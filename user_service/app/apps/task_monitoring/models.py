from django.db import models


class TaskExecution(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        STARTED = "STARTED", "Started"
        SUCCESS = "SUCCESS", "Success"
        FAILURE = "FAILURE", "Failure"
        RETRY = "RETRY", "Retry"
        REVOKED = "REVOKED", "Revoked"

    task_id = models.CharField(
        max_length=255,
        unique=True,
        db_index=True
    )

    root_task_id = models.CharField(
        max_length=255,
        blank=True
    )

    parent_task_id = models.CharField(
        max_length=255,
        blank=True
    )

    task_name = models.CharField(max_length=255)

    queue = models.CharField(
        max_length=100,
        blank=True
    )

    worker = models.CharField(
        max_length=255,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )

    retries = models.PositiveIntegerField(default=0)

    args = models.JSONField(null=True, blank=True)
    kwargs = models.JSONField(null=True, blank=True)

    result = models.JSONField(
        null=True,
        blank=True
    )

    exception = models.TextField(blank=True)

    traceback = models.TextField(blank=True)

    started_at = models.DateTimeField(
        null=True,
        blank=True
    )

    finished_at = models.DateTimeField(
        null=True,
        blank=True
    )

    duration_ms = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["task_name"]),
            models.Index(fields=["created_at"]),
        ]