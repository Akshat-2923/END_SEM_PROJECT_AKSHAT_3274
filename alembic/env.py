"""Alembic environment configuration for DharaScope database migrations."""

import os
import sys
from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv
from geoalchemy2 import alembic_helpers
from sqlalchemy import create_engine, pool

# Ensure root directory is on sys.path and .env is loaded for standalone CLI runs
_root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, _root_dir)
_env_path = os.path.join(_root_dir, ".env")
if os.path.exists(_env_path):
    load_dotenv(_env_path)

from src.database.base import Base
import src.database.models  # noqa: F401 - load all models for metadata
from src.database.config import (
    get_database_config,
    get_database_url,
    normalize_database_url,
    parse_database_url,
)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

_ALEMBIC_INI_DEFAULT_URL = "postgresql+psycopg2://postgres@localhost:5432/dharascope"
_configured_url = config.get_main_option("sqlalchemy.url", "")

# Respect explicit programmatic overrides (e.g. test suites setting TEST_DATABASE_URL),
# while ensuring DATABASE_URL from environment/.env overrides the static alembic.ini default.
resolved_url = get_database_url()
if (
    not _configured_url
    or "driver://user:pass" in _configured_url
    or (_configured_url == _ALEMBIC_INI_DEFAULT_URL and os.getenv("DATABASE_URL"))
):
    config.set_main_option("sqlalchemy.url", resolved_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Generates SQL scripts without an active database connection.
    """
    url = str(normalize_database_url(config.get_main_option("sqlalchemy.url") or resolved_url))
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=alembic_helpers.include_object,
        process_revision_directives=alembic_helpers.writer,
        render_item=alembic_helpers.render_item,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    Creates an Engine and associates a connection with the context, or reuses
    an existing connection if supplied in config attributes.
    """
    connectable = config.attributes.get("connection", None)

    if connectable is None:
        target_url = str(normalize_database_url(config.get_main_option("sqlalchemy.url") or resolved_url))
        db_config = get_database_config(url=target_url)
        parsed = parse_database_url(target_url)

        connect_args = {}
        if parsed.drivername.startswith("postgresql"):
            connect_args["connect_timeout"] = db_config.connect_timeout
            if db_config.ssl_mode:
                connect_args["sslmode"] = db_config.ssl_mode
            if db_config.ssl_root_cert:
                connect_args["sslrootcert"] = db_config.ssl_root_cert

        connectable = create_engine(
            db_config.url,
            poolclass=pool.NullPool,
            connect_args=connect_args,
        )

        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                include_object=alembic_helpers.include_object,
                process_revision_directives=alembic_helpers.writer,
                render_item=alembic_helpers.render_item,
            )

            with context.begin_transaction():
                context.run_migrations()
    else:
        context.configure(
            connection=connectable,
            target_metadata=target_metadata,
            include_object=alembic_helpers.include_object,
            process_revision_directives=alembic_helpers.writer,
            render_item=alembic_helpers.render_item,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
