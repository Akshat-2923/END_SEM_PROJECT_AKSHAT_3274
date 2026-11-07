"""AnalysisRun model recording satellite pipeline execution metadata and status."""

import uuid
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base

if TYPE_CHECKING:
    from src.database.models.aoi import AOI
    from src.database.models.artifact import AnalysisArtifact
    from src.database.models.profile import Profile
    from src.database.models.water_metrics import WaterMetrics


class AnalysisRun(Base):
    """AnalysisRun tracks multi-temporal Sentinel-2 pipeline execution and metadata."""

    __tablename__ = "analysis_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('QUEUED', 'PROCESSING', 'SUCCESS', 'FAILED')",
            name="ck_analysis_runs_status",
        ),
        CheckConstraint(
            "ndwi_threshold >= -1.0 AND ndwi_threshold <= 1.0",
            name="ck_analysis_runs_threshold",
        ),
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
    aoi_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("aois.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="QUEUED",
        server_default="QUEUED",
        index=True,
    )
    data_provider: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    is_real_data: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    # Observation T1 (Earlier)
    t1_scene_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    t1_date: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    t1_cloud_cover: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )

    # Observation T2 (Later)
    t2_scene_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    t2_date: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    t2_cloud_cover: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )

    ndwi_threshold: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        server_default="0.0",
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    execution_duration_sec: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    execution_timestamp: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
        nullable=False,
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
        back_populates="analysis_runs",
    )
    aoi: Mapped[Optional["AOI"]] = relationship(
        "AOI",
        back_populates="analysis_runs",
    )
    water_metrics: Mapped[Optional["WaterMetrics"]] = relationship(
        "WaterMetrics",
        back_populates="analysis_run",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    artifacts: Mapped[List["AnalysisArtifact"]] = relationship(
        "AnalysisArtifact",
        back_populates="analysis_run",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return (
            f"<AnalysisRun id={self.id} status={self.status} "
            f"t1={self.t1_date} t2={self.t2_date} user_id={self.user_id}>"
        )
