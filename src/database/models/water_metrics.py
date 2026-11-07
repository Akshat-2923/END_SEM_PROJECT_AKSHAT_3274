"""WaterMetrics model storing quantitative hydrological change statistics."""

import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base

if TYPE_CHECKING:
    from src.database.models.analysis import AnalysisRun


class WaterMetrics(Base):
    """Stores quantitative surface water area metrics and multi-temporal transition data."""

    __tablename__ = "water_metrics"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analysis_runs.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # Comparison Grid Domain
    common_valid_pixels: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    common_valid_area_ha: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    pixel_size_m2: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=100.0,
        server_default="100.0",
    )

    # Earlier Observation T1
    t1_water_pixels: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    t1_water_area_m2: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    t1_water_area_ha: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    # Later Observation T2
    t2_water_pixels: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    t2_water_area_m2: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    t2_water_area_ha: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    # Summary Delta Metrics
    absolute_change_m2: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    absolute_change_ha: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    percentage_change: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,  # Safe handling for zero T1 baseline
    )

    # Hydrological Transition Components
    persistent_water_m2: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    persistent_water_ha: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    apparent_loss_m2: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    apparent_loss_ha: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    apparent_gain_m2: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    apparent_gain_ha: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    limitation_statement: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    analysis_run: Mapped["AnalysisRun"] = relationship(
        "AnalysisRun",
        back_populates="water_metrics",
    )

    def __repr__(self) -> str:
        return (
            f"<WaterMetrics id={self.id} analysis_id={self.analysis_run_id} "
            f"t1_ha={self.t1_water_area_ha} t2_ha={self.t2_water_area_ha} "
            f"net_change_ha={self.absolute_change_ha}>"
        )
