"""Spatial Area of Interest (AOI) model with PostGIS polygon geometry."""

import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base

if TYPE_CHECKING:
    from src.database.models.analysis import AnalysisRun
    from src.database.models.profile import Profile


class AOI(Base):
    """Geographical Area of Interest (AOI) polygon entity."""

    __tablename__ = "aois"
    __table_args__ = (
        CheckConstraint("area_km2 >= 0.10 AND area_km2 <= 100.00", name="ck_aois_area_bounds"),
        CheckConstraint("vertex_count >= 4 AND vertex_count <= 500", name="ck_aois_vertex_bounds"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # PostGIS Polygon Geometry in WGS84 (SRID 4326) with automatic GiST spatial indexing
    geometry = mapped_column(
        Geometry(geometry_type="POLYGON", srid=4326, spatial_index=True),
        nullable=False,
    )

    # Pre-calculated ellipsoidal area metrics (consistent with src/aoi_validation.py)
    area_km2: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    area_hectares: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    # Spatial Envelope metadata [min_lon, min_lat, max_lon, max_lat] and [centroid_lon, centroid_lat]
    bbox: Mapped[List[float]] = mapped_column(
        JSON,
        nullable=False,
    )
    centroid: Mapped[List[float]] = mapped_column(
        JSON,
        nullable=False,
    )
    vertex_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    is_public: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
        index=True,
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    profile: Mapped["Profile"] = relationship(
        "Profile",
        back_populates="aois",
    )
    analysis_runs: Mapped[List["AnalysisRun"]] = relationship(
        "AnalysisRun",
        back_populates="aoi",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<AOI id={self.id} name={self.name} area_km2={self.area_km2} user_id={self.user_id}>"
