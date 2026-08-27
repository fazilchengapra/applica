from app.core.config import settings
import json
import boto3
from app.core.config import settings

_sns_client = boto3.client(
    "sns",
    region_name=settings.AWS_REGION,
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
)


def publish_to_sns(topic_arn: str, message: dict) -> None:
    _sns_client.publish(
        TopicArn=topic_arn,
        Message=json.dumps(message),
    )
