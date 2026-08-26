import os

import boto3
from botocore.exceptions import ClientError


class S3Service:
    def __init__(self):
        self.bucket_name = os.getenv("AWS_S3_BUCKET")
        self.region = os.getenv("AWS_REGION")

        self.client = boto3.client(
            "s3",
            region_name=self.region,
        )

    def upload_file(
        self,
        file_path: str,
        s3_key: str,
        content_type: str | None = None,
    ) -> str:
        extra_args = {}

        if content_type:
            extra_args["ContentType"] = content_type

        try:
            self.client.upload_file(
                Filename=file_path,
                Bucket=self.bucket_name,
                Key=s3_key,
                ExtraArgs=extra_args or None,
            )

            return s3_key

        except ClientError as exc:
            raise RuntimeError(f"Failed to upload file to S3: {s3_key}") from exc

    def delete_file(
        self,
        s3_key: str,
    ) -> None:
        try:
            self.client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key,
            )

        except ClientError as exc:
            raise RuntimeError(f"Failed to delete file from S3: {s3_key}") from exc

    def generate_presigned_url(
        self,
        s3_key: str,
        expires_in: int = 3600,
    ) -> str:
        try:
            return self.client.generate_presigned_url(
                ClientMethod="get_object",
                Params={
                    "Bucket": self.bucket_name,
                    "Key": s3_key,
                },
                ExpiresIn=expires_in,
            )

        except ClientError as exc:
            raise RuntimeError(f"Failed to generate URL for: {s3_key}") from exc
