import uuid
import boto3
from botocore.exceptions import ClientError

from app.core.config import settings
from app.modules.master_cv.constants import S3_PREFIX
from app.modules.master_cv.exceptions import S3UploadError, S3ObjectNotFoundError

s3_client = boto3.client(
    "s3",
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.AWS_REGION,
)

def _pdf_exists(object_key: str):
    try:
        s3_client.head_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=object_key,
        )
    except ClientError as e:
        raise S3ObjectNotFoundError('The requested file does not exist.')

def upload_pdf_to_s3(contents: bytes, original_filename: str) -> str:
    object_key = f"{S3_PREFIX}{uuid.uuid4()}.pdf"

    try:
        s3_client.put_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=object_key,
            Body=contents,
            ContentType="application/pdf",
            Metadata={"original_filename": original_filename},
        )
    except ClientError as e:
        raise S3UploadError(str(e))

    return object_key


def delete_pdf_from_s3(object_key: str) -> None:
    try:
        _pdf_exists(object_key)
        s3_client.delete_object(Bucket=settings.S3_BUCKET_NAME, Key=object_key)
    except ClientError as e:
        raise S3ObjectNotFoundError("The requested file does not exist.")
