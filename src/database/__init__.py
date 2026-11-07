"""DharaScope Database Package.

Provides PostgreSQL 16 + PostGIS database configuration, session management,
SQLAlchemy 2.0 declarative models, and Alembic migration infrastructure.
"""

from src.database.base import Base
from src.database.config import DatabaseConfig, get_database_url
from src.database.session import get_db, get_engine, get_session_factory

__all__ = [
    "Base",
    "DatabaseConfig",
    "get_database_url",
    "get_engine",
    "get_session_factory",
    "get_db",
]
