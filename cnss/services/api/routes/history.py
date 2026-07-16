# ==============================================================================
# CnSS Historical Data REST API Routes
# Handles lazy-loading of time-series telemetry and host-specific Rx/Tx data
# for the Management User Interface (MUI) line charts.
# Dynamically calculates optimal time_bucket intervals and ensures continuous
# time-series output by filling empty buckets with zero-values.
# ==============================================================================
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Path, Query

from core.config import settings
from core.contracts.auth import TokenPayload
from core.db import db_channel_exists, db_fetch_channel_history, db_fetch_host_history
from core.exceptions import ResourceNotFoundError, ValidationError
from services.api.deps import get_current_user, require_channel_access
from services.api.schemas import (
    ChannelHistoryResponse,
    HistoryPoint,
    HostHistoryPoint,
    HostHistoryResponse,
)

# --- Router Configuration ---
# Grouped under /api/v1 prefix. Tags provide OpenAPI documentation grouping.
router = APIRouter(prefix="/api/v1", tags=["History"])

# --- Constants ---
# Data retention period in days (strictly matches TimescaleDB retention policy).
RETENTION_DAYS = settings.retention_days


# --- Helper Functions ---
def calculate_optimal_bucket(period_sec: int, target_points: int = 1000) -> int:
    """
    Dynamically calculates the optimal time_bucket size in seconds
    to return approximately `target_points` on the chart.
    Snaps to logical time steps for cleaner chart rendering.
    """
    # Calculate raw bucket size to hit the target point count
    raw_bucket = max(1, period_sec // target_points)

    # Logical time steps (in seconds) for snapping
    logical_steps = [1, 2, 3, 5, 6, 8, 10, 15, 20, 30, 40, 60, 100, 200, 300, 400, 600, 1800, 3600]

    # Find the first logical step that is >= raw_bucket
    for step in logical_steps:
        if raw_bucket <= step:
            return step

    # For very large periods (e.g., 30 days), snap to hourly boundaries
    return max(3600, (raw_bucket // 3600) * 3600)


def _validate_time_range(start_time: datetime, period_sec: int) -> tuple[datetime, datetime]:
    """
    Validates the requested time range against business rules and data retention.
    Returns the validated (start_time, end_time) tuple.
    Raises ValidationError (400) if constraints are violated.
    """
    now = datetime.now(timezone.utc)

    # Ensure start_time is not in the future
    if start_time > now:
        raise ValidationError(error_code="bad_request", message="start_time cannot be in the future.")

    # Calculate end_time based on the numeric period in seconds
    end_time = start_time + timedelta(seconds=period_sec)

    # Ensure the requested range does not exceed the data retention policy
    retention_cutoff = now - timedelta(days=RETENTION_DAYS)
    if start_time < retention_cutoff:
        raise ValidationError(
            error_code="bad_request",
            message=f"Requested time range exceeds data retention period ({RETENTION_DAYS} days).",
        )
    return start_time, end_time


# ==============================================================================
# GET /api/v1/channel/{channel_id}/history
# ==============================================================================
@router.get("/channel/{channel_id}/history", response_model=ChannelHistoryResponse)
async def get_channel_history(
    channel_id: str = Depends(require_channel_access("channel_id")),
    period_sec: int = Query(..., gt=0, description="Duration of the time window in seconds."),
    start_time: Optional[datetime] = Query(None, description="Start of the time range (ISO 8601)."),
    current_user: TokenPayload = Depends(get_current_user),
) -> ChannelHistoryResponse:
    """
    Lazy-loads historical telemetry data for the Channel Line Chart.
    Dynamically calculates the optimal time_bucket interval and ensures
    continuous time-series output by filling empty buckets with zero-values.
    """
    # --- Time Range Validation & Defaults ---
    now = datetime.now(timezone.utc)

    # Default to now - period_sec if start_time is not provided
    if start_time is None:
        start_time = now - timedelta(seconds=period_sec)

    # Ensure start_time is timezone-aware (UTC) to prevent DB comparison errors
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)

    validated_start, validated_end = _validate_time_range(start_time, period_sec)

    # Calculate optimal bucket size dynamically based on the requested period
    interval_sec = calculate_optimal_bucket(period_sec)

    # --- Channel Existence Check ---
    if not await db_channel_exists(channel_id):
        raise ResourceNotFoundError(message=f"Channel '{channel_id}' not found.")

    # --- SQL Query Execution ---
    rows = await db_fetch_channel_history(channel_id, validated_start, validated_end, interval_sec)

    # --- Response Formatting ---
    points = [
        HistoryPoint(
            timestamp=row["timestamp"],
            packets_in_per_sec=float(row["packets_in_per_sec"]),
            packets_out_per_sec=float(row["packets_out_per_sec"]),
            bytes_in_per_sec=float(row.get("bytes_in_per_sec", 0.0)),
            bytes_out_per_sec=float(row.get("bytes_out_per_sec", 0.0)),
            is_active=row["is_active"],
        )
        for row in rows
    ]

    return ChannelHistoryResponse(
        channel_id=channel_id,
        period_sec=period_sec,
        start_time=validated_start,
        end_time=validated_end,
        interval_sec=interval_sec,
        points=points,
    )


# ==============================================================================
# GET /api/v1/channel/{channel_id}/hosts/{host_ip}/history
# ==============================================================================
@router.get("/channel/{channel_id}/hosts/{host_ip}/history", response_model=HostHistoryResponse)
async def get_host_history(
    channel_id: str = Depends(require_channel_access("channel_id")),
    host_ip: str = Path(..., description="IP address of the host (IPv4/IPv6)."),
    period_sec: int = Query(..., gt=0, description="Duration of the time window in seconds."),
    start_time: Optional[datetime] = Query(None, description="Start of the time range (ISO 8601)."),
    current_user: TokenPayload = Depends(get_current_user),
) -> HostHistoryResponse:
    """
    Lazy-loads historical Rx/Tx rate data for a specific Host Line Chart.
    Queries the raw packet_flows hypertable since continuous aggregates
    do not store per-host IP breakdowns.
    """
    # --- Time Range Validation & Defaults ---
    now = datetime.now(timezone.utc)

    if start_time is None:
        start_time = now - timedelta(seconds=period_sec)

    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)

    validated_start, validated_end = _validate_time_range(start_time, period_sec)

    # Calculate optimal bucket size dynamically based on the requested period
    interval_sec = calculate_optimal_bucket(period_sec)

    # --- Channel Existence Check ---
    if not await db_channel_exists(channel_id):
        raise ResourceNotFoundError(message=f"Channel '{channel_id}' not found.")

    # --- SQL Query Execution ---
    rows = await db_fetch_host_history(channel_id, host_ip, validated_start, validated_end, interval_sec)

    # --- Response Formatting ---
    points = [
        HostHistoryPoint(
            timestamp=row["timestamp"],
            packets_in_per_sec=float(row["packets_in_per_sec"]),
            packets_out_per_sec=float(row["packets_out_per_sec"]),
            bytes_in_per_sec=float(row.get("bytes_in_per_sec", 0.0)),
            bytes_out_per_sec=float(row.get("bytes_out_per_sec", 0.0)),
        )
        for row in rows
    ]

    return HostHistoryResponse(
        channel_id=channel_id,
        host_ip=host_ip,
        period_sec=period_sec,
        start_time=validated_start,
        end_time=validated_end,
        interval_sec=interval_sec,
        points=points,
    )
