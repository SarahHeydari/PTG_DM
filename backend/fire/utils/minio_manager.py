# fire/utils/minio_manager.py
import os
import json
from minio import Minio
from minio.error import S3Error


class MinioManager:
    def __init__(self):
        endpoint = os.getenv("MINIO_ENDPOINT", "minio:9000")
        access_key = os.getenv("MINIO_ACCESS_KEY") or os.getenv("MINIO_ROOT_USER", "minioadmin")
        secret_key = os.getenv("MINIO_SECRET_KEY") or os.getenv("MINIO_ROOT_PASSWORD", "minioadmin")
        secure = (os.getenv("MINIO_SECURE", "false").lower() == "true")

        self.client = Minio(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )

        self.public_base = os.getenv("MINIO_PUBLIC_BASE_URL", "http://localhost:9000").rstrip("/")

    def _bucket_policy_public_download(self, bucket: str) -> str:
        # Allows anonymous GET object
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "PublicReadGetObject",
                    "Effect": "Allow",
                    "Principal": {"AWS": ["*"]},
                    "Action": ["s3:GetObject"],
                    "Resource": [f"arn:aws:s3:::{bucket}/*"],
                }
            ],
        }
        return json.dumps(policy)

    def ensure_bucket_public(self, bucket: str) -> None:
        """
        Ensure bucket exists AND is public-download (anonymous GET).
        """
        bucket = (bucket or "").strip()
        if not bucket:
            raise ValueError("bucket is empty")

        try:
            found = self.client.bucket_exists(bucket)
            if not found:
                self.client.make_bucket(bucket)
        except S3Error as e:
            raise Exception(f"MinIO bucket_exists/make_bucket failed: {str(e)}")

        # Set public policy (idempotent)
        try:
            self.client.set_bucket_policy(bucket, self._bucket_policy_public_download(bucket))
        except S3Error as e:
            raise Exception(f"MinIO set_bucket_policy failed for {bucket}: {str(e)}")

    def put_bytes(self, bucket: str, object_name: str, content: bytes, content_type: str = "application/octet-stream"):
        from io import BytesIO

        self.ensure_bucket_public(bucket)

        data = BytesIO(content)
        length = len(content)

        try:
            self.client.put_object(
                bucket_name=bucket,
                object_name=object_name,
                data=data,
                length=length,
                content_type=content_type,
            )
        except S3Error as e:
            raise Exception(f"MinIO put_object failed: {str(e)}")

        return f"{self.public_base}/{bucket}/{object_name}"

    def upload_satellite(self, satellite_name: str, file_name: str, content: bytes) -> str:
        bucket = f"sat-{(satellite_name or '').strip().lower()}"
        return self.put_bytes(bucket, file_name, content, content_type="image/tiff")

    def upload_index(self, index_name: str, file_name: str, content: bytes) -> str:
        bucket = f"idx-{(index_name or '').strip().lower()}"
        return self.put_bytes(bucket, file_name, content, content_type="image/tiff")