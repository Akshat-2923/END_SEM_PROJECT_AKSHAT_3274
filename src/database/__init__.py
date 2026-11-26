"""DharaScope Database Package.

Provides PostgreSQL 16 + PostGIS database configuration, session management,
SQLAlchemy 2.0 declarative models, and Alembic migration infrastructure.
Supports local development, Supabase Managed PostgreSQL (Direct & Session Pooler),
and Azure Database for PostgreSQL Flexible Server.
"""

from src.database.base import Base
from src.database.config import (
    DatabaseConfig,
    get_database_config,
    get_database_url,
    get_sanitized_database_url,
    is_cloud_postgres_host,
    normalize_database_url,
    parse_database_url,
)
from src.database.session import (
    check_database_connectivity,
    dispose_engines,
    get_db,
    get_engine,
    get_session_factory,
)

__all__ = [
    "Base",
    "DatabaseConfig",
    "get_database_config",
    "get_database_url",
    "get_sanitized_database_url",
    "is_cloud_postgres_host",
    "normalize_database_url",
    "parse_database_url",
    "get_engine",
    "get_session_factory",
    "get_db",
    "dispose_engines",
    "check_database_connectivity",
]

