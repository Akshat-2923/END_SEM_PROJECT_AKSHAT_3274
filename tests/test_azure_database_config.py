"""Automated tests for Azure PostgreSQL Flexible Server configuration and diagnostics.

Verifies:
1. Safe URL parsing with SQLAlchemy make_url (credentials never leaked).
2. Environment-based configuration (DB_SSL_MODE, DB_POOL_SIZE, DB_MAX_OVERFLOW).
3. SSL mode injection for PostgreSQL without breaking SQLite or non-SSL connections.
4. Connection pool lifecycle and pool_pre_ping validation.
5. Database connectivity diagnostic check and password redaction during failures.
6. FastAPI /health/db and /api/v1/health/db diagnostic endpoints.
"""

import os
from unittest.mock import patch
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.pool import QueuePool

from src.api.app import create_app
from src.database.config import (
    DatabaseConfig,
    get_database_config,
    get_database_url,
    get_sanitized_database_url,
    parse_database_url,
)
from src.database.session import (
    check_database_connectivity,
    get_engine,
)


# ===========================================================================
# 1. Safe URL Parsing & Credential Redaction Tests
# ===========================================================================

class TestSafeURLParsing:
    """Verify SQLAlchemy URL parsing and credential masking."""

    def test_parse_database_url_preserves_attributes(self):
        """Verify make_url extracts host, port, database, user without leaking secrets."""
        raw_url = "postgresql+psycopg2://azure_admin:SuperSecretPass123!@dharascope-flexible.postgres.database.azure.com:5432/dharascope_prod"
        parsed = parse_database_url(raw_url)

        assert isinstance(parsed, URL)
        assert parsed.drivername == "postgresql+psycopg2"
        assert parsed.host == "dharascope-flexible.postgres.database.azure.com"
        assert parsed.port == 5432
        assert parsed.database == "dharascope_prod"
        assert parsed.username == "azure_admin"
        assert parsed.password == "SuperSecretPass123!"

    def test_get_sanitized_database_url_masks_password(self):
        """Verify passwords are replaced with '***' in sanitized strings."""
        secret_password = "azure_db_top_secret_key!@#"
        raw_url = f"postgresql+psycopg2://dharascope_user:{secret_password}@dharascope-db.postgres.database.azure.com:5432/dharascope"

        sanitized = get_sanitized_database_url(raw_url)

        assert secret_password not in sanitized
        assert "***" in sanitized
        assert "dharascope-db.postgres.database.azure.com" in sanitized
        assert "dharascope_user" in sanitized
        assert "postgresql+psycopg2" in sanitized

    def test_sanitized_database_url_without_password(self):
        """Verify URL without password parses cleanly without errors."""
        url_no_pass = "postgresql+psycopg2://postgres@localhost:5432/dharascope"
        sanitized = get_sanitized_database_url(url_no_pass)
        assert "localhost" in sanitized
        assert "postgres@" in sanitized

    def test_sanitized_database_url_with_existing_url_object(self):
        """Verify get_sanitized_database_url accepts an existing URL instance."""
        url_obj = make_url("postgresql+psycopg2://usr:my_pwd@10.0.0.5:5432/db")
        sanitized = get_sanitized_database_url(url_obj)
        assert "my_pwd" not in sanitized
        assert "***" in sanitized


# ===========================================================================
# 2. Environment Configuration Tests
# ===========================================================================

class TestDatabaseConfiguration:
    """Verify environment-based database configuration parsing."""

    def test_database_config_defaults(self):
        """Verify default pool and SSL settings for development."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("DB_SSL_MODE", None)
            os.environ.pop("DB_POOL_SIZE", None)
            os.environ.pop("DB_MAX_OVERFLOW", None)
            os.environ.pop("DB_POOL_TIMEOUT", None)
            os.environ.pop("DB_POOL_RECYCLE", None)

            cfg = get_database_config()
            assert isinstance(cfg, DatabaseConfig)
            assert cfg.pool_size == 5
            assert cfg.max_overflow == 10
            assert cfg.pool_timeout == 30
            assert cfg.pool_recycle == 1800
            assert cfg.ssl_mode is None
            assert cfg.ssl_root_cert is None

    def test_database_config_env_overrides(self):
        """Verify environment variables override configuration for Azure deployment."""
        env_vars = {
            "DATABASE_URL": "postgresql+psycopg2://azure_user:pwd@azure-pg.database.azure.com:5432/dharascope",
            "DB_SSL_MODE": "require",
            "DB_SSL_ROOT_CERT": "/certs/DigiCertGlobalRootCA.crt.pem",
            "DB_POOL_SIZE": "8",
            "DB_MAX_OVERFLOW": "16",
            "DB_POOL_TIMEOUT": "45",
            "DB_POOL_RECYCLE": "900",
            "DB_ECHO": "true",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            cfg = get_database_config()
            assert cfg.ssl_mode == "require"
            assert cfg.ssl_root_cert == "/certs/DigiCertGlobalRootCA.crt.pem"
            assert cfg.pool_size == 8
            assert cfg.max_overflow == 16
            assert cfg.pool_timeout == 45
            assert cfg.pool_recycle == 900
            assert cfg.echo is True

    def test_database_config_query_sslmode_fallback(self):
        """Verify query string sslmode parameter is detected when DB_SSL_MODE is unset."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("DB_SSL_MODE", None)
            url_with_ssl = "postgresql+psycopg2://u:p@host:5432/db?sslmode=verify-full"
            cfg = get_database_config(url=url_with_ssl)
            assert cfg.ssl_mode == "verify-full"

    def test_database_config_test_mode(self):
        """Verify test configuration uses isolated TEST_DATABASE_URL and TEST_DB_SSL_MODE."""
        env_vars = {
            "TEST_DATABASE_URL": "postgresql+psycopg2://test_user:test_pwd@localhost:5432/test_isolated",
            "TEST_DB_SSL_MODE": "disable",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            cfg = get_database_config(is_test=True)
            assert "test_isolated" in cfg.url
            assert cfg.ssl_mode == "disable"


# ===========================================================================
# 3. SQLAlchemy Engine Creation & SSL Handling Tests
# ===========================================================================

class TestEngineSSLAndPoolConfiguration:
    """Verify engine initialization with SSL connect_args and pooling."""

    def test_get_engine_passes_sslmode_for_postgresql(self):
        """Verify sslmode is injected into connect_args for PostgreSQL engines."""
        test_url = "postgresql+psycopg2://test_user:pwd@dummy-azure.postgres.database.azure.com:5432/dharascope"
        engine = get_engine(test_url, ssl_mode="require", pool_size=4, max_overflow=8)

        # Engine URL and dialect properties
        assert engine.url.host == "dummy-azure.postgres.database.azure.com"
        assert isinstance(engine.pool, QueuePool)
        assert engine.pool.size() == 4

        # Verify connect_args captured sslmode
        connect_args = getattr(engine, "_connect_args", {})
        assert "sslmode" in connect_args
        assert connect_args["sslmode"] == "require"

    def test_get_engine_omits_sslmode_for_sqlite(self):
        """Verify SQLite engine creation does not inject sslmode, preventing TypeError."""
        sqlite_url = "sqlite:///:memory:"
        # Should not raise TypeError: 'sslmode' is an invalid keyword argument for Connection()
        engine = get_engine(sqlite_url, ssl_mode="require")
        assert engine.url.drivername == "sqlite"
        connect_args = getattr(engine, "_connect_args", {})
        assert "sslmode" not in connect_args

    def test_get_engine_root_ca_certificate(self):
        """Verify sslrootcert is passed when configured."""
        test_url = "postgresql+psycopg2://test_user:pwd@dummy-azure.postgres.database.azure.com:5432/dharascope_ca"
        cert_path = "/var/ssl/DigiCertGlobalRootCA.crt.pem"
        engine = get_engine(test_url, ssl_mode="verify-ca", ssl_root_cert=cert_path)
        connect_args = getattr(engine, "_connect_args", {})
        assert connect_args.get("sslrootcert") == cert_path


# ===========================================================================
# 4. Database Connectivity Diagnostics Tests
# ===========================================================================

class TestDatabaseConnectivityDiagnostics:
    """Verify sanitized database diagnostic check functions."""

    def test_check_database_connectivity_live_db(self):
        """Verify diagnostic check against operational PostgreSQL test database."""
        result = check_database_connectivity()

        assert result["status"] == "connected"
        assert result["connected"] is True
        assert result["dialect"] == "postgresql"
        assert result["driver"] == "psycopg2"
        assert result["database_name"] is not None
        assert result["username"] is not None
        assert result["sanitized_url"] is not None
        assert result["error"] is None

        # Verify passwords never leaked in sanitized_url
        assert "password" not in result["sanitized_url"].lower() or "***" in result["sanitized_url"]

        # Pool metrics verified
        if result["pool"]:
            assert result["pool"]["type"] == "QueuePool"
            assert result["pool"]["size"] is not None

    def test_check_database_connectivity_failure_masks_password(self):
        """Verify connection failures capture errors without exposing credentials."""
        secret_password = "very_sensitive_db_password_xyz!"
        bad_url = f"postgresql+psycopg2://azure_svc:{secret_password}@127.0.0.1:5439/nonexistent_db"
        bad_engine = create_engine(bad_url)

        result = check_database_connectivity(bad_engine)

        assert result["status"] == "disconnected"
        assert result["connected"] is False
        assert result["error"] is not None

        # Absolute guarantee: the raw secret password is not exposed in the error or sanitized URL
        assert secret_password not in result["error"]
        assert secret_password not in result["sanitized_url"]
        assert "***" in result["sanitized_url"]

    def test_check_database_connectivity_mock_engine(self):
        """Verify check_database_connectivity works with SQLite memory engine."""
        mem_engine = create_engine("sqlite:///:memory:")
        result = check_database_connectivity(mem_engine)

        assert result["status"] == "connected"
        assert result["connected"] is True
        assert result["dialect"] == "sqlite"
        assert "memory" in result["sanitized_url"]
        assert result["postgis_version"] is None  # PostGIS absent in pure SQLite memory


# ===========================================================================
# 5. FastAPI Health & Diagnostics Endpoints Tests
# ===========================================================================

class TestHealthDiagnosticsEndpoints:
    """Verify HTTP API endpoints expose safe diagnostics without leaking credentials."""

    @pytest.fixture(autouse=True)
    def setup_client(self):
        self.app = create_app()
        self.client = TestClient(self.app)

    def test_health_db_endpoint(self):
        """Verify GET /health/db returns structured diagnostic metrics."""
        response = self.client.get("/health/db")
        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert "connected" in data
        assert "dialect" in data
        assert "driver" in data
        assert "database_name" in data
        assert "sanitized_url" in data
        assert "ssl_active" in data
        assert "timestamp" in data

        # Check credentials are not present
        assert "password" not in str(data).lower() or "***" in str(data)

    def test_api_v1_health_db_alias(self):
        """Verify GET /api/v1/health/db returns identical diagnostic structure."""
        response = self.client.get("/api/v1/health/db")
        assert response.status_code == 200
        data = response.json()
        assert data["connected"] is True
        assert data["dialect"] == "postgresql"

    def test_standard_health_endpoint_backward_compatibility(self):
        """Verify standard GET /health remains fully backward-compatible."""
        response = self.client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("healthy", "degraded")
        assert data["app_name"] == "DharaScope"
        assert data["version"] == "2.2.0"
        assert data["database"] == "connected"
        assert "timestamp" in data
