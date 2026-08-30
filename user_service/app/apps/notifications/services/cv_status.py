from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def push_cv_status(user_id: str, cv_id: str, status: str) -> None:

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"user_{user_id}",
        {
            "type": "cv.status.update",
            "event_type": "cv.updated",
            "data": {"cv_id": cv_id, "status": status},
        },
    )
