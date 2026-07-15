# ==============================================================================
# CnSS Packet Flow ORM Model
# SQLAlchemy model for the 'packet_flows' TimescaleDB hypertable.
# Stores raw packet metadata partitioned by time for high-performance aggregation.
# ==============================================================================

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, Integer, SmallInteger, String, text
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, mapped_column

from core.models.base import Base


# --- Packet Flow Model ---
# Represents a single network packet's metadata captured by a Communication Node.
# This table is a TimescaleDB hypertable, partitioned by the 'time' column.
class PacketFlow(Base):
    """
    ORM model for the 'packet_flows' hypertable.
    Stores raw telemetry data with a composite primary key (id, time).
    """

    __tablename__ = "packet_flows"

    # Unique row identifier (BIGSERIAL in PostgreSQL)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="Unique row identifier")

    # Timestamp of the packet capture/ingestion (required for hypertable partitioning)
    time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True, nullable=False, comment="Timestamp of packet ingestion"
    )

    # Identifier of the channel this packet belongs to
    channel_id: Mapped[str] = mapped_column(String, nullable=False, comment="Channel identifier")

    # Traffic direction: 0 for IN, 1 for OUT
    direction: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="Traffic direction: 0 = IN, 1 = OUT")

    # Source and destination network endpoints
    src_ip: Mapped[str] = mapped_column(INET, nullable=False, comment="Source IP address")

    dst_ip: Mapped[str] = mapped_column(INET, nullable=False, comment="Destination IP address")

    src_port: Mapped[int] = mapped_column(Integer, nullable=False, comment="Source port number")

    dst_port: Mapped[int] = mapped_column(Integer, nullable=False, comment="Destination port number")

    # Network protocol (e.g., TCP, UDP, ICMP). Defaults to 'UNKNOWN' for backward compatibility.
    protocol: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="UNKNOWN", comment="Network protocol identifier"
    )

    # Packet size in bytes
    size: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default="0", comment="Packet size in bytes"
    )

    # --- Indexes ---
    # Composite index for fast channel-specific time-series queries
    __table_args__ = (
        Index(
            "idx_channel_time",
            "channel_id",
            text("time DESC"),
        ),
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"<PacketFlow(id={self.id}, channel_id={self.channel_id}, time={self.time})>"
