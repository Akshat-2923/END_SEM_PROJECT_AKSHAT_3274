"""AnalysisArtifact model storing external object storage metadata references."""

import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base

if TYPE_CHECKING:
    from src.database.models.analysis import AnalysisRun


class AnalysisArtifact(Base):
    """References generated raster outputs, figures, and reports stored in object storage."""

    __tablename__ = "analysis_artifacts"
    __table_args__ = (
        CheckConstraint(
            "artifact_type IN ('MAP_PNG', 'PANEL_PNG', 'REPORT_PDF', 'REPORT_CSV', 'RASTER_TIFF', 'THUMBNAIL_JPG')",
            name="ck_artifacts_type",
        ),
        CheckConstraint(
            "storage_bucket IN ('maps', 'reports', 'rasters')",
            name="ck_artifacts_bucket",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analysis_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    artifact_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    storage_bucket: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    storage_path: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )
    file_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    file_size_bytes: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True,
    )
    mime_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    # 90-day retention schedule target for ephemeral rasters
    expires_at: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    analysis_run: Mapped["AnalysisRun"] = relationship(
        "AnalysisRun",
        back_populates="artifacts",
    )

    def __repr__(self) -> str:
        return (
            f"<AnalysisArtifact id={self.id} type={self.artifact_type} "
            f"bucket={self.storage_bucket} file={self.file_name}>"
        )
