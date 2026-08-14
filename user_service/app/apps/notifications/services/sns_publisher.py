import os
import boto3
import json
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

_sns_client = boto3.client(
    "sns",
    region_name=os.getenv("AWS_REGION"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)


def publish_notification_event(
    event: str, user_id: str, title: str, body: str, meta_data: dict
) -> str | None:

    try:
        response = _sns_client.publish(
            TopicArn=os.getenv("SNS_NOTIFICATIONS_TOPIC_ARN"),
            Message=json.dumps(
                {
                    "event_type": event,
                    "user_id": str(user_id),
                    "title": title,
                    "body": body,
                    "meta_data": meta_data,
                }
            ),
            MessageAttributes={
                "event_type": {"DataType": "String", "StringValue": event}
            },
        )
        print("event succeed the response is 0", response)
        return response["MessageId"]
    except Exception:
        logger.exception("Failed to publish SNS notification: %s", event)
        return None
