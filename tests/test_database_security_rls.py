"""Live PostgreSQL Row-Level Security (RLS) enforcement and isolation tests.

Verifies actual database-level security policies against PostgreSQL 16 + PostGIS 3.6:
- Private AOI isolation between User A and User B.
- Public AOI viewability vs modification protection.
- AnalysisRun cross-user access prevention.
- Child record inheritance for WaterMetrics and AnalysisArtifacts.
- Database-level prevention of unauthorized role escalation.
- Admin policy overrides.
"""

import uuid
from datetime import datetime, timezone

import pytest
from geoalchemy2.elements import WKTElement
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError, ProgrammingError
from sqlalchemy.orm import Session, sessionmaker

from src.auth import AuthenticatedUser, apply_rls_context, get_authenticated_db
from src.database.base import Base
from src.database.config import get_database_url
from src.database.models import AnalysisArtifact, AnalysisRun, AOI, Profile, WaterMetrics


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


@skip_if_no_postgres
class TestDatabaseRowLevelSecurity:
    """Test suite executing real database queries to verify PostgreSQL RLS enforcement."""

    @pytest.fixture(autouse=True)
    def setup_rls_suite(self):
        """Prepare fresh schema on isolated test database with RLS policies enabled."""
        url = get_database_url(is_test=True)
        self.engine = create_engine(url)
        self.SessionLocal = sessionmaker(bind=self.engine)

        from alembic import command
        from alembic.config import Config

        cfg = Config("alembic.ini")
        cfg.set_main_option("sqlalchemy.url", url)

        # Ensure clean migration state
        with self.engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
            conn.commit()

        command.upgrade(cfg, "head")

        with self.engine.connect() as conn:
            conn.execute(text("GRANT USAGE ON SCHEMA public, auth TO dharascope_app;"))
            conn.execute(text("GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO dharascope_app;"))
            conn.execute(text("GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO dharascope_app;"))
            conn.commit()

        # Create two distinct test user identities and one admin identity
        self.user_a = AuthenticatedUser(
            id=uuid.uuid4(),
            email=f"user_a_{uuid.uuid4().hex[:6]}@example.com",
            role="user",
            is_admin=False,
            claims={},
        )
        self.user_b = AuthenticatedUser(
            id=uuid.uuid4(),
            email=f"user_b_{uuid.uuid4().hex[:6]}@example.com",
            role="user",
            is_admin=False,
            claims={},
        )
        self.admin_user = AuthenticatedUser(
            id=uuid.uuid4(),
            email=f"admin_{uuid.uuid4().hex[:6]}@example.com",
            role="admin",
            is_admin=True,
            claims={},
        )

        # Seed initial profile records using superuser session before applying RLS
        with self.SessionLocal() as session:
            session.add_all([
                Profile(id=self.user_a.id, email=self.user_a.email, role="user"),
                Profile(id=self.user_b.id, email=self.user_b.email, role="user"),
                Profile(id=self.admin_user.id, email=self.admin_user.email, role="admin"),
            ])
            session.commit()

        yield

        # Cleanup: truncate tables after test
        with self.engine.connect() as conn:
            conn.execute(text("TRUNCATE profiles CASCADE;"))
            conn.commit()
        self.engine.dispose()

    def test_aoi_private_isolation(self):
        """Verify User A's private AOI is invisible to User B, but visible to User A and Admin."""
        wkt = "POLYGON((80.90 26.84, 80.92 26.84, 80.92 26.86, 80.90 26.86, 80.90 26.84))"

        # 1. User A inserts a private AOI
        with self.SessionLocal() as session:
            with get_authenticated_db(self.user_a, session):
                aoi_a = AOI(
                    id=uuid.uuid4(),
                    user_id=self.user_a.id,
                    name="User A Private AOI",
                    geometry=WKTElement(wkt, srid=4326),
                    area_km2=4.4,
                    area_hectares=440.0,
                    bbox=[80.90, 26.84, 80.92, 26.86],
                    centroid=[80.91, 26.85],
                    vertex_count=5,
                    is_public=False,
                )
                session.add(aoi_a)
                session.commit()
                aoi_a_id = aoi_a.id

        # 2. User A queries: must see own private AOI
        with self.SessionLocal() as session:
            with get_authenticated_db(self.user_a, session):
                aois_for_a = session.scalars(select(AOI).where(AOI.id == aoi_a_id)).all()
                assert len(aois_for_a) == 1

        # 3. User B queries: must NOT see User A's private AOI (returns empty)
        with self.SessionLocal() as session:
            with get_authenticated_db(self.user_b, session):
                aois_for_b = session.scalars(select(AOI).where(AOI.id == aoi_a_id)).all()
                assert len(aois_for_b) == 0

        # 4. Admin queries: must see User A's AOI via admin override
        with self.SessionLocal() as session:
            with get_authenticated_db(self.admin_user, session):
                aois_for_admin = session.scalars(select(AOI).where(AOI.id == aoi_a_id)).all()
                assert len(aois_for_admin) == 1

    def test_aoi_public_read_vs_write_protection(self):
        """Verify User B can read User A's public AOI, but cannot modify or delete it."""
        wkt = "POLYGON((80.90 26.84, 80.92 26.84, 80.92 26.86, 80.90 26.86, 80.90 26.84))"

        # User A creates a public AOI
        with self.SessionLocal() as session:
            with get_authenticated_db(self.user_a, session):
                public_aoi = AOI(
                    id=uuid.uuid4(),
                    user_id=self.user_a.id,
                    name="Gomti Baseline (Public)",
                    geometry=WKTElement(wkt, srid=4326),
                    area_km2=4.4,
                    area_hectares=440.0,
                    bbox=[80.90, 26.84, 80.92, 26.86],
                    centroid=[80.91, 26.85],
                    vertex_count=5,
                    is_public=True,
                )
                session.add(public_aoi)
                session.commit()
                aoi_id = public_aoi.id

        # User B queries: CAN read public AOI
        with self.SessionLocal() as session:
            with get_authenticated_db(self.user_b, session):
                visible_aoi = session.scalar(select(AOI).where(AOI.id == aoi_id))
                assert visible_aoi is not None
                assert visible_aoi.name == "Gomti Baseline (Public)"

                # User B attempts to UPDATE: 0 rows affected
                result = session.execute(
                    text("UPDATE aois SET name = 'Hacked Name' WHERE id = :id"),
                    {"id": str(aoi_id)},
                )
                assert result.rowcount == 0
                session.commit()

        # Verify name is unchanged
        with self.SessionLocal() as session:
            with get_authenticated_db(self.user_a, session):
                current_aoi = session.scalar(select(AOI).where(AOI.id == aoi_id))
                assert current_aoi.name == "Gomti Baseline (Public)"

                # User B attempts to DELETE: 0 rows affected
                with get_authenticated_db(self.user_b, session):
                    del_result = session.execute(
                        text("DELETE FROM aois WHERE id = :id"),
                        {"id": str(aoi_id)},
                    )
                    assert del_result.rowcount == 0

        # Verify AOI was not deleted
        with self.SessionLocal() as session:
            with get_authenticated_db(self.user_a, session):
                assert session.scalar(select(AOI).where(AOI.id == aoi_id)) is not None

    def test_analysis_runs_cross_user_isolation(self):
        """Verify User B cannot view, update, or delete User A's analysis runs."""
        with self.SessionLocal() as session:
            with get_authenticated_db(self.user_a, session):
                run_a = AnalysisRun(
                    id=uuid.uuid4(),
                    user_id=self.user_a.id,
                    status="SUCCESS",
                    data_provider="CDSE Sentinel-2 L2A",
                    t1_scene_id="S2A_TEST_T1",
                    t1_date=datetime(2023, 10, 10, tzinfo=timezone.utc),
                    t2_scene_id="S2B_TEST_T2",
                    t2_date=datetime(2023, 12, 9, tzinfo=timezone.utc),
                )
                session.add(run_a)
                session.commit()
                run_a_id = run_a.id

        # User B queries: returns empty
        with self.SessionLocal() as session:
            with get_authenticated_db(self.user_b, session):
                assert session.scalar(select(AnalysisRun).where(AnalysisRun.id == run_a_id)) is None

                # User B tries to update status: 0 rows affected
                res = session.execute(
                    text("UPDATE analysis_runs SET status = 'FAILED' WHERE id = :id"),
                    {"id": str(run_a_id)},
                )
                assert res.rowcount == 0

                # User B tries to delete: 0 rows affected
                del_res = session.execute(
                    text("DELETE FROM analysis_runs WHERE id = :id"),
                    {"id": str(run_a_id)},
                )
                assert del_res.rowcount == 0

    def test_child_record_inheritance_water_metrics(self):
        """Verify water_metrics inherits access control through parent analysis_runs."""
        # User A creates run and water_metrics
        with self.SessionLocal() as session:
            with get_authenticated_db(self.user_a, session):
                run_a = AnalysisRun(
                    id=uuid.uuid4(),
                    user_id=self.user_a.id,
                    status="SUCCESS",
                    data_provider="CDSE Sentinel-2 L2A",
                    t1_scene_id="S2A_TEST_T1",
                    t1_date=datetime(2023, 10, 10, tzinfo=timezone.utc),
                    t2_scene_id="S2B_TEST_T2",
                    t2_date=datetime(2023, 12, 9, tzinfo=timezone.utc),
                )
                session.add(run_a)
                session.flush()

                wm = WaterMetrics(
                    id=uuid.uuid4(),
                    analysis_run_id=run_a.id,
                    common_valid_pixels=1000,
                    common_valid_area_ha=10.0,
                    pixel_size_m2=100.0,
                    t1_water_pixels=200,
                    t1_water_area_m2=20000.0,
                    t1_water_area_ha=2.0,
                    t2_water_pixels=150,
                    t2_water_area_m2=15000.0,
                    t2_water_area_ha=1.5,
                    absolute_change_m2=-5000.0,
                    absolute_change_ha=-0.5,
                    percentage_change=-25.0,
                    persistent_water_m2=15000.0,
                    persistent_water_ha=1.5,
                    apparent_loss_m2=5000.0,
                    apparent_loss_ha=0.5,
                    apparent_gain_m2=0.0,
                    apparent_gain_ha=0.0,
                    limitation_statement="Child RLS test.",
                )
                session.add(wm)
                session.commit()
                wm_id = wm.id
                run_id = run_a.id

        # User B queries water_metrics: returns empty
        with self.SessionLocal() as session:
            with get_authenticated_db(self.user_b, session):
                assert session.scalar(select(WaterMetrics).where(WaterMetrics.id == wm_id)) is None

                # User B attempts to inject a metric linked to User A's run: RLS policy denies
                unauthorized_wm = WaterMetrics(
                    id=uuid.uuid4(),
                    analysis_run_id=run_id,
                    common_valid_pixels=500,
                    common_valid_area_ha=5.0,
                    pixel_size_m2=100.0,
                    t1_water_pixels=50,
                    t1_water_area_m2=5000.0,
                    t1_water_area_ha=0.5,
                    t2_water_pixels=50,
                    t2_water_area_m2=5000.0,
                    t2_water_area_ha=0.5,
                    absolute_change_m2=0.0,
                    absolute_change_ha=0.0,
                    persistent_water_m2=5000.0,
                    persistent_water_ha=0.5,
                    apparent_loss_m2=0.0,
                    apparent_loss_ha=0.0,
                    apparent_gain_m2=0.0,
                    apparent_gain_ha=0.0,
                    limitation_statement="Malicious injection attempt.",
                )
                session.add(unauthorized_wm)
                with pytest.raises((IntegrityError, DBAPIError, ProgrammingError)):
                    session.commit()
                session.rollback()

    def test_child_record_inheritance_analysis_artifacts(self):
        """Verify analysis_artifacts inherits access control through parent analysis_runs."""
        with self.SessionLocal() as session:
            with get_authenticated_db(self.user_a, session):
                run_a = AnalysisRun(
                    id=uuid.uuid4(),
                    user_id=self.user_a.id,
                    status="SUCCESS",
                    data_provider="CDSE Sentinel-2 L2A",
                    t1_scene_id="S2A_TEST_T1",
                    t1_date=datetime(2023, 10, 10, tzinfo=timezone.utc),
                    t2_scene_id="S2B_TEST_T2",
                    t2_date=datetime(2023, 12, 9, tzinfo=timezone.utc),
                )
                session.add(run_a)
                session.flush()

                art = AnalysisArtifact(
                    id=uuid.uuid4(),
                    analysis_run_id=run_a.id,
                    artifact_type="REPORT_PDF",
                    storage_bucket="reports",
                    storage_path="reports/run_a.pdf",
                    file_name="run_a.pdf",
                    mime_type="application/pdf",
                )
                session.add(art)
                session.commit()
                art_id = art.id

        # User B queries: returns empty
        with self.SessionLocal() as session:
            with get_authenticated_db(self.user_b, session):
                assert session.scalar(select(AnalysisArtifact).where(AnalysisArtifact.id == art_id)) is None

        # Admin queries: returns the artifact
        with self.SessionLocal() as session:
            with get_authenticated_db(self.admin_user, session):
                assert session.scalar(select(AnalysisArtifact).where(AnalysisArtifact.id == art_id)) is not None

    def test_database_anti_privilege_escalation(self):
        """Verify database-level RLS policy rejects user attempting to set role='admin'."""
        with self.SessionLocal() as session:
            with get_authenticated_db(self.user_a, session):
                # User A attempts to update their own role from 'user' to 'admin'
                with pytest.raises((IntegrityError, DBAPIError, ProgrammingError)) as exc_info:
                    session.execute(
                        text("UPDATE profiles SET role = 'admin' WHERE id = :id"),
                        {"id": str(self.user_a.id)},
                    )
                    session.commit()
                # Verify RLS check policy violation
                assert "violates row-level security policy" in str(exc_info.value).lower()
                session.rollback()

        # Verify role is still 'user'
        with self.SessionLocal() as session:
            with get_authenticated_db(self.user_a, session):
                prof = session.scalar(select(Profile).where(Profile.id == self.user_a.id))
                assert prof.role == "user"
