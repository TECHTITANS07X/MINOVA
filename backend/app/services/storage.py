"""
Object storage service with MinIO primary and filesystem fallback.
Provides S3-compatible API for document/attachment storage.
"""
from __future__ import annotations

import hashlib
import shutil
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote, urlencode

import structlog

from app.core.config import settings

logger = structlog.get_logger()

STORAGE_ROOT = Path(settings.storage_root)


class StorageService:
    def __init__(self) -> None:
        self._minio_available = False
        self._client = None
        self._try_minio()

    def _try_minio(self) -> None:
        try:
            from minio import Minio
            self._client = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=False,
            )
            self._client.list_buckets()
            self._minio_available = True
            logger.info("storage.minio_connected", endpoint=settings.MINIO_ENDPOINT)
        except Exception:
            self._minio_available = False
            logger.warning("storage.minio_unavailable_using_filesystem", root=str(STORAGE_ROOT))
            STORAGE_ROOT.mkdir(parents=True, exist_ok=True)

    def _bucket_path(self, bucket: str) -> Path:
        p = STORAGE_ROOT / bucket
        p.mkdir(parents=True, exist_ok=True)
        return p

    async def put_object(self, bucket: str, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        if self._minio_available and self._client:
            from io import BytesIO
            self._client.put_object(bucket, key, BytesIO(data), len(data), content_type=content_type)
        else:
            dest = self._bucket_path(bucket) / key
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
        return key

    async def get_object(self, bucket: str, key: str) -> bytes:
        if self._minio_available and self._client:
            resp = self._client.get_object(bucket, key)
            return resp.read()
        else:
            return (self._bucket_path(bucket) / key).read_bytes()

    async def delete_object(self, bucket: str, key: str) -> None:
        if self._minio_available and self._client:
            self._client.remove_object(bucket, key)
        else:
            path = self._bucket_path(bucket) / key
            if path.exists():
                path.unlink()

    async def presigned_put_url(self, bucket: str, key: str, expires: int = 3600) -> str:
        if self._minio_available and self._client:
            return self._client.presigned_put_object(bucket, key, expires=timedelta(seconds=expires))
        return f"/api/v1/storage/upload/{bucket}/{quote(key, safe='')}"

    async def presigned_get_url(self, bucket: str, key: str, expires: int = 3600) -> str:
        if self._minio_available and self._client:
            return self._client.presigned_get_object(bucket, key, expires=timedelta(seconds=expires))
        return f"/api/v1/storage/download/{bucket}/{quote(key, safe='')}"

    async def list_objects(self, bucket: str, prefix: str = "") -> list[str]:
        if self._minio_available and self._client:
            return [obj.object_name for obj in self._client.list_objects(bucket, prefix=prefix)]
        bp = self._bucket_path(bucket)
        prefix_path = bp / prefix if prefix else bp
        if not prefix_path.exists():
            return []
        return [str(p.relative_to(bp)) for p in prefix_path.rglob("*") if p.is_file()]

    def generate_key(self, filename: str, mine_id: str | None = None) -> str:
        ts = datetime.now(timezone.utc).strftime("%Y/%m/%d")
        uid = uuid.uuid4().hex[:12]
        prefix = f"{mine_id}/{ts}" if mine_id else ts
        return f"{prefix}/{uid}_{filename}"


storage = StorageService()
