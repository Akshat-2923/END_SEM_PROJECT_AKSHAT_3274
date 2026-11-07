"""Database configuration and connection parameters."""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class DatabaseConfig:
    """Immutable database configuration settings."""
    url: str
    echo: bool = False
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 1800


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
            "postgresql+psycopg2://postgres@localhost:5432/dharascope_test"
        )

    # Standard application database URL
    return os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres@localhost:5432/dharascope"
    )
