import boto3
from app.core.config import settings

def download_pdf_from_s3(s3_key: str) -> bytes:
    s3 = boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL,   # MinIO override in local dev, per your existing pattern
    )
    response = s3.get_object(Bucket=settings.S3_BUCKET_NAME, Key=s3_key)
    return response["Body"].read()