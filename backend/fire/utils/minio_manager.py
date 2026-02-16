import io
import os
import re
from minio import Minio
from minio.error import S3Error

PUBLIC_READ_POLICY_TEMPLATE = """
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"AWS": ["*"]},
      "Action": ["s3:GetObject"],
      "Resource": ["arn:aws:s3:::%s/*"]
    }
  ]
}
"""

def _slug(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"[^a-z0-9-]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s or "unknown"


class MinioManager:
    def __init__(self):
        self.endpoint = os.getenv("MINIO_ENDPOINT", "minio:9000")
        self.public_base_url = os.getenv("MINIO_PUBLIC_BASE_URL", "http://localhost:9000")
        self.access_key = os.getenv("MINIO_ACCESS_KEY")
        self.secret_key = os.getenv("MINIO_SECRET_KEY")
        self.secure = str(os.getenv("MINIO_SECURE", "false")).lower() == "true"

        if not self.access_key or not self.secret_key:
            raise RuntimeError("MINIO_ACCESS_KEY / MINIO_SECRET_KEY is not set")

        self.client = Minio(
            self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure
        )

    def ensure_bucket(self, bucket_name: str, make_public=True):
        try:
            if not self.client.bucket_exists(bucket_name):
                self.client.make_bucket(bucket_name)

            if make_public:
                policy = PUBLIC_READ_POLICY_TEMPLATE % bucket_name
                self.client.set_bucket_policy(bucket_name, policy)

        except S3Error as e:
            raise RuntimeError(f"MinIO bucket error: {e}")

    def upload_bytes(self, bucket: str, object_name: str, content: bytes, content_type="application/octet-stream") -> str:
        self.ensure_bucket(bucket, make_public=True)

        data_stream = io.BytesIO(content)
        self.client.put_object(
            bucket_name=bucket,
            object_name=object_name,
            data=data_stream,
            length=len(content),
            content_type=content_type
        )

        return f"{self.public_base_url}/{bucket}/{object_name}"

    # --- requested behavior ---
    def upload_satellite(self, satellite_name: str, file_name: str, content: bytes) -> str:
        bucket = f"sat-{_slug(satellite_name)}"
        return self.upload_bytes(bucket, file_name, content)

    def upload_index(self, index_name: str, file_name: str, content: bytes) -> str:
        bucket = f"idx-{_slug(index_name)}"
        return self.upload_bytes(bucket, file_name, content)
