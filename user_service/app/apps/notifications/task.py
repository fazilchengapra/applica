# notifications/tasks.py
from celery import shared_task
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from notifications.models import Notification


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def push_notification_task(self, notification_id: str):
    try:
        notification = Notification.objects.select_related("user").get(id=notification_id)
    except Notification.DoesNotExist as exc:
        raise self.retry(exc=exc)

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"user_{notification.user_id}",
        {
            "type": "notification.message",
            "data": {
                "id": str(notification.id),
                "type": notification.type,
                "title": notification.title,
                "message": notification.message,
                "payload": notification.payload,
                "is_read": notification.is_read,
                "created_at": notification.created_at.isoformat(),
            },
        },
    )