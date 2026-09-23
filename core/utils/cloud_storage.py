import uuid

import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from django.utils import timezone


class CloudStorageService:
    """Manages S3 private bucket storage and pre-signed access generation."""

    @classmethod
    def get_s3_client(cls):
        return boto3.client(
            "s3",
            aws_access_key_id=getattr(settings, "AWS_ACCESS_KEY_ID", ""),
            aws_secret_access_key=getattr(settings, "AWS_SECRET_ACCESS_KEY", ""),
            region_name=getattr(settings, "AWS_S3_REGION_NAME", "us-east-1"),
        )

    @classmethod
    def generate_presigned_upload_url(cls, user_id: int, file_name: str, file_type: str) -> dict:
        """Generates pre-signed URL to upload directly to S3 private bucket."""
        ext = file_name.split(".")[-1] if "." in file_name else "pdf"
        s3_key = f"resumes/user_{user_id}/{uuid.uuid4().hex[:10]}.{ext}"

        if not getattr(settings, "AWS_ACCESS_KEY_ID", None):
            # Fallback mock for local testing
            return {
                "upload_url": f"http://127.0.0.1:8000/api/mock-storage/upload/{s3_key}",
                "s3_key": s3_key,
                "expires_in": 900,
            }

        s3_client = cls.get_s3_client()
        try:
            presigned_post = s3_client.generate_presigned_post(
                Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                Key=s3_key,
                Fields={"Content-Type": file_type},
                Conditions=[
                    {"Content-Type": file_type},
                    ["content-length-range", 1024, 10485760],  # Max 10MB
                ],
                ExpiresIn=900,
            )
            return {"presigned_post": presigned_post, "s3_key": s3_key}
        except ClientError as e:
            return {"error": str(e)}

    @classmethod
    def generate_secure_access_url(cls, s3_key: str) -> str:
        """Returns a temporary access link for viewing/downloading resumes."""
        if not getattr(settings, "AWS_ACCESS_KEY_ID", None):
            return (
                f"https://cdn.zecpath.com/{s3_key}?mock_token={uuid.uuid4().hex[:12]}&expires=900"
            )

        s3_client = cls.get_s3_client()
        return s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.AWS_STORAGE_BUCKET_NAME, "Key": s3_key},
            ExpiresIn=getattr(settings, "AWS_QUERYSTRING_EXPIRE", 900),
        )
