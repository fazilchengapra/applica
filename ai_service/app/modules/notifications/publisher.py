from app.core.config import settings
from app.modules.notifications.schemas import NotificationEvent
from app.modules.notifications.sns_client import publish_to_sns


def publish_event(event_type: str, user_id: str, payload: dict) -> None:
    event = NotificationEvent(event_type=event_type, user_id=user_id, payload=payload)
    publish_to_sns(settings.SNS_NOTIFICATIONS_TOPIC_ARN, event.model_dump())
