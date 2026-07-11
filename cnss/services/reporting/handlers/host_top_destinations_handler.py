# ==============================================================================
# CnSS Host Top Destinations Subscription Handler
# Handles SQL execution for the 'host_top_destinations' subscription target.
# Provides top remote IPs that a specific host communicates with, including
# LAN/WAN classification based on traffic direction and src/dst roles.
#
# LAN/WAN Classification Logic:
# - WAN: IP appears as src_ip when direction=0 (IN) OR as dst_ip when direction=1 (OUT)
# - LAN: IP appears as dst_ip when direction=0 (IN) OR as src_ip when direction=1 (OUT)
#
# Architecture Reference: §2.2.2 (Dynamic SQL Execution), §4.4 (Subscription Targets)
# ==============================================================================
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import asyncpg

from core.contracts.subscriptions import SubscribeRequest
from core.exceptions import DatabaseError
from services.reporting.handlers.base import BaseSubscriptionHandler
from services.reporting.query_builder import (
    ParameterizedQuery,
    build_limit_param,
    build_offset,
    build_order_by,
    resolve_period_interval,
)

# --- Module Logger ---
logger = logging.getLogger(__name__)

# --- Default Period ---
# Default aggregation window in seconds if not specified in the subscription request.
# Set to 300 seconds (5 minutes) for a balance between responsiveness and stability.
DEFAULT_PERIOD_SEC = 300.0

# --- Sort By Whitelist ---
# Maps user-facing sort_by aliases to actual SQL column names from the aggregated CTE.
# Strict whitelisting prevents SQL injection via ORDER BY clause.
HOST_TOP_DESTINATIONS_SORT_WHITELIST: Dict[str, str] = {
    "ip": "remote_ip",
    "location": "location",
    "received": "received_per_sec",
    "last_seen": "last_seen",
}


# --- Host Top Destinations Handler ---
class HostTopDestinationsHandler(BaseSubscriptionHandler):
    """
    Executes SQL queries for the 'host_top_destinations' subscription target.
    Provides a paginated, sortable list of top remote IPs that a specific host
    communicates with, including LAN/WAN classification and traffic rates.
    """

    @property
    def target_name(self) -> str:
        """Identifier for this handler, matching SubscribeRequest.target."""
        return "host_top_destinations"

    async def execute(self, db_pool: asyncpg.Pool, request: SubscribeRequest) -> Optional[Dict[str, Any]]:
        """
        Executes the host top destinations query and returns the formatted JSON result.
        Query Strategy (2-stage CTE pipeline):
        1. host_flows CTE: Filters packet_flows for packets where host_ip participates,
           extracts remote_ip and classifies it as LAN/WAN based on direction and role.
        2. destination_stats CTE: Groups by remote_ip, computes received_per_sec,
           last_seen, and LAN/WAN classification.
        3. Final SELECT: Applies ORDER BY, LIMIT/OFFSET, and uses COUNT(*) OVER()
           to compute total_count for pagination metadata.

        :param db_pool: The asyncpg connection pool.
        :param request: The validated subscription request.
        :return: Dictionary with host_top_destinations_update payload, or None if host_ip missing.
        :raises DatabaseError: On query execution failures.
        """
        # --- Common Validation ---
        self._validate_request(request)

        # --- Parameter Extraction ---
        params = request.params
        channel_id = request.channel_id

        # host_ip is required for this target
        if not params.host_ip:
            logger.warning("[host_top_destinations] host_ip parameter is required but missing.")
            return None

        # Resolve period_sec: use provided value or fallback to default (300 seconds = 5 minutes)
        # Pydantic validates period_sec as float, so it's safe for SQL interpolation.
        period_sec = params.period_sec if params.period_sec and params.period_sec > 0 else DEFAULT_PERIOD_SEC
        interval_str = resolve_period_interval(period_sec)

        logger.debug(
            f"[host_top_destinations] Executing query for channel '{channel_id}', "
            f"host '{params.host_ip}' (period_sec: {period_sec}, interval: {interval_str})."
        )

        # --- Dynamic Parameter Tracking ---
        # ParameterizedQuery tracks $N placeholders as we add parameters dynamically.
        pq = ParameterizedQuery(start_index=1)

        # Fixed parameters: channel_id ($1), interval ($2), host_ip ($3)
        channel_ph = pq.add_param(channel_id)
        interval_ph = pq.add_param(interval_str)
        host_ip_ph = pq.add_param(params.host_ip)

        # --- ORDER BY, LIMIT, OFFSET ---
        # All use strict whitelisting / parameterized placeholders for safety.
        order_by_sql = build_order_by(params.sort_by, params.sort_order, HOST_TOP_DESTINATIONS_SORT_WHITELIST)
        limit_sql = build_limit_param(params.limit, pq)
        offset_sql = build_offset(params.offset, pq)

        # --- Query Assembly ---
        # 2-stage CTE pipeline ensures clean separation of concerns:
        # - host_flows: filters packets where host_ip participates, extracts remote_ip
        # - destination_stats: aggregates by remote_ip with LAN/WAN classification
        # - final SELECT: sorting, pagination, total_count
        #
        # IMPORTANT: period_sec is used directly in division for rate calculation.
        # Since Pydantic validates it as a numeric value (float), this is 100% safe
        # from SQL injection and supports arbitrary custom time windows.
        # --- Execution ---
        try:
            from core.db import db_fetch_host_top_destinations_data
            rows = await db_fetch_host_top_destinations_data(
                host_ip_ph,
                channel_ph,
                interval_ph,
                period_sec,
                order_by_sql,
                limit_sql,
                offset_sql,
                pq.get_params(),
                pool=db_pool,
            )

            # --- Result Formatting ---
            # Extract destinations and total_count from the paginated result set.
            # total_count is identical across all rows (window function),
            # so we read it once from the first row.
            destinations: list[Dict[str, Any]] = []
            total_count = 0

            for row in rows:
                total_count = int(row["total_count"])
                destinations.append(
                    {
                        "ip": str(row["remote_ip"]),
                        "location": row["location"],
                        "received_per_sec": float(row["received_per_sec"]),
                        "last_seen": (row["last_seen"].isoformat() if row["last_seen"] else None),
                    }
                )

            result = {
                "type": "host_top_destinations_update",
                "channel_id": channel_id,
                "host_ip": params.host_ip,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "total_count": total_count,
                "destinations": destinations,
            }

            logger.debug(
                f"[host_top_destinations] Success for host '{params.host_ip}' "
                f"in channel '{channel_id}': {len(destinations)} destinations returned "
                f"(total: {total_count})."
            )
            return result

        except asyncpg.PostgresError as e:
            logger.error(
                f"[host_top_destinations] Database error for host '{params.host_ip}' "
                f"in channel '{channel_id}': {e}",
                exc_info=True,
            )
            raise DatabaseError(message=f"Host top destinations query failed for host '{params.host_ip}'.") from e
        except Exception as e:
            logger.error(
                f"[host_top_destinations] Unexpected error for host '{params.host_ip}' "
                f"in channel '{channel_id}': {e}",
                exc_info=True,
            )
            raise DatabaseError(
                message=f"Unexpected host top destinations query failure for host '{params.host_ip}'."
            ) from e
