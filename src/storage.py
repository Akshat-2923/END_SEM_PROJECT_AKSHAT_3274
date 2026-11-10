"""Storage subsystem abstraction for DharaScope.

Supports LocalFilesystemStorage for local development and SupabaseStorageBackend
for configured cloud deployments.
"""

from abc import ABC, abstractmethod
import logging
import os
from pathlib import Path
from typing import Optional, Union
import uuid

import httpx

from src.config import (
    BASE_DIR,
    OUTPUTS_DIR,
)

logger = logging.getLogger("dhara_scope.storage")

# Standard storage bucket constants
BUCKET_RASTERS = "rasters"
BUCKET_MAPS = "maps"
BUCKET_REPORTS = "reports"
VALID_BUCKETS = {BUCKET_RASTERS, BUCKET_MAPS, BUCKET_REPORTS}


class StorageError(Exception):
    """Base exception for storage errors."""
    pass


class StorageUploadError(StorageError):
    """Raised when an artifact upload to storage fails."""
    pass


class StorageNotFoundError(StorageError):
    """Raised when a requested artifact object is not found in storage."""
    pass


class StorageConfigurationError(StorageError):
    """Raised when cloud storage is improperly configured."""
    pass


class BaseStorageBackend(ABC):
    """Abstract base class for storage backends."""

    @abstractmethod
    def upload_file(
        self,
        local_path: Union[str, Path],
        bucket: str,
        destination_path: str,
        content_type: Optional[str] = None,
    ) -> str:
        """Upload a local file into a storage bucket.

        Args:
            local_path: Path to the local file to upload.
            bucket: Target bucket name ('rasters', 'maps', 'reports').
            destination_path: Object path / key within the bucket.
            content_type: MIME type of the file.

        Returns:
            The normalized stored object path / key.
        """
        pass

    @abstractmethod
    def download_file(
        self,
        bucket: str,
        object_path: str,
        target_path: Optional[Union[str, Path]] = None,
    ) -> Path:
        """Download an object from a bucket to a local file path.

        Args:
            bucket: Source bucket name.
            object_path: Object path / key within the bucket.
            target_path: Optional destination Path. If None, saves to local cache.

        Returns:
            Path to the downloaded local file.
        """
        pass

    @abstractmethod
    def read_bytes(self, bucket: str, object_path: str) -> bytes:
        """Read the binary payload of an object from storage."""
        pass

    @abstractmethod
    def exists(self, bucket: str, object_path: str) -> bool:
        """Check whether an object exists in the storage bucket."""
        pass

    @abstractmethod
    def delete_file(self, bucket: str, object_path: str) -> bool:
        """Delete an object from storage."""
        pass

    @abstractmethod
    def get_local_path(self, bucket: str, object_path: str) -> Optional[Path]:
        """Return the direct local filesystem Path if available on disk."""
        pass

    @abstractmethod
    def get_signed_url(self, bucket: str, object_path: str, expires_in: int = 3600) -> Optional[str]:
        """Return a time-limited signed download URL if supported by backend."""
        pass


class LocalStorageBackend(BaseStorageBackend):
    """Local filesystem storage backend for local development and offline environments."""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or OUTPUTS_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_local_path(self, bucket: str, object_path: str) -> Path:
        """Resolve a storage object path against base_dir and outputs."""
        norm_path = object_path.replace("\\", "/").lstrip("/")
        
        # 1. Direct match relative to base_dir (e.g. outputs/<user>/<run>/<file>)
        candidate = self.base_dir / norm_path
        if candidate.exists():
            return candidate

        # 2. Check under bucket subdirectory: base_dir / bucket / norm_path
        candidate_bucket = self.base_dir / bucket / norm_path
        if candidate_bucket.exists():
            return candidate_bucket

        # 3. Check relative to BASE_DIR if norm_path contains 'outputs/'
        candidate_base = BASE_DIR / norm_path
        if candidate_base.exists():
            return candidate_base

        # Default fallback target location
        return self.base_dir / norm_path

    def upload_file(
        self,
        local_path: Union[str, Path],
        bucket: str,
        destination_path: str,
        content_type: Optional[str] = None,
    ) -> str:
        src = Path(local_path)
        if not src.exists():
            raise StorageUploadError(f"Source file does not exist: {local_path}")

        norm_dest = destination_path.replace("\\", "/").lstrip("/")
        target = self.base_dir / norm_dest

        # If source is not already at target, copy bytes
        if src.resolve() != target.resolve():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(src.read_bytes())

        logger.debug("LocalStorage: saved %s to %s (bucket %s)", src.name, norm_dest, bucket)
        return norm_dest

    def download_file(
        self,
        bucket: str,
        object_path: str,
        target_path: Optional[Union[str, Path]] = None,
    ) -> Path:
        resolved = self._resolve_local_path(bucket, object_path)
        if not resolved.exists():
            raise StorageNotFoundError(f"Local storage object not found: {object_path}")

        if target_path is not None:
            dest = Path(target_path)
            if dest.resolve() != resolved.resolve():
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(resolved.read_bytes())
            return dest

        return resolved

    def read_bytes(self, bucket: str, object_path: str) -> bytes:
        resolved = self._resolve_local_path(bucket, object_path)
        if not resolved.exists():
            raise StorageNotFoundError(f"Local storage object not found: {object_path}")
        return resolved.read_bytes()

    def exists(self, bucket: str, object_path: str) -> bool:
        return self._resolve_local_path(bucket, object_path).exists()

    def delete_file(self, bucket: str, object_path: str) -> bool:
        resolved = self._resolve_local_path(bucket, object_path)
        if resolved.exists():
            try:
                resolved.unlink()
                return True
            except OSError as err:
                logger.warning("Failed to delete local storage file %s: %s", resolved, err)
                return False
        return False

    def get_local_path(self, bucket: str, object_path: str) -> Optional[Path]:
        resolved = self._resolve_local_path(bucket, object_path)
        return resolved if resolved.exists() else None

    def get_signed_url(self, bucket: str, object_path: str, expires_in: int = 3600) -> Optional[str]:
        # Local backend does not produce HTTP signed URLs
        return None


class SupabaseStorageBackend(BaseStorageBackend):
    """Supabase Storage REST backend using service-role credentials.

    Stores artifacts remotely in Supabase Storage buckets ('rasters', 'maps', 'reports').
    Caches downloaded payloads locally for FileResponse streaming.
    """

    def __init__(
        self,
        supabase_url: str,
        service_role_key: str,
        cache_dir: Optional[Path] = None,
        timeout: float = 30.0,
    ):
        if not supabase_url or not service_role_key:
            raise StorageConfigurationError(
                "SupabaseStorageBackend requires both SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY."
            )

        self.supabase_url = supabase_url.rstrip("/")
        self.service_role_key = service_role_key.strip()
        self.cache_dir = cache_dir or (OUTPUTS_DIR / "cache" / "supabase")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout

    @property
    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.service_role_key}",
            "apikey": self.service_role_key,
        }

    def upload_file(
        self,
        local_path: Union[str, Path],
        bucket: str,
        destination_path: str,
        content_type: Optional[str] = None,
    ) -> str:
        src = Path(local_path)
        if not src.exists():
            raise StorageUploadError(f"Source file does not exist: {local_path}")

        norm_dest = destination_path.replace("\\", "/").lstrip("/")
        url = f"{self.supabase_url}/storage/v1/object/{bucket}/{norm_dest}"
        headers = self._headers.copy()
        headers["Content-Type"] = content_type or "application/octet-stream"
        headers["x-upsert"] = "true"

        data = src.read_bytes()
        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(url, headers=headers, content=data)
        except Exception as exc:
            logger.error("Supabase Storage upload network exception: %s", exc)
            raise StorageUploadError(f"Network error during Supabase Storage upload: {exc}") from exc

        if res.status_code in (200, 201):
            logger.info("Supabase Storage: uploaded %s to %s/%s", src.name, bucket, norm_dest)
            return norm_dest

        logger.error(
            "Supabase Storage upload failed with status %d: %s",
            res.status_code,
            res.text[:300],
        )
        raise StorageUploadError(
            f"Supabase Storage upload failed ({res.status_code}): {res.text[:200]}"
        )

    def download_file(
        self,
        bucket: str,
        object_path: str,
        target_path: Optional[Union[str, Path]] = None,
    ) -> Path:
        norm_path = object_path.replace("\\", "/").lstrip("/")
        dest = Path(target_path) if target_path else (self.cache_dir / bucket / norm_path)
        dest.parent.mkdir(parents=True, exist_ok=True)

        data = self.read_bytes(bucket, object_path)
        dest.write_bytes(data)
        return dest

    def read_bytes(self, bucket: str, object_path: str) -> bytes:
        norm_path = object_path.replace("\\", "/").lstrip("/")
        # Authenticated object retrieval
        url = f"{self.supabase_url}/storage/v1/object/authenticated/{bucket}/{norm_path}"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.get(url, headers=self._headers)
        except Exception as exc:
            logger.error("Supabase Storage read network exception: %s", exc)
            raise StorageError(f"Network error during Supabase Storage download: {exc}") from exc

        if res.status_code == 200:
            return res.content
        if res.status_code == 404:
            raise StorageNotFoundError(f"Object '{norm_path}' not found in bucket '{bucket}'")

        raise StorageError(
            f"Supabase Storage download failed with status {res.status_code}: {res.text[:200]}"
        )

    def exists(self, bucket: str, object_path: str) -> bool:
        norm_path = object_path.replace("\\", "/").lstrip("/")
        url = f"{self.supabase_url}/storage/v1/object/authenticated/{bucket}/{norm_path}"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                # Use GET with Range: bytes=0-0 to check existence without fetching full payload
                res = client.get(url, headers={**self._headers, "Range": "bytes=0-0"})
                return res.status_code in (200, 206)
        except Exception:
            return False

    def delete_file(self, bucket: str, object_path: str) -> bool:
        norm_path = object_path.replace("\\", "/").lstrip("/")
        url = f"{self.supabase_url}/storage/v1/object/{bucket}/{norm_path}"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.delete(url, headers=self._headers)
                return res.status_code in (200, 204)
        except Exception as exc:
            logger.warning("Failed to delete object from Supabase Storage: %s", exc)
            return False

    def get_local_path(self, bucket: str, object_path: str) -> Optional[Path]:
        """Check if artifact is already cached locally or on disk."""
        norm_path = object_path.replace("\\", "/").lstrip("/")
        
        # 1. Check local outputs directory
        local_cand = OUTPUTS_DIR / norm_path
        if local_cand.exists():
            return local_cand

        # 2. Check local cache directory
        cached_cand = self.cache_dir / bucket / norm_path
        if cached_cand.exists():
            return cached_cand

        return None

    def get_signed_url(self, bucket: str, object_path: str, expires_in: int = 3600) -> Optional[str]:
        norm_path = object_path.replace("\\", "/").lstrip("/")
        url = f"{self.supabase_url}/storage/v1/object/sign/{bucket}/{norm_path}"
        headers = self._headers.copy()
        headers["Content-Type"] = "application/json"
        payload = {"expiresIn": expires_in}

        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    signed_part = data.get("signedURL")
                    if signed_part:
                        if signed_part.startswith("http"):
                            return signed_part
                        return f"{self.supabase_url}/storage/v1{signed_part}"
        except Exception as exc:
            logger.warning("Failed to generate signed URL from Supabase Storage: %s", exc)
            return None

        return None


def get_storage_backend(force_backend: Optional[str] = None) -> BaseStorageBackend:
    """Retrieve the configured storage backend.

    Defaults to LocalStorageBackend unless SUPABASE_STORAGE_ENABLED=true and
    valid credentials (SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY) are provided.
    """
    if force_backend == "local":
        return LocalStorageBackend()

    supabase_url = os.getenv("SUPABASE_URL", "").strip()
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    storage_enabled = os.getenv("SUPABASE_STORAGE_ENABLED", "false").lower() in ("true", "1", "yes")

    if force_backend == "supabase" or (storage_enabled and supabase_url and service_key):
        return SupabaseStorageBackend(
            supabase_url=supabase_url,
            service_role_key=service_key,
        )

    return LocalStorageBackend()
