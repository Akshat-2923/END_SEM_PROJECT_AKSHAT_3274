"""Database configuration, URL parsing, and connection parameters.

Supports both local development PostgreSQL and cloud deployment via
Azure Database for PostgreSQL Flexible Server (PostgreSQL 16 + PostGIS 3.6).
"""

import os
from dataclasses import dataclass
from typing import Optional, Union
from sqlalchemy.engine import URL, make_url


@dataclass(frozen=True)
class DatabaseConfig:
    """Immutable database configuration settings."""
    url: str
    echo: bool = False
    ssl_mode: Optional[str] = None
    ssl_root_cert: Optional[str] = None
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 1800


def parse_database_url(url_or_str: Union[str, URL]) -> URL:
    """Safely parse a database URL using SQLAlchemy's make_url.

    Args:
        url_or_str: Raw URL string or existing SQLAlchemy URL object.

    Returns:
        SQLAlchemy URL instance.
    """
    if isinstance(url_or_str, URL):
        return url_or_str
    return make_url(url_or_str)


def get_sanitized_database_url(
    url: Optional[Union[str, URL]] = None,
    is_test: bool = False,
) -> str:
    """Return database connection URL with credentials securely redacted.

    Args:
        url: Optional connection string or URL object.
        is_test: If True and url is None, inspects test database URL.

    Returns:
        Connection string with password replaced by '***'.
    """
    raw_url = url or get_database_url(is_test=is_test)
    parsed = parse_database_url(raw_url)
    return parsed.render_as_string(hide_password=True)


def get_database_url(is_test: bool = False) -> str:
    """Retrieve database connection URL from environment variables.

    Args:
        is_test: If True, checks TEST_DATABASE_URL or uses isolated test database.

    Returns:
        SQLAlchemy-compatible database connection string.
    """
    if is_test:
        test_url = os.getenv("TEST_DATABASE_URL")
        if test_url:
            return test_url
        # Default isolated local PostgreSQL test database
        return os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg2://postgres@localhost:5432/dharascope_test",
        )

    # Standard application database URL
    return os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres@localhost:5432/dharascope",
    )


def get_database_config(
    is_test: bool = False,
    url: Optional[Union[str, URL]] = None,
) -> DatabaseConfig:
    """Retrieve complete database configuration from environment and URL parameters.

    Supports Azure Database for PostgreSQL Flexible Server TLS/SSL enforcement
    via DB_SSL_MODE and fine-grained connection pooling.

    Args:
        is_test: If True, inspects test-specific environment parameters.
        url: Optional connection URL override.

    Returns:
        Immutable DatabaseConfig instance.
    """
    raw_url = str(url) if url is not None else get_database_url(is_test=is_test)
    parsed_url = parse_database_url(raw_url)

    echo = os.getenv("DB_ECHO", "false").lower() in ("true", "1", "yes")

    # SSL configuration: environment variable takes precedence, fallback to URL query
    if is_test:
        ssl_mode = os.getenv("TEST_DB_SSL_MODE") or os.getenv("DB_SSL_MODE")
    else:
        ssl_mode = os.getenv("DB_SSL_MODE")

    if not ssl_mode and parsed_url.query.get("sslmode"):
        ssl_mode = str(parsed_url.query["sslmode"])

    if ssl_mode and not ssl_mode.strip():
        ssl_mode = None

    ssl_root_cert = os.getenv("DB_SSL_ROOT_CERT")
    if ssl_root_cert and not ssl_root_cert.strip():
        ssl_root_cert = None

    pool_size = int(os.getenv("DB_POOL_SIZE", "5"))
    max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "10"))
    pool_timeout = int(os.getenv("DB_POOL_TIMEOUT", "30"))
    pool_recycle = int(os.getenv("DB_POOL_RECYCLE", "1800"))

    return DatabaseConfig(
        url=raw_url,
        echo=echo,
        ssl_mode=ssl_mode,
        ssl_root_cert=ssl_root_cert,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=pool_timeout,
        pool_recycle=pool_recycle,
    )

