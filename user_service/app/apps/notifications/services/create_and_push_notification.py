from asgiref.sync import async_to_sync
from django.db import transaction
from app.apps.notifications.models import Notification
from channels.layers import get_channel_layer


@transaction.atomic
def create_and_push(*, user, type: str, title: str, body: str, metadata: dict = None):
    notification = Notification.objects.create(
        user=user,
        type=type,
        title=title,
        body=body,
        metadata=metadata or {},
    )

    def _push():
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"user_{user.id}",
            {
                "type": "send_notification",
                "data": {
                    "id": str(notification.id),
                    "message": notification.body,
                    "notif_type": notification.type,
                    "created_at": notification.created_at.isoformat(),
                },
            },
        )

    transaction.on_commit(_push)
    return notification
