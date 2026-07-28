# notification_service/api/v1/tasks.py
from celery import shared_task
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from app.apps.notifications.models import Notification

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
            "type": "notification.message",   # maps to consumer method notification_message
            "data": {
                "id": str(notification.id),
                "type": notification.type,
                "payload": notification.payload,
                "created_at": notification.created_at.isoformat(),
            },
        },
    )