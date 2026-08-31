import boto3
from app.config import settings

sns_client = boto3.client("sns", region_name="eu-north-1")

SNS_TOPIC_ARN = settings.SNS_NOTIFICATIONS_TOPIC_ARN
