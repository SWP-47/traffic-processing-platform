# ==============================================================================
# CnSS UDP Data Contracts
# Pydantic models for validating and typing incoming UDP telemetry payloads
# from Communication Nodes (CN). Strictly enforces data type constraints.
# ==============================================================================

from typing import List

from pydantic import BaseModel, Field, IPvAnyAddress


# --- Packet Metadata Model ---
# Represents a single network packet's metadata captured by the CN.
# Note: The 'time' field is absent in the UDP payload and is assigned
# by the Ingestion Worker upon database insertion.
class PacketMeta(BaseModel):
    """
    Metadata for a single packet within a TelemetryBatch.
    """

    # Traffic direction: 0 for IN, 1 for OUT
    direction: int = Field(..., ge=0, le=1, description="Traffic direction: 0 for IN, 1 for OUT.")

    # Source and destination network endpoints
    src_ip: IPvAnyAddress = Field(..., description="Source IP address.")
    dst_ip: IPvAnyAddress = Field(..., description="Destination IP address.")
    src_port: int = Field(..., ge=0, le=65535, description="Source port number.")
    dst_port: int = Field(..., ge=0, le=65535, description="Destination port number.")


# --- Telemetry Batch Model ---
# Represents a batch of packets sent from a CN to the CnSS Ingestion Worker.
class TelemetryBatch(BaseModel):
    """
    A batch of telemetry data sent via UDP.
    """

    # Unique identifier of the channel (trusted assertion from CN)
    channel_id: str = Field(..., min_length=1, description="Unique identifier of the channel.")

    # Unix timestamp of the batch creation/completion at the CN side
    timestamp: int = Field(..., description="Unix timestamp of the batch in seconds.")

    # 64-bit sequence number for drop calculation and reset detection
    sequence: int = Field(..., description="64-bit sequence number for drop calculation.")

    # Aggregation window duration in milliseconds
    window_ms: int = Field(..., ge=0, description="Aggregation window duration in milliseconds.")

    # List of packet metadata. Can be empty for keep-alive batches
    packets: List[PacketMeta] = Field(default_factory=list, description="List of packet metadata.")
