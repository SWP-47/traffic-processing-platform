# ==============================================================================
# CnSS Historical Data REST API Routes
# Handles lazy-loading of time-series telemetry and host-specific Rx/Tx data
# for the Management User Interface (MUI) line charts.
# Dynamically calculates optimal time_bucket intervals and ensures continuous
# time-series output by filling empty buckets with zero-values.
# ==============================================================================

from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Path, Query

from core.contracts.auth import TokenPayload
from core.database import get_db_pool
from core.exceptions import ResourceNotFoundError, ValidationError
from services.api.deps import get_current_user, require_channel_access
from services.api.schemas import (
    ChannelHistoryResponse,
    HistoryPoint,
    HostHistoryPoint,
    HostHistoryResponse,
)
from core.config import settings

# --- Router Configuration ---
# Grouped under /api/v1 prefix. Tags provide OpenAPI documentation grouping.
router = APIRouter(prefix="/api/v1", tags=["History"])

# --- Constants & Mappings ---
# Data retention period in days (strictly matches TimescaleDB retention policy).
RETENTION_DAYS = settings.retention_days

# Dynamically calculate optimal time_bucket interval based on period (seconds).
# Maps human-readable period strings to the bucket size in seconds.
PERIOD_BUCKET_SEC = {
    "1h": 3,
    "24h": 60,
    "7d": 7 * 60,
    "30d": 30 * 60,
}

# Maps human-readable period strings to PostgreSQL INTERVAL literals.
PERIOD_SQL_MAP = {
    "1h": "1 hour",
    "24h": "24 hours",
    "7d": "7 days",
    "30d": "30 days",
}

# Maps human-readable period strings to Python timedelta for validation.
PERIOD_DELTAS = {
    "1h": timedelta(hours=1),
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
}


# --- Helper Functions ---
def _validate_time_range(start_time: datetime, period: str) -> tuple[datetime, datetime]:
    """
    Validates the requested time range against business rules and data retention.
    Returns the validated (start_time, end_time) tuple.
    Raises ValidationError (400) if constraints are violated.
    """
    now = datetime.now(timezone.utc)
    
    # Ensure start_time is not in the future
    if start_time > now:
        raise ValidationError(
            error_code="bad_request",
            message="start_time cannot be in the future."
        )
    
    # Calculate end_time based on period
    end_time = start_time + PERIOD_DELTAS[period]
    
    # Ensure the requested range does not exceed the data retention policy
    retention_cutoff = now - timedelta(days=RETENTION_DAYS)
    if start_time < retention_cutoff:
        raise ValidationError(
            error_code="bad_request",
            message=f"Requested time range exceeds data retention period ({RETENTION_DAYS} days)."
        )
        
    return start_time, end_time


# ==============================================================================
# GET /api/v1/channel/{channel_id}/history
# ==============================================================================
@router.get("/channel/{channel_id}/history", response_model=ChannelHistoryResponse)
async def get_channel_history(
    channel_id: str = Depends(require_channel_access("channel_id")),
    period: Literal["1h", "24h", "7d", "30d"] = Query(..., description="Duration of the time window."),
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
    if start_time is None:
        # Default to now - period
        start_time = now - PERIOD_DELTAS[period]
    
    # Ensure start_time is timezone-aware (UTC) to prevent DB comparison errors
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)
        
    validated_start, validated_end = _validate_time_range(start_time, period)
    interval_sec = PERIOD_BUCKET_SEC[period]
    
    # --- Channel Existence Check ---
    db_pool = get_db_pool()
    async with db_pool.acquire() as conn:
        channel_row = await conn.fetchrow(
            "SELECT 1 FROM channels WHERE channel_id = $1",
            channel_id
        )
    if not channel_row:
        raise ResourceNotFoundError(message=f"Channel '{channel_id}' not found.")

    # --- SQL Query Execution ---
    # Uses generate_series to create a continuous timeline with buckets aligned to start_time.
    # For each bucket, we manually compute the range [bucket_start, bucket_end) and aggregate
    # telemetry_1s data within that range. This avoids time_bucket misalignment issues.
    query = """
    WITH time_buckets AS (
        SELECT generate_series($1::timestamptz, $2::timestamptz, ($3::int || ' seconds')::interval) AS bucket_start
    ),
    aggregated AS (
        SELECT
            tb.bucket_start,
            SUM(t.packets_in) AS packets_in,
            SUM(t.packets_out) AS packets_out
        FROM time_buckets tb
        LEFT JOIN telemetry_1s t
            ON t.channel_id = $4
            AND t.bucket >= tb.bucket_start
            AND t.bucket < tb.bucket_start + ($3::int || ' seconds')::interval
        GROUP BY tb.bucket_start
    )
    SELECT
        a.bucket_start AS timestamp,
        COALESCE(a.packets_in, 0) / $3::float AS packets_in_per_sec,
        COALESCE(a.packets_out, 0) / $3::float AS packets_out_per_sec,
        (COALESCE(a.packets_in, 0) + COALESCE(a.packets_out, 0)) > 0 AS is_active
    FROM aggregated a
    ORDER BY a.bucket_start;
    """
    
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            query,
            validated_start,
            validated_end,
            interval_sec,
            channel_id
        )
        
    # --- Response Formatting ---
    points = [
        HistoryPoint(
            timestamp=row["timestamp"],
            packets_in_per_sec=float(row["packets_in_per_sec"]),
            packets_out_per_sec=float(row["packets_out_per_sec"]),
            is_active=row["is_active"],
        )
        for row in rows
    ]
    
    return ChannelHistoryResponse(
        channel_id=channel_id,
        period=period,
        start_time=validated_start,
        end_time=validated_end,
        interval_sec=interval_sec,
        points=points,
    )


# ==============================================================================
# GET /api/v1/channel/{channel_id}/hosts/{host_ip}/history
# ==============================================================================
@router.get(
    "/channel/{channel_id}/hosts/{host_ip}/history", 
    response_model=HostHistoryResponse
)
async def get_host_history(
    channel_id: str = Depends(require_channel_access("channel_id")),
    host_ip: str = Path(..., description="IP address of the host (IPv4/IPv6)."),
    period: Literal["1h", "24h", "7d", "30d"] = Query(..., description="Duration of the time window."),
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
        start_time = now - PERIOD_DELTAS[period]
    
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)
        
    validated_start, validated_end = _validate_time_range(start_time, period)
    interval_sec = PERIOD_BUCKET_SEC[period]
    
    # --- Channel Existence Check ---
    db_pool = get_db_pool()
    async with db_pool.acquire() as conn:
        channel_row = await conn.fetchrow(
            "SELECT 1 FROM channels WHERE channel_id = $1",
            channel_id
        )
    if not channel_row:
        raise ResourceNotFoundError(message=f"Channel '{channel_id}' not found.")

    # --- SQL Query Execution ---
    # Queries raw packet_flows to extract per-host metrics.
    # Uses generate_series to create a continuous timeline with buckets aligned to start_time.
    # For each bucket, we manually compute the range [bucket_start, bucket_end) and aggregate
    # packet_flows data within that range. This avoids time_bucket misalignment issues.
    # Rx/Tx logic: dst_ip = host means IN (receiving), src_ip = host means OUT (sending).
    # 
    # IMPORTANT TYPE INFERENCE FIX:
    # We must explicitly cast $3 to ::int BEFORE concatenation (i.e., $3::int || ' seconds').
    # Without this, asyncpg's query parser sees "$3 || ' seconds'" and incorrectly infers 
    # that $3 is of type 'text', causing a TypeError when we pass an integer from Python.
    query = """
    WITH time_buckets AS (
        SELECT generate_series($1::timestamptz, $2::timestamptz, ($3::int || ' seconds')::interval) AS bucket_start
    ),
    aggregated AS (
        SELECT
            tb.bucket_start,
            COUNT(*) FILTER (WHERE pf.dst_ip = $4::inet) AS packets_in,
            COUNT(*) FILTER (WHERE pf.src_ip = $4::inet) AS packets_out
        FROM time_buckets tb
        LEFT JOIN packet_flows pf
            ON pf.channel_id = $5
            AND pf.time >= tb.bucket_start
            AND pf.time < tb.bucket_start + ($3::int || ' seconds')::interval
            AND (pf.src_ip = $4::inet OR pf.dst_ip = $4::inet)
        GROUP BY tb.bucket_start
    )
    SELECT
        a.bucket_start AS timestamp,
        COALESCE(a.packets_in, 0) / $3::float AS packets_in_per_sec,
        COALESCE(a.packets_out, 0) / $3::float AS packets_out_per_sec
    FROM aggregated a
    ORDER BY a.bucket_start;
    """
    
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            query,
            validated_start,
            validated_end,
            interval_sec,
            host_ip,
            channel_id
        )
        
    # --- Response Formatting ---
    points = [
        HostHistoryPoint(
            timestamp=row["timestamp"],
            packets_in_per_sec=float(row["packets_in_per_sec"]),
            packets_out_per_sec=float(row["packets_out_per_sec"]),
        )
        for row in rows
    ]
    
    return HostHistoryResponse(
        channel_id=channel_id,
        host_ip=host_ip,
        period=period,
        start_time=validated_start,
        end_time=validated_end,
        interval_sec=interval_sec,
        points=points,
    )