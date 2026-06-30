# ==============================================================================
# CnSS Channel ORM Model
# SQLAlchemy model for the persistent channel registry.
# Maps to the 'channels' table in TimescaleDB, storing metadata and state
# that is periodically synchronized by the Reporting Worker.
# ==============================================================================

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from core.models.base import Base


# --- Channel Model ---
# Represents a network channel (bridge) monitored by the CnSS.
# While real-time status is served from Redis for sub-millisecond latency,
# this table maintains the persistent historical record and audit trail.
class Channel(Base):
    """
    ORM model for the 'channels' table.
    Acts as the persistent registry for channel metadata and aggregated state.
    """

    __tablename__ = "channels"

    # Unique identifier of the channel (trusted assertion from Communication Node)
    channel_id: Mapped[str] = mapped_column(String, primary_key=True, comment="Unique identifier of the channel")

    # Timestamp of the channel's first discovery/creation in the system
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Timestamp when the channel was first registered",
    )

    # Timestamp of the last successfully processed telemetry batch.
    # Nullable because a newly created channel might not have received traffic yet.
    last_activity_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Timestamp of the last received telemetry batch"
    )

    # Accumulated count of dropped packets (updated by Reporting Worker)
    dropped: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False, comment="Total count of dropped packets"
    )

    # Activity flag toggled by the Reporting Worker based on last_activity_at.
    # False if no activity for > 5 seconds, True otherwise.
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
        comment="Indicates if the channel is currently active",
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"<Channel(channel_id={self.channel_id}, is_active={self.is_active})>"
