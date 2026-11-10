"""Tests for the DharaScope Storage Subsystem (Local & Supabase Storage)."""

from pathlib import Path
import tempfile
import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.database.models.analysis import AnalysisRun
from src.database.models.artifact import AnalysisArtifact
from src.database.models.profile import Profile
from src.database.session import get_db
from src.storage import (
    BUCKET_MAPS,
    BUCKET_RASTERS,
    BUCKET_REPORTS,
    LocalStorageBackend,
    StorageConfigurationError,
    StorageError,
    StorageNotFoundError,
    StorageUploadError,
    SupabaseStorageBackend,
    get_storage_backend,
)


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as td:
        yield Path(td)


@pytest.fixture
def sample_file(temp_dir):
    f = temp_dir / "test_report.pdf"
    f.write_bytes(b"%PDF-1.4 test report content payload")
    return f


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


class TestLocalStorageBackend:
    """Test suite for LocalStorageBackend."""

    def test_upload_file_creates_file(self, temp_dir, sample_file):
        storage = LocalStorageBackend(base_dir=temp_dir / "storage")
        dest = storage.upload_file(
            local_path=sample_file,
            bucket=BUCKET_REPORTS,
            destination_path="user_123/run_456/test_report.pdf",
            content_type="application/pdf",
        )
        assert dest == "user_123/run_456/test_report.pdf"
        assert storage.exists(BUCKET_REPORTS, dest)

    def test_upload_nonexistent_file_raises_error(self, temp_dir):
        storage = LocalStorageBackend(base_dir=temp_dir / "storage")
        with pytest.raises(StorageUploadError):
            storage.upload_file(
                local_path=temp_dir / "nonexistent.png",
                bucket=BUCKET_MAPS,
                destination_path="maps/nonexistent.png",
            )

    def test_download_and_read_bytes(self, temp_dir, sample_file):
        storage = LocalStorageBackend(base_dir=temp_dir / "storage")
        dest = storage.upload_file(
            local_path=sample_file,
            bucket=BUCKET_REPORTS,
            destination_path="test_read.pdf",
        )
        data = storage.read_bytes(BUCKET_REPORTS, dest)
        assert data == b"%PDF-1.4 test report content payload"

        # Download to specific path
        target_dest = temp_dir / "downloaded.pdf"
        downloaded = storage.download_file(BUCKET_REPORTS, dest, target_path=target_dest)
        assert downloaded.exists()
        assert downloaded.read_bytes() == data

    def test_download_nonexistent_raises_not_found(self, temp_dir):
        storage = LocalStorageBackend(base_dir=temp_dir / "storage")
        with pytest.raises(StorageNotFoundError):
            storage.download_file(BUCKET_REPORTS, "ghost_file.pdf")

    def test_delete_file(self, temp_dir, sample_file):
        storage = LocalStorageBackend(base_dir=temp_dir / "storage")
        dest = storage.upload_file(sample_file, BUCKET_REPORTS, "to_delete.pdf")
        assert storage.exists(BUCKET_REPORTS, dest)
        assert storage.delete_file(BUCKET_REPORTS, dest) is True
        assert storage.exists(BUCKET_REPORTS, dest) is False

    def test_get_local_path_returns_path_when_present(self, temp_dir, sample_file):
        storage = LocalStorageBackend(base_dir=temp_dir / "storage")
        dest = storage.upload_file(sample_file, BUCKET_MAPS, "figure.png")
        path = storage.get_local_path(BUCKET_MAPS, dest)
        assert path is not None
        assert path.exists()


class TestSupabaseStorageBackend:
    """Test suite for SupabaseStorageBackend using mocked HTTP responses."""

    def test_init_validation(self):
        with pytest.raises(StorageConfigurationError):
            SupabaseStorageBackend(supabase_url="", service_role_key="")

    def test_upload_file_success(self, temp_dir, sample_file):
        storage = SupabaseStorageBackend(
            supabase_url="https://testproject.supabase.co",
            service_role_key="test_service_key",
            cache_dir=temp_dir / "cache",
        )
        mock_res = MagicMock()
        mock_res.status_code = 200

        with patch("httpx.Client.post", return_value=mock_res) as mock_post:
            dest = storage.upload_file(
                local_path=sample_file,
                bucket=BUCKET_REPORTS,
                destination_path="user_1/run_1/report.pdf",
                content_type="application/pdf",
            )
            assert dest == "user_1/run_1/report.pdf"
            mock_post.assert_called_once()
            called_url = mock_post.call_args[0][0]
            assert "https://testproject.supabase.co/storage/v1/object/reports/user_1/run_1/report.pdf" in called_url
            headers = mock_post.call_args[1]["headers"]
            assert headers["Authorization"] == "Bearer test_service_key"

    def test_upload_file_failure_raises_storage_upload_error(self, temp_dir, sample_file):
        storage = SupabaseStorageBackend(
            supabase_url="https://testproject.supabase.co",
            service_role_key="test_service_key",
            cache_dir=temp_dir / "cache",
        )
        mock_res = MagicMock()
        mock_res.status_code = 500
        mock_res.text = "Internal Server Error in Supabase Storage"

        with patch("httpx.Client.post", return_value=mock_res):
            with pytest.raises(StorageUploadError) as exc_info:
                storage.upload_file(sample_file, BUCKET_MAPS, "panel.png")
            assert "500" in str(exc_info.value)

    def test_download_file_success(self, temp_dir):
        storage = SupabaseStorageBackend(
            supabase_url="https://testproject.supabase.co",
            service_role_key="test_service_key",
            cache_dir=temp_dir / "cache",
        )
        mock_res = MagicMock()
        mock_res.status_code = 200
        mock_res.content = b"cloud downloaded map bytes"

        with patch("httpx.Client.get", return_value=mock_res):
            downloaded = storage.download_file(BUCKET_MAPS, "user_1/run_1/map.png")
            assert downloaded.exists()
            assert downloaded.read_bytes() == b"cloud downloaded map bytes"

    def test_download_file_404_raises_storage_not_found_error(self, temp_dir):
        storage = SupabaseStorageBackend(
            supabase_url="https://testproject.supabase.co",
            service_role_key="test_service_key",
            cache_dir=temp_dir / "cache",
        )
        mock_res = MagicMock()
        mock_res.status_code = 404

        with patch("httpx.Client.get", return_value=mock_res):
            with pytest.raises(StorageNotFoundError):
                storage.download_file(BUCKET_MAPS, "missing.png")

    def test_get_signed_url_success(self, temp_dir):
        storage = SupabaseStorageBackend(
            supabase_url="https://testproject.supabase.co",
            service_role_key="test_service_key",
            cache_dir=temp_dir / "cache",
        )
        mock_res = MagicMock()
        mock_res.status_code = 200
        mock_res.json.return_value = {"signedURL": "/object/sign/maps/user_1/map.png?token=xyz"}

        with patch("httpx.Client.post", return_value=mock_res):
            signed_url = storage.get_signed_url(BUCKET_MAPS, "user_1/map.png")
            assert signed_url is not None
            assert "token=xyz" in signed_url


class TestStorageBackendFactory:
    """Test suite for get_storage_backend() factory."""

    def test_factory_returns_local_storage_by_default(self, monkeypatch):
        monkeypatch.delenv("SUPABASE_STORAGE_ENABLED", raising=False)
        backend = get_storage_backend()
        assert isinstance(backend, LocalStorageBackend)

    def test_factory_returns_supabase_storage_when_enabled(self, monkeypatch):
        monkeypatch.setenv("SUPABASE_STORAGE_ENABLED", "true")
        monkeypatch.setenv("SUPABASE_URL", "https://testproject.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test_role_key_value")
        backend = get_storage_backend()
        assert isinstance(backend, SupabaseStorageBackend)

    def test_factory_force_backend_override(self, monkeypatch):
        monkeypatch.setenv("SUPABASE_STORAGE_ENABLED", "true")
        monkeypatch.setenv("SUPABASE_URL", "https://testproject.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test_role_key_value")
        backend = get_storage_backend(force_backend="local")
        assert isinstance(backend, LocalStorageBackend)


class TestArtifactUploadFailureHandling:
    """Verify that failed artifact uploads do not generate misleading database records."""

    def test_upload_failure_skips_artifact_database_row(self, monkeypatch, temp_dir):
        """Simulate upload failure in storage backend and verify database does not persist phantom record."""
        # Force a storage backend that raises StorageUploadError on upload
        class FailingStorage(LocalStorageBackend):
            def upload_file(self, *args, **kwargs):
                raise StorageUploadError("Simulated remote cloud network partition")

        failing_storage = FailingStorage(base_dir=temp_dir)
        monkeypatch.setattr("src.services.analysis_service.get_storage_backend", lambda: failing_storage)

        # Trigger quick synthetic pipeline execution
        app = create_app()
        test_client = TestClient(app)

        import jwt

        secret = "super_secret_test_key_for_dharascope_verification_32_bytes"
        uid = uuid.uuid4()
        token = jwt.encode(
            {"sub": str(uid), "email": f"test_failure_{uid.hex[:6]}@dharascope.org", "aud": "authenticated", "iss": "https://testproject.supabase.co/auth/v1", "app_metadata": {"role": "user"}},
            secret,
            algorithm="HS256",
        )
        headers = {"Authorization": f"Bearer {token}"}

        res = test_client.post(
            "/api/v1/analyses?sync=true",
            headers=headers,
            json={
                "aoi_geometry": {
                    "type": "Polygon",
                    "coordinates": [[[80.90, 26.84], [80.92, 26.84], [80.92, 26.86], [80.90, 26.86], [80.90, 26.84]]]
                },
                "data_source": "synthetic",
            },
        )
        assert res.status_code == 201
        run_id = res.json()["id"]

        # Inspect database: AnalysisArtifact count should be 0 because all uploads failed
        with get_db() as session:
            artifacts = session.query(AnalysisArtifact).filter(AnalysisArtifact.analysis_run_id == run_id).all()
            assert len(artifacts) == 0  # No misleading phantom records!
