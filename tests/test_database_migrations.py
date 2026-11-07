"""Tests verifying Alembic migrations, upgrade/downgrade cycles, and PostGIS schema."""

import os
import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text

from src.database.base import Base
from src.database.config import get_database_url
import src.database.models  # noqa: F401


def is_postgres_available() -> bool:
    """Check if test PostgreSQL instance is reachable."""
    url = get_database_url(is_test=True)
    try:
        engine = create_engine(url, connect_args={"connect_timeout": 3})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1;"))
        return True
    except Exception:
        return False


POSTGRES_AVAILABLE = is_postgres_available()
skip_if_no_postgres = pytest.mark.skipif(
    not POSTGRES_AVAILABLE,
    reason="PostgreSQL + PostGIS test database is not available",
)


class TestAlembicMigrationConfiguration:
    """Tests checking Alembic configuration and migration script files."""

    def test_alembic_ini_exists_and_loads(self):
        """Verify alembic.ini is present in repository root and valid."""
        assert os.path.exists("alembic.ini")
        cfg = Config("alembic.ini")
        assert cfg.get_main_option("script_location") is not None

    def test_migration_scripts_discovery(self):
        """Verify migration revisions are discoverable and contain required functions."""
        cfg = Config("alembic.ini")
        script_dir = ScriptDirectory.from_config(cfg)
        revisions = list(script_dir.walk_revisions())

        assert len(revisions) >= 2
        initial_rev = revisions[-1]
        assert initial_rev.down_revision is None
        head_rev = revisions[0]
        assert head_rev.down_revision == initial_rev.revision

        # Verify module has upgrade and downgrade callables
        for rev in revisions:
            module = rev.module
            assert hasattr(module, "upgrade")
            assert callable(module.upgrade)
            assert hasattr(module, "downgrade")
            assert callable(module.downgrade)


@skip_if_no_postgres
class TestAlembicMigrationExecution:
    """Integration test suite executing Alembic migrations against isolated PostgreSQL."""

    def test_full_migration_upgrade_and_downgrade_cycle(self):
        """Verify upgrade to head, schema verification, downgrade to base, and re-upgrade."""
        test_url = get_database_url(is_test=True)
        engine = create_engine(test_url)

        # Clean slate: drop any tables created by earlier tests or create_all
        Base.metadata.drop_all(bind=engine)
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
            conn.execute(text("DROP TABLE IF EXISTS alembic_version;"))
            conn.commit()

        cfg = Config("alembic.ini")
        cfg.set_main_option("sqlalchemy.url", test_url)

        dharascope_tables = {
            "profiles",
            "aois",
            "analysis_runs",
            "water_metrics",
            "analysis_artifacts",
        }

        # 1. Start from base: verify tables do not exist initially
        insp = inspect(engine)
        initial_tables = set(insp.get_table_names(schema="public"))
        assert not dharascope_tables.intersection(initial_tables)

        # 2. Upgrade to head
        command.upgrade(cfg, "head")
        insp = inspect(engine)
        upgraded_tables = set(insp.get_table_names(schema="public"))
        assert dharascope_tables.issubset(upgraded_tables)

        # Verify spatial index and geometry column on aois
        indexes = {idx["name"] for idx in insp.get_indexes("aois")}
        assert "idx_aois_geometry" in indexes

        columns = {col["name"]: col for col in insp.get_columns("aois")}
        assert "geometry" in columns

        # Verify foreign keys
        fks_runs = {fk["referred_table"] for fk in insp.get_foreign_keys("analysis_runs")}
        assert "profiles" in fks_runs
        assert "aois" in fks_runs

        # Verify RLS enabled on all 5 tables
        with engine.connect() as conn:
            rls_rows = conn.execute(
                text("SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public' AND tablename IN ('profiles', 'aois', 'analysis_runs', 'water_metrics', 'analysis_artifacts');")
            ).fetchall()
            assert len(rls_rows) == 5
            for tbl, rls_active in rls_rows:
                assert rls_active is True, f"RLS not enabled on {tbl}"

            # Verify RLS policies exist
            policies = conn.execute(
                text("SELECT policyname FROM pg_policies WHERE schemaname = 'public';")
            ).fetchall()
            assert len(policies) >= 15

        # 3. Downgrade to base
        command.downgrade(cfg, "base")
        insp = inspect(engine)
        downgraded_tables = set(insp.get_table_names(schema="public"))
        assert not dharascope_tables.intersection(downgraded_tables)

        # 4. Re-upgrade to head so database remains in a ready state
        command.upgrade(cfg, "head")
        insp = inspect(engine)
        final_tables = set(insp.get_table_names(schema="public"))
        assert dharascope_tables.issubset(final_tables)
        engine.dispose()
