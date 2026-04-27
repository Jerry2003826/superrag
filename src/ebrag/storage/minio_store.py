from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any


class MinioStore:
    def __init__(
        self,
        endpoint: str,
        *,
        access_key: str = "minio",
        secret_key: str = "minio123",
        secure: bool = False,
        client: Any | None = None,
    ) -> None:
        self.endpoint = endpoint
        if client is None:
            from minio import Minio

            client = Minio(
                endpoint,
                access_key=access_key,
                secret_key=secret_key,
                secure=secure,
            )
        self.client = client

    def _ensure_bucket(self, bucket: str) -> None:
        if not self.client.bucket_exists(bucket):
            self.client.make_bucket(bucket)

    def put_bytes(self, bucket: str, key: str, data: bytes) -> str:
        normalized_key = key.replace("\\", "/").lstrip("/")
        self._ensure_bucket(bucket)
        self.client.put_object(
            bucket,
            normalized_key,
            BytesIO(data),
            length=len(data),
            content_type="application/octet-stream",
        )
        return f"minio://{bucket}/{normalized_key}"

    def put_file(self, bucket: str, key: str, path: Path) -> str:
        return self.put_bytes(bucket, key, path.read_bytes())

    def get_bytes(self, bucket: str, key: str) -> bytes:
        response = self.client.get_object(bucket, key.replace("\\", "/").lstrip("/"))
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def exists(self, bucket: str, key: str) -> bool:
        try:
            self.client.stat_object(bucket, key.replace("\\", "/").lstrip("/"))
        except Exception:
            return False
        return True
