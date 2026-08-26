import uuid

import boto3
from botocore.exceptions import ClientError

from app.core.config import settings
from app.modules.master_cv.exceptions import S3UploadError


s3_client = boto3.client(
    "s3",
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.AWS_REGION,
)


def upload_bytes(
    contents: bytes,
    folder: str,
    extension: str,
    content_type: str,
) -> str:
    object_key = f"{folder}/{uuid.uuid4()}.{extension}"

    try:
        s3_client.put_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=object_key,
            Body=contents,
            ContentType=content_type,
        )

    except ClientError as e:
        raise S3UploadError(
            f"Failed to upload file to S3: {str(e)}"
        )

    return object_key