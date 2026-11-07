"""Comprehensive tests for DharaScope SQLAlchemy database models and constraints."""

import os
import uuid
from datetime import datetime, timezone

import pytest
from geoalchemy2.elements import WKTElement
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

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


class TestModelDefinitions:
    """Unit tests validating model class attributes, tables, and column configurations."""

    def test_registered_tables(self):
        """Ensure all 5 entity tables are registered in the declarative Base metadata."""
        table_names = set(Base.metadata.tables.keys())
        expected_tables = {
            "profiles",
            "aois",
            "analysis_runs",
            "water_metrics",
            "analysis_artifacts",
        }
        assert expected_tables.issubset(table_names)

    def test_profile_table_metadata(self):
        """Verify profiles table columns, primary key, and check constraints."""
        table = Base.metadata.tables["profiles"]
        cols = {c.name for c in table.columns}
        assert {"id", "email", "full_name", "role", "quota_monthly_runs", "created_at", "updated_at"} == cols

        assert table.columns["id"].primary_key is True
        assert table.columns["email"].unique is True or any(
            idx.unique for idx in table.indexes if "email" in [col.name for col in idx.columns]
        )

        constraints = {c.name for c in table.constraints if hasattr(c, "name") and c.name}
        assert "ck_profiles_role" in constraints
        assert "ck_profiles_quota_positive" in constraints

    def test_aoi_table_metadata(self):
        """Verify aois table columns, geometry column, and check constraints."""
        table = Base.metadata.tables["aois"]
        cols = {c.name for c in table.columns}
        expected_cols = {
            "id",
            "user_id",
            "name",
            "description",
            "geometry",
            "area_km2",
            "area_hectares",
            "bbox",
            "centroid",
            "vertex_count",
            "is_public",
            "created_at",
            "updated_at",
        }
        assert expected_cols == cols

        # Check PostGIS geometry type and SRID
        geom_col = table.columns["geometry"]
        assert geom_col.type.geometry_type == "POLYGON"
        assert geom_col.type.srid == 4326

        constraints = {c.name for c in table.constraints if hasattr(c, "name") and c.name}
        assert "ck_aois_area_bounds" in constraints
        assert "ck_aois_vertex_bounds" in constraints

    def test_analysis_runs_table_metadata(self):
        """Verify analysis_runs table columns and constraints."""
        table = Base.metadata.tables["analysis_runs"]
        cols = {c.name for c in table.columns}
        expected_cols = {
            "id",
            "user_id",
            "aoi_id",
            "status",
            "data_provider",
            "is_real_data",
            "t1_scene_id",
            "t1_date",
            "t1_cloud_cover",
            "t2_scene_id",
            "t2_date",
            "t2_cloud_cover",
            "ndwi_threshold",
            "error_message",
            "execution_duration_sec",
            "execution_timestamp",
            "created_at",
            "updated_at",
        }
        assert expected_cols == cols

        constraints = {c.name for c in table.constraints if hasattr(c, "name") and c.name}
        assert "ck_analysis_runs_status" in constraints
        assert "ck_analysis_runs_threshold" in constraints

    def test_water_metrics_table_metadata(self):
        """Verify water_metrics table columns and 1:1 foreign key unique index."""
        table = Base.metadata.tables["water_metrics"]
        cols = {c.name for c in table.columns}
        expected_cols = {
            "id",
            "analysis_run_id",
            "common_valid_pixels",
            "common_valid_area_ha",
            "pixel_size_m2",
            "t1_water_pixels",
            "t1_water_area_m2",
            "t1_water_area_ha",
            "t2_water_pixels",
            "t2_water_area_m2",
            "t2_water_area_ha",
            "absolute_change_m2",
            "absolute_change_ha",
            "percentage_change",
            "persistent_water_m2",
            "persistent_water_ha",
            "apparent_loss_m2",
            "apparent_loss_ha",
            "apparent_gain_m2",
            "apparent_gain_ha",
            "limitation_statement",
            "created_at",
        }
        assert expected_cols == cols
        assert table.columns["percentage_change"].nullable is True

    def test_analysis_artifacts_table_metadata(self):
        """Verify analysis_artifacts table columns and constraints."""
        table = Base.metadata.tables["analysis_artifacts"]
        cols = {c.name for c in table.columns}
        expected_cols = {
            "id",
            "analysis_run_id",
            "artifact_type",
            "storage_bucket",
            "storage_path",
            "file_name",
            "file_size_bytes",
            "mime_type",
            "expires_at",
            "created_at",
        }
        assert expected_cols == cols

        constraints = {c.name for c in table.constraints if hasattr(c, "name") and c.name}
        assert "ck_artifacts_type" in constraints
        assert "ck_artifacts_bucket" in constraints

    def test_model_repr_methods(self):
        """Verify string representations of model instances."""
        user_uuid = uuid.uuid4()
        p = Profile(id=user_uuid, email="test@dharascope.org", role="user")
        assert "test@dharascope.org" in repr(p)

        aoi = AOI(id=uuid.uuid4(), name="Gomti Study Area", area_km2=4.5, user_id=user_uuid)
        assert "Gomti Study Area" in repr(aoi)

        run = AnalysisRun(
            id=uuid.uuid4(),
            user_id=user_uuid,
            status="SUCCESS",
            t1_date=datetime(2023, 10, 10, tzinfo=timezone.utc),
            t2_date=datetime(2023, 12, 9, tzinfo=timezone.utc),
        )
        assert "SUCCESS" in repr(run)

        wm = WaterMetrics(
            id=uuid.uuid4(),
            analysis_run_id=run.id,
            t1_water_area_ha=54.2,
            t2_water_area_ha=42.1,
            absolute_change_ha=-12.1,
        )
        assert "-12.1" in repr(wm)

        art = AnalysisArtifact(
            id=uuid.uuid4(),
            analysis_run_id=run.id,
            artifact_type="MAP_PNG",
            storage_bucket="maps",
            file_name="water_change_map.png",
        )
        assert "water_change_map.png" in repr(art)


@skip_if_no_postgres
class TestLiveDatabaseOperations:
    """Integration test suite executing CRUD operations and constraints against PostgreSQL."""

    @pytest.fixture(autouse=True)
    def setup_db(self):
        """Prepare fresh schema on isolated test database before each test."""
        url = get_database_url(is_test=True)
        engine = create_engine(url)
        SessionLocal = sessionmaker(bind=engine)

        from alembic.config import Config
        from alembic import command
        cfg = Config("alembic.ini")
        cfg.set_main_option("sqlalchemy.url", url)
        command.upgrade(cfg, "head")

        with engine.connect() as conn:
            conn.execute(text("TRUNCATE profiles CASCADE;"))
            conn.commit()

        self.engine = engine
        self.session: Session = SessionLocal()

        yield

        self.session.close()
        self.engine.dispose()

    def test_profile_crud_and_defaults(self):
        """Test inserting and querying a user profile."""
        profile = Profile(
            email=f"user_{uuid.uuid4().hex[:6]}@example.com",
            full_name="Hydrology Researcher",
            role="user",
        )
        self.session.add(profile)
        self.session.commit()

        queried = self.session.scalar(select(Profile).where(Profile.id == profile.id))
        assert queried is not None
        assert queried.role == "user"
        assert queried.quota_monthly_runs == 50
        assert queried.created_at is not None

    def test_profile_role_constraint(self):
        """Ensure check constraint rejects invalid user roles."""
        invalid_profile = Profile(
            email=f"invalid_{uuid.uuid4().hex[:6]}@example.com",
            role="superadmin",  # not in ('user', 'admin')
        )
        self.session.add(invalid_profile)
        with pytest.raises(IntegrityError):
            self.session.commit()
        self.session.rollback()

    def test_profile_quota_constraint(self):
        """Ensure check constraint rejects negative quotas."""
        invalid_profile = Profile(
            email=f"quota_{uuid.uuid4().hex[:6]}@example.com",
            quota_monthly_runs=-5,
        )
        self.session.add(invalid_profile)
        with pytest.raises(IntegrityError):
            self.session.commit()
        self.session.rollback()

    def test_aoi_postgis_insertion_and_spatial_query(self):
        """Test inserting an AOI with PostGIS geometry and querying with PostGIS ST_Area."""
        user = Profile(email=f"aoi_user_{uuid.uuid4().hex[:6]}@example.com")
        self.session.add(user)
        self.session.commit()

        wkt = "POLYGON((80.90 26.84, 80.92 26.84, 80.92 26.86, 80.90 26.86, 80.90 26.84))"
        aoi = AOI(
            user_id=user.id,
            name="Lucknow Reach",
            geometry=WKTElement(wkt, srid=4326),
            area_km2=4.40,
            area_hectares=440.0,
            bbox=[80.90, 26.84, 80.92, 26.86],
            centroid=[80.91, 26.85],
            vertex_count=5,
        )
        self.session.add(aoi)
        self.session.commit()

        # Query using PostGIS ST_Area on geography
        res = self.session.execute(
            text("SELECT ST_Area(geometry::geography) / 1000000.0 AS area_calc FROM aois WHERE id = :id"),
            {"id": aoi.id},
        ).scalar_one()

        assert 4.3 < res < 4.5
        assert round(res, 1) == round(aoi.area_km2, 1)

    def test_aoi_area_constraints(self):
        """Verify check constraint enforces 0.10 to 100.00 km² range."""
        user = Profile(email=f"bounds_user_{uuid.uuid4().hex[:6]}@example.com")
        self.session.add(user)
        self.session.commit()

        wkt = "POLYGON((80.90 26.84, 80.92 26.84, 80.92 26.86, 80.90 26.86, 80.90 26.84))"

        # Too small (< 0.10 km²)
        small_aoi = AOI(
            user_id=user.id,
            name="Too Small",
            geometry=WKTElement(wkt, srid=4326),
            area_km2=0.05,
            area_hectares=5.0,
            bbox=[80.90, 26.84, 80.92, 26.86],
            centroid=[80.91, 26.85],
            vertex_count=5,
        )
        self.session.add(small_aoi)
        with pytest.raises(IntegrityError):
            self.session.commit()
        self.session.rollback()

        # Too large (> 100.00 km²)
        large_aoi = AOI(
            user_id=user.id,
            name="Too Large",
            geometry=WKTElement(wkt, srid=4326),
            area_km2=105.0,
            area_hectares=10500.0,
            bbox=[80.90, 26.84, 80.92, 26.86],
            centroid=[80.91, 26.85],
            vertex_count=5,
        )
        self.session.add(large_aoi)
        with pytest.raises(IntegrityError):
            self.session.commit()
        self.session.rollback()

    def test_aoi_vertex_count_constraints(self):
        """Verify check constraint enforces vertex limits (4 to 500)."""
        user = Profile(email=f"vertex_user_{uuid.uuid4().hex[:6]}@example.com")
        self.session.add(user)
        self.session.commit()

        wkt = "POLYGON((80.90 26.84, 80.92 26.84, 80.92 26.86, 80.90 26.86, 80.90 26.84))"

        # Under min vertices (< 4)
        invalid_aoi = AOI(
            user_id=user.id,
            name="Degenerate",
            geometry=WKTElement(wkt, srid=4326),
            area_km2=5.0,
            area_hectares=500.0,
            bbox=[80.90, 26.84, 80.92, 26.86],
            centroid=[80.91, 26.85],
            vertex_count=3,
        )
        self.session.add(invalid_aoi)
        with pytest.raises(IntegrityError):
            self.session.commit()
        self.session.rollback()

        # Over max vertices (> 500)
        invalid_aoi_max = AOI(
            user_id=user.id,
            name="Too Complex",
            geometry=WKTElement(wkt, srid=4326),
            area_km2=5.0,
            area_hectares=500.0,
            bbox=[80.90, 26.84, 80.92, 26.86],
            centroid=[80.91, 26.85],
            vertex_count=501,
        )
        self.session.add(invalid_aoi_max)
        with pytest.raises(IntegrityError):
            self.session.commit()
        self.session.rollback()

    def test_analysis_run_constraints(self):
        """Verify status and ndwi_threshold check constraints on AnalysisRun."""
        user = Profile(email=f"run_user_{uuid.uuid4().hex[:6]}@example.com")
        self.session.add(user)
        self.session.commit()

        # Invalid status
        invalid_run = AnalysisRun(
            user_id=user.id,
            status="UNKNOWN_STATUS",
            data_provider="CDSE Sentinel-2 L2A",
            t1_scene_id="S2A_1",
            t1_date=datetime(2023, 10, 10, tzinfo=timezone.utc),
            t2_scene_id="S2B_2",
            t2_date=datetime(2023, 12, 9, tzinfo=timezone.utc),
        )
        self.session.add(invalid_run)
        with pytest.raises(IntegrityError):
            self.session.commit()
        self.session.rollback()

        # Invalid NDWI threshold (> 1.0)
        invalid_threshold_run = AnalysisRun(
            user_id=user.id,
            status="PROCESSING",
            data_provider="CDSE Sentinel-2 L2A",
            t1_scene_id="S2A_1",
            t1_date=datetime(2023, 10, 10, tzinfo=timezone.utc),
            t2_scene_id="S2B_2",
            t2_date=datetime(2023, 12, 9, tzinfo=timezone.utc),
            ndwi_threshold=1.5,
        )
        self.session.add(invalid_threshold_run)
        with pytest.raises(IntegrityError):
            self.session.commit()
        self.session.rollback()

    def test_water_metrics_uniqueness_and_null_percentage(self):
        """Verify 1:1 unique relationship and nullable percentage for zero baseline."""
        user = Profile(email=f"wm_user_{uuid.uuid4().hex[:6]}@example.com")
        self.session.add(user)
        self.session.commit()

        run = AnalysisRun(
            user_id=user.id,
            status="SUCCESS",
            data_provider="CDSE Sentinel-2 L2A",
            t1_scene_id="S2A_1",
            t1_date=datetime(2023, 10, 10, tzinfo=timezone.utc),
            t2_scene_id="S2B_2",
            t2_date=datetime(2023, 12, 9, tzinfo=timezone.utc),
        )
        self.session.add(run)
        self.session.commit()

        wm1 = WaterMetrics(
            analysis_run_id=run.id,
            common_valid_pixels=50000,
            common_valid_area_ha=500.0,
            pixel_size_m2=100.0,
            t1_water_pixels=0,
            t1_water_area_m2=0.0,
            t1_water_area_ha=0.0,
            t2_water_pixels=1500,
            t2_water_area_m2=150000.0,
            t2_water_area_ha=15.0,
            absolute_change_m2=150000.0,
            absolute_change_ha=15.0,
            percentage_change=None,  # undefined percentage change for zero baseline
            persistent_water_m2=0.0,
            persistent_water_ha=0.0,
            apparent_loss_m2=0.0,
            apparent_loss_ha=0.0,
            apparent_gain_m2=150000.0,
            apparent_gain_ha=15.0,
            limitation_statement="Baseline water was zero.",
        )
        self.session.add(wm1)
        self.session.commit()

        # Second water_metrics for same analysis_run_id must violate unique constraint
        wm2 = WaterMetrics(
            analysis_run_id=run.id,
            common_valid_pixels=50000,
            common_valid_area_ha=500.0,
            t1_water_pixels=100,
            t1_water_area_m2=10000.0,
            t1_water_area_ha=1.0,
            t2_water_pixels=100,
            t2_water_area_m2=10000.0,
            t2_water_area_ha=1.0,
            absolute_change_m2=0.0,
            absolute_change_ha=0.0,
            persistent_water_m2=10000.0,
            persistent_water_ha=1.0,
            apparent_loss_m2=0.0,
            apparent_loss_ha=0.0,
            apparent_gain_m2=0.0,
            apparent_gain_ha=0.0,
            limitation_statement="Duplicate test.",
        )
        self.session.add(wm2)
        with pytest.raises(IntegrityError):
            self.session.commit()
        self.session.rollback()

    def test_artifact_constraints(self):
        """Verify artifact_type and storage_bucket check constraints."""
        user = Profile(email=f"art_user_{uuid.uuid4().hex[:6]}@example.com")
        self.session.add(user)
        self.session.commit()

        run = AnalysisRun(
            user_id=user.id,
            status="SUCCESS",
            data_provider="CDSE Sentinel-2 L2A",
            t1_scene_id="S2A_1",
            t1_date=datetime(2023, 10, 10, tzinfo=timezone.utc),
            t2_scene_id="S2B_2",
            t2_date=datetime(2023, 12, 9, tzinfo=timezone.utc),
        )
        self.session.add(run)
        self.session.commit()

        # Invalid bucket
        invalid_art = AnalysisArtifact(
            analysis_run_id=run.id,
            artifact_type="MAP_PNG",
            storage_bucket="invalid_bucket",
            storage_path="runs/test.png",
            file_name="test.png",
            mime_type="image/png",
        )
        self.session.add(invalid_art)
        with pytest.raises(IntegrityError):
            self.session.commit()
        self.session.rollback()

        # Invalid artifact type
        invalid_art_type = AnalysisArtifact(
            analysis_run_id=run.id,
            artifact_type="EXECUTABLE_BINARY",
            storage_bucket="maps",
            storage_path="runs/bin",
            file_name="bin",
            mime_type="application/octet-stream",
        )
        self.session.add(invalid_art_type)
        with pytest.raises(IntegrityError):
            self.session.commit()
        self.session.rollback()

    def test_cascading_deletions(self):
        """Verify ON DELETE behavior: SET NULL on AOI, CASCADE on AnalysisRun, and CASCADE on Profile."""
        user = Profile(email=f"cascade_{uuid.uuid4().hex[:6]}@example.com")
        self.session.add(user)
        self.session.commit()

        wkt = "POLYGON((80.90 26.84, 80.92 26.84, 80.92 26.86, 80.90 26.86, 80.90 26.84))"
        aoi = AOI(
            user_id=user.id,
            name="Cascade Test AOI",
            geometry=WKTElement(wkt, srid=4326),
            area_km2=4.0,
            area_hectares=400.0,
            bbox=[80.90, 26.84, 80.92, 26.86],
            centroid=[80.91, 26.85],
            vertex_count=5,
        )
        self.session.add(aoi)
        self.session.commit()

        run = AnalysisRun(
            user_id=user.id,
            aoi_id=aoi.id,
            status="SUCCESS",
            data_provider="CDSE Sentinel-2 L2A",
            t1_scene_id="S2A_1",
            t1_date=datetime(2023, 10, 10, tzinfo=timezone.utc),
            t2_scene_id="S2B_2",
            t2_date=datetime(2023, 12, 9, tzinfo=timezone.utc),
        )
        self.session.add(run)
        self.session.commit()

        wm = WaterMetrics(
            analysis_run_id=run.id,
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
            limitation_statement="Cascade test.",
        )
        art = AnalysisArtifact(
            analysis_run_id=run.id,
            artifact_type="REPORT_PDF",
            storage_bucket="reports",
            storage_path="reports/test.pdf",
            file_name="test.pdf",
            mime_type="application/pdf",
        )
        self.session.add_all([wm, art])
        self.session.commit()

        # 1. Delete AOI -> AnalysisRun still exists, aoi_id is set to None (SET NULL)
        self.session.delete(aoi)
        self.session.commit()

        refreshed_run = self.session.scalar(select(AnalysisRun).where(AnalysisRun.id == run.id))
        assert refreshed_run is not None
        assert refreshed_run.aoi_id is None

        # 2. Delete AnalysisRun -> WaterMetrics and AnalysisArtifacts deleted (CASCADE)
        run_id = run.id
        self.session.delete(refreshed_run)
        self.session.commit()

        assert self.session.scalar(select(WaterMetrics).where(WaterMetrics.analysis_run_id == run_id)) is None
        assert len(self.session.scalars(select(AnalysisArtifact).where(AnalysisArtifact.analysis_run_id == run_id)).all()) == 0

        # 3. Delete Profile -> Cleans up completely
        self.session.delete(user)
        self.session.commit()
        assert self.session.scalar(select(Profile).where(Profile.id == user.id)) is None
