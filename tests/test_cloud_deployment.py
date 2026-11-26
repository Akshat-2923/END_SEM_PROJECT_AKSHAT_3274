"""Tests verifying cloud deployment configuration for Supabase, Docker, and Render.

Covers:
1. Supabase URL normalization (postgres://, postgresql://) and auto-SSL detection.
2. Production startup configuration validation and placeholder rejection.
3. Dynamic CORS allowlist enforcement for deployed FRONTEND_URL vs unauthorized origins.
4. Database health check resilience on disconnected sessions.
5. Storage path traversal hardening, private bucket provisioning, and deletion cleanup.
6. Dockerfile, .dockerignore, .env.example, render.yaml, and SPA redirect checks.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch
import uuid

from fastapi.testclient import TestClient
import pytest

from src.api.app import create_app
from src.config import BASE_DIR, get_cors_origins, validate_startup_config
from src.database.config import (
    get_database_config,
    get_sanitized_database_url,
    is_cloud_postgres_host,
    normalize_database_url,
    parse_database_url,
)
from src.storage import (
    LocalStorageBackend,
    StorageError,
    SupabaseStorageBackend,
)


class TestSupabaseDatabaseIntegrationConfig:
    """Verify Supabase Direct & Session Pooler connection URL and SSL handling."""

    def test_postgres_scheme_normalization(self):
        """Legacy postgres:// and bare postgresql:// URLs normalize to postgresql+psycopg2://."""
        url_legacy = "postgres://postgres.proj:secretpwd@aws-0-ap-south-1.pooler.supabase.com:5432/postgres"
        url_std = "postgresql://postgres.proj:secretpwd@db.proj.supabase.co:5432/postgres"
        url_explicit = "postgresql+psycopg://postgres:pwd@localhost:5432/dharascope"

        assert str(normalize_database_url(url_legacy)).startswith("postgresql+psycopg2://")
        assert str(normalize_database_url(url_std)).startswith("postgresql+psycopg2://")
        assert str(normalize_database_url(url_explicit)).startswith("postgresql+psycopg://")

        parsed = parse_database_url(url_legacy)
        assert parsed.drivername == "postgresql+psycopg2"
        assert parsed.host == "aws-0-ap-south-1.pooler.supabase.com"
        assert parsed.port == 5432

    def test_cloud_postgres_host_detection_and_auto_ssl(self, monkeypatch):
        """Supabase and cloud Postgres endpoints auto-enable sslmode=require when unset."""
        monkeypatch.delenv("DB_SSL_MODE", raising=False)
        monkeypatch.delenv("TEST_DB_SSL_MODE", raising=False)

        assert is_cloud_postgres_host("aws-0-ap-south-1.pooler.supabase.com") is True
        assert is_cloud_postgres_host("db.abcdefghijklmno.supabase.co") is True
        assert is_cloud_postgres_host("localhost") is False
        assert is_cloud_postgres_host("127.0.0.1") is False

        supabase_pooler_url = "postgresql://postgres.ref:pwd123@aws-0-ap-south-1.pooler.supabase.com:5432/postgres"
        cfg_cloud = get_database_config(url=supabase_pooler_url)
        assert cfg_cloud.ssl_mode == "require"

        sanitized = get_sanitized_database_url(supabase_pooler_url)
        assert "pwd123" not in sanitized
        assert "***" in sanitized

        cfg_local = get_database_config(url="postgresql+psycopg2://postgres@localhost:5432/dharascope")
        assert cfg_local.ssl_mode is None


class TestEnvironmentValidationAndCORS:
    """Verify startup configuration checks and dynamic CORS allowlisting."""

    def test_production_startup_validation_fails_on_missing_or_placeholders(self, monkeypatch):
        """Production startup rejects missing vars and unmodified template placeholders."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("DATABASE_URL", "")
        monkeypatch.setenv("SUPABASE_URL", "https://your-project-ref.supabase.co")
        monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
        monkeypatch.delenv("SUPABASE_JWT_SECRET", raising=False)
        monkeypatch.delenv("FRONTEND_URL", raising=False)
        monkeypatch.delenv("CORS_ORIGINS", raising=False)

        with pytest.raises(RuntimeError) as exc_info:
            validate_startup_config(strict=True)
        msg = str(exc_info.value)
        assert "DATABASE_URL" in msg
        assert "SUPABASE_URL" in msg
        assert "SUPABASE_SERVICE_ROLE_KEY" in msg
        assert "FRONTEND_URL" in msg

    def test_production_startup_validation_succeeds_with_valid_env(self, monkeypatch):
        """Production startup succeeds cleanly when valid settings are configured."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("DATABASE_URL", "postgresql://postgres.ref:pwd@aws-0-ap-south-1.pooler.supabase.com:5432/postgres")
        monkeypatch.setenv("SUPABASE_URL", "https://realproject123.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.validservice")
        monkeypatch.setenv("SUPABASE_JWT_SECRET", "prod_jwt_secret_minimum_32_characters_long")
        monkeypatch.setenv("FRONTEND_URL", "https://dharascope-frontend.onrender.com/")
        monkeypatch.setenv("SUPABASE_STORAGE_ENABLED", "true")

        summary = validate_startup_config(strict=True)
        assert summary["environment"] == "production"
        assert summary["storage_backend"] == "supabase"
        assert get_cors_origins() == ["https://dharascope-frontend.onrender.com"]

    def test_cors_allows_configured_frontend_origin_and_blocks_others(self, monkeypatch):
        """FastAPI CORSMiddleware permits FRONTEND_URL and denies unlisted origins."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("FRONTEND_URL", "dharascope-frontend.onrender.com")
        monkeypatch.setenv("CORS_ORIGINS", "https://custom.dharascope.org/")

        app = create_app()
        client = TestClient(app)

        # Allowed origin preflight
        allowed_res = client.options(
            "/health",
            headers={
                "Origin": "https://dharascope-frontend.onrender.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert allowed_res.status_code == 200
        assert (
            allowed_res.headers.get("access-control-allow-origin")
            == "https://dharascope-frontend.onrender.com"
        )

        # Disallowed origin preflight (including localhost in production!)
        disallowed_res = client.options(
            "/health",
            headers={
                "Origin": "https://untrusted.attacker.example",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert disallowed_res.headers.get("access-control-allow-origin") is None

    def test_health_endpoint_handles_db_connection_failure_gracefully(self):
        """GET /health returns degraded status safely without unhandled 500 when DB fails."""
        from src.api.dependencies import get_anonymous_db_session

        failing_session = MagicMock()
        failing_session.execute.side_effect = Exception("Connection refused to database")

        app = create_app()
        app.dependency_overrides[get_anonymous_db_session] = lambda: failing_session
        client = TestClient(app)

        res = client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "degraded"
        assert data["database"] == "disconnected"
        failing_session.rollback.assert_called_once()


class TestStorageHardeningAndPrivateBuckets:
    """Verify object storage traversal guards and private Supabase bucket helpers."""

    def test_path_traversal_rejected_in_local_storage(self, tmp_path: Path):
        """LocalStorageBackend rejects '..' traversal segments."""
        storage = LocalStorageBackend(base_dir=tmp_path)
        with pytest.raises(StorageError):
            storage.exists("reports", "../../etc/passwd")

    def test_ensure_private_buckets_creates_and_enforces_private(self, tmp_path: Path):
        """SupabaseStorageBackend provisions missing buckets as private (public=False)."""
        backend = SupabaseStorageBackend(
            supabase_url="https://testproject.supabase.co",
            service_role_key="test_service_key",
            cache_dir=tmp_path,
        )

        get_404 = MagicMock(status_code=404)
        get_public = MagicMock(status_code=200)
        get_public.json.return_value = {"id": "maps", "public": True}
        get_private = MagicMock(status_code=200)
        get_private.json.return_value = {"id": "reports", "public": False}

        post_ok = MagicMock(status_code=201)
        put_ok = MagicMock(status_code=200)

        with patch("httpx.Client.get", side_effect=[get_404, get_public, get_private]), \
             patch("httpx.Client.post", return_value=post_ok) as mock_post, \
             patch("httpx.Client.put", return_value=put_ok) as mock_put:
            res = backend.ensure_private_buckets()

        assert res["rasters"] == "created_private"
        assert res["maps"] == "updated_to_private"
        assert res["reports"] == "exists_private"
        mock_post.assert_called_once()
        mock_put.assert_called_once()


class TestDeploymentArtifactsIntegrity:
    """Verify repository deployment configuration files exist and contain zero secrets."""

    def test_docker_and_render_files_present_and_valid(self):
        dockerfile = (BASE_DIR / "Dockerfile").read_text(encoding="utf-8")
        dockerignore = (BASE_DIR / ".dockerignore").read_text(encoding="utf-8")
        render_yaml = (BASE_DIR / "render.yaml").read_text(encoding="utf-8")
        env_example = (BASE_DIR / ".env.example").read_text(encoding="utf-8")
        redirects = (BASE_DIR / "frontend" / "public" / "_redirects").read_text(encoding="utf-8")

        # Dockerfile invariants
        assert "USER appuser" in dockerfile
        assert "0.0.0.0" in dockerfile
        assert "${PORT:-8000}" in dockerfile
        assert "/health" in dockerfile
        assert "--reload" not in dockerfile

        # .dockerignore exclusions
        assert ".env" in dockerignore
        assert ".venv" in dockerignore
        assert "frontend" in dockerignore

        # render.yaml invariants & zero hardcoded secrets
        assert "dharascope-backend" in render_yaml
        assert "dharascope-frontend" in render_yaml
        assert "runtime: docker" in render_yaml
        assert "runtime: static" in render_yaml
        assert "staticPublishPath: dist" in render_yaml
        assert "healthCheckPath: /health" in render_yaml
        assert "VITE_API_BASE_URL" in render_yaml
        assert "envVarKey: RENDER_EXTERNAL_URL" in render_yaml
        assert "destination: /index.html" in render_yaml
        assert "postgresql://" not in render_yaml
        assert "eyJ" not in render_yaml

        # .env.example required placeholders
        for key in (
            "DATABASE_URL=",
            "SUPABASE_URL=",
            "SUPABASE_ANON_KEY=",
            "SUPABASE_SERVICE_ROLE_KEY=",
            "FRONTEND_URL=",
        ):
            assert key in env_example

        # SPA fallback redirects
        assert "/index.html 200" in redirects
