from django.db import transaction
from app.apps.notifications.models import Notification


@transaction.atomic
def create_and_push(*, user, type: str, title: str, body: str, metadata: dict = None):
    from app.apps.notifications.tasks import push_notification_task

    notification = Notification.objects.create(
        user=user,
        type=type,
        title=title,
        body=body,
        metadata=metadata or {},
    )
    # transaction.on_commit(lambda: push_notification_task.delay(str(notification.id)))
    return notification