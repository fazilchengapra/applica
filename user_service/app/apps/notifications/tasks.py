from celery import shared_task

from app.apps.notifications.services.sns_publisher import publish_notification_event


# publish notification event
@shared_task
def publish_notification_event_task(
    event: str, user_id: str, title: str, body: str, meta_data: dict | None = None
):
    if meta_data is None:
        meta_data = None
    publish_notification_event(
        event=event,
        user_id=user_id,
        title=title,
        body=body,
        meta_data=meta_data,
    )
