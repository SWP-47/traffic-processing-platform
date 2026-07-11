# ==============================================================================
# CnSS Telemetry Subscription Handler
# Handles SQL execution for the 'telemetry' subscription target.
# Queries the TimescaleDB continuous aggregate 'telemetry_1s' to provide
# real-time packet rate metrics (packets_in, packets_out) for a channel.
#
# IMPORTANT: Continuous Aggregate Stability
# The 'telemetry_1s' view has a refresh policy with:
#   - start_offset => 5 seconds (buckets within last 5s are "live" and may be recalculated)
#   - end_offset => 1 second (the current incomplete bucket is excluded)
# This means:
#   - Buckets in [NOW-5s, NOW-1s] are "preliminary" and may increase if late packets arrive.
#   - Buckets older than NOW-5s are "stable" and will not change.
# For window_sec <= 5s, we read only closed buckets but accept that values may be refined.
# For long-term statistics, the sum will converge as all buckets stabilize.
#
# IMPORTANT: Accurate Rate Calculation
# Since telemetry_1s contains discrete 1-second buckets, the actual time window
# may differ from the requested window_sec. We use the actual bucket count from
# the database to calculate packets_per_sec, ensuring accurate statistics even
# when window_sec is not a whole number (e.g., 1.5s reads 2 buckets = 2s actual).
#
# Architecture Reference: §2.2.2 (Dynamic SQL Execution), §3.1 (Continuous Aggregates)
# ==============================================================================

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import asyncpg

from core.contracts.subscriptions import SubscribeRequest
from core.exceptions import DatabaseError
from services.reporting.handlers.base import BaseSubscriptionHandler

# --- Module Logger ---
logger = logging.getLogger(__name__)

# --- Continuous Aggregate Policy Constants ---
# These values MUST match the TimescaleDB continuous aggregate policy defined in migrations.
# They determine the "stability window" for telemetry data.

# end_offset: The most recent bucket is excluded because it's still being filled.
# We always read buckets up to NOW() - 1 second to ensure we only see closed buckets.
CONTINUOUS_AGG_END_OFFSET_SEC = 1.0

# start_offset: Buckets within the last 5 seconds may be recalculated if late packets arrive.
# For window_sec <= 5s, we accept that values are "preliminary" and may be refined.
# For window_sec > 5s, part of the window will be in the "stable" zone.
CONTINUOUS_AGG_START_OFFSET_SEC = 5.0

# --- Default Telemetry Settings ---
# Default aggregation window if not specified in the subscription request.
# Set to 1.0 second for real-time speed metrics.
DEFAULT_WINDOW_SEC = 1.0

# Minimum allowed window size.
# Windows smaller than 1 second may return 0 packets (no buckets available).
MIN_WINDOW_SEC = 0.1


# --- Telemetry Handler ---
class TelemetryHandler(BaseSubscriptionHandler):
    """
    Executes SQL queries for the 'telemetry' subscription target.

    Combines the persistent 'channels' registry with the real-time
    'telemetry_1s' continuous aggregate to produce a unified telemetry update.
    Strictly avoids sorting or heavy grouping, focusing purely on fast
    window-based aggregation for real-time speed metrics.
    """

    @property
    def target_name(self) -> str:
        """Identifier for this handler, matching SubscribeRequest.target."""
        return "telemetry"

    async def execute(self, db_pool: asyncpg.Pool, request: SubscribeRequest) -> Optional[Dict[str, Any]]:
        """
        Executes the telemetry aggregation query and returns the formatted JSON result.

        Query Strategy:
        - LEFT JOIN 'channels' with 'telemetry_1s' to include inactive channels.
        - Time window logic:
          * Upper bound: NOW() - end_offset (1s) to read only CLOSED buckets.
          * Lower bound: NOW() - window_sec - end_offset to ensure approximately window_sec duration.
        - Buckets within [NOW-5s, NOW-1s] are "preliminary" and may be recalculated.
        - Calculate packets_per_sec based on ACTUAL bucket count from database,
          not the requested window_sec, to ensure accurate statistics.

        :param db_pool: The asyncpg connection pool.
        :param request: The validated subscription request.
        :return: Dictionary with telemetry_update payload, or None if channel missing.
        """
        # --- Common Validation ---
        self._validate_request(request)

        # --- Parameter Extraction ---
        params = request.params
        window_sec = params.window_sec if params.window_sec is not None else DEFAULT_WINDOW_SEC

        # Validate window_sec to prevent division by zero or negative values
        if window_sec < MIN_WINDOW_SEC:
            logger.warning(
                f"[telemetry] window_sec={window_sec} is below minimum {MIN_WINDOW_SEC}. "
                f"Using default {DEFAULT_WINDOW_SEC}s."
            )
            window_sec = DEFAULT_WINDOW_SEC

        channel_id = request.channel_id

        logger.debug(
            f"[telemetry] Executing query for channel '{channel_id}' "
            f"(window: {window_sec}s, end_offset: {CONTINUOUS_AGG_END_OFFSET_SEC}s)."
        )

        # --- Execution ---
        try:
            from core.db import db_fetch_telemetry_data
            row = await db_fetch_telemetry_data(channel_id, window_sec, pool=db_pool)

            if row is None:
                logger.debug(f"[telemetry] Channel '{channel_id}' not found in registry.")
                return None

            # --- Metric Calculation ---
            total_in = int(row["total_in"])
            total_out = int(row["total_out"])
            bucket_count = int(row["bucket_count"])

            # --- Accurate Rate Calculation ---
            # Use actual bucket count as the real time window.
            # Each bucket in telemetry_1s represents exactly 1 second.
            # This ensures accurate statistics even when window_sec is not a whole number.
            if bucket_count == 0:
                # No buckets available (e.g., window_sec too small or no data)
                pps_in = 0
                pps_out = 0
                actual_window_sec = 0.0
                logger.debug(
                    f"[telemetry] No buckets found for channel '{channel_id}'. " f"Requested window: {window_sec}s."
                )
            else:
                # Each bucket = 1 second, so bucket_count = actual time window in seconds
                actual_window_sec = float(bucket_count)
                pps_in = int(total_in / actual_window_sec)
                pps_out = int(total_out / actual_window_sec)
                logger.debug(
                    f"[telemetry] Calculated rates using {bucket_count} bucket(s) "
                    f"(actual window: {actual_window_sec}s, requested: {window_sec}s)."
                )

            # Timestamps for the payload
            now = datetime.now(timezone.utc)
            latest_bucket = row["latest_bucket"]

            # --- Response Formatting ---
            result = {
                "type": "telemetry_update",
                "channel_id": channel_id,
                "is_active": row["is_active"],
                "window_ms": int(actual_window_sec * 1000),  # Actual window
                "dropped_batches": int(row["dropped"]),
                "metrics": {
                    "direction_out": {
                        "packets_per_sec": pps_out,
                        "packets": total_out,
                    },
                    "direction_in": {
                        "packets_per_sec": pps_in,
                        "packets": total_in,
                    },
                },
                "timestamp": latest_bucket.isoformat() if latest_bucket else now.isoformat(),
                "received_at": now.isoformat(),
            }

            logger.debug(
                f"[telemetry] Success for '{channel_id}': "
                f"in={total_in} ({pps_in} pps), out={total_out} ({pps_out} pps) "
                f"over {actual_window_sec}s."
            )
            return result

        except asyncpg.PostgresError as e:
            logger.error(
                f"[telemetry] Database error for channel '{channel_id}': {e}",
                exc_info=True,
            )
            raise DatabaseError(message=f"Telemetry query failed for channel '{channel_id}'.") from e
        except Exception as e:
            logger.error(
                f"[telemetry] Unexpected error for channel '{channel_id}': {e}",
                exc_info=True,
            )
            raise DatabaseError(message=f"Unexpected telemetry query failure for channel '{channel_id}'.") from e
