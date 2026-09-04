import json
import logging
import uuid
from typing import Literal
from datetime import datetime, timezone

from pydantic import BaseModel

from app.apps.notifications.config.aws import SNS_TOPIC_ARN, sns_client

logger = logging.getLogger(__name__)


def publish_to_sns(
    event_type: str,
    user_id: str,
    payload: BaseModel | None,
    channel: Literal["EMAIL", "SMS"],
) -> None:
    message = {
        "eventId": str(uuid.uuid4()),
        "eventType": event_type,
        "userId": str(user_id),
        "occurredAt": datetime.now(timezone.utc).isoformat(),
        "source": "user_service",
        "payload": payload.model_dump(mode="json") if payload else None,
    }

    try:
        sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Message=json.dumps(message),
            MessageAttributes={
                "eventType": {"DataType": "String", "StringValue": event_type},
                "channel": {"DataType": "String", "StringValue": channel},
            },
        )
    except Exception:
        logger.exception(
            "Failed to publish event to SNS",
            extra={"eventType": event_type, "userId": str(user_id)},
        )
