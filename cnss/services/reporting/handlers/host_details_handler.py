# ==============================================================================
# CnSS Host Details Subscription Handler
# Handles SQL execution for the 'host_details' subscription target.
# Provides real-time Rx/Tx packet rates for a specific host IP address.
#
# Rate Calculation Logic:
# - tx_per_sec: Packets where host_ip = src_ip (host is sending)
# - rx_per_sec: Packets where host_ip = dst_ip (host is receiving)
# This logic is universal and works for both LAN and WAN hosts.
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
    resolve_period_interval,
)

# --- Module Logger ---
logger = logging.getLogger(__name__)

# --- Period to Seconds Mapping ---
# Maps human-readable period strings to their duration in seconds.
# Used to convert packet COUNT(*) into per-second rates (tx_per_sec, rx_per_sec).
PERIOD_TO_SECONDS: Dict[str, int] = {
    "5m": 300,
    "15m": 900,
    "1h": 3600,
    "24h": 86400,
    "7d": 604800,
    "30d": 2592000,
}
DEFAULT_PERIOD = "5m"


# --- Host Details Handler ---
class HostDetailsHandler(BaseSubscriptionHandler):
    """
    Executes SQL queries for the 'host_details' subscription target.
    Provides real-time tx/rx packet rates for a specific host IP address
    over a configurable time period.
    """

    @property
    def target_name(self) -> str:
        """Identifier for this handler, matching SubscribeRequest.target."""
        return "host_details"

    async def execute(self, db_pool: asyncpg.Pool, request: SubscribeRequest) -> Optional[Dict[str, Any]]:
        """
        Executes the host details query and returns the formatted JSON result.

        Query Strategy:
        - Filter packet_flows by channel_id and time window
        - Find all packets where host_ip appears as src_ip OR dst_ip
        - Calculate tx_per_sec: COUNT(src_ip = host_ip) / period_seconds
        - Calculate rx_per_sec: COUNT(dst_ip = host_ip) / period_seconds

        :param db_pool: The asyncpg connection pool.
        :param request: The validated subscription request.
        :return: Dictionary with host_details_update payload, or None if host_ip missing.
        :raises DatabaseError: On query execution failures.
        """
        # --- Common Validation ---
        self._validate_request(request)

        # --- Parameter Extraction ---
        params = request.params
        channel_id = request.channel_id

        # host_ip is required for this target
        if not params.host_ip:
            logger.warning("[host_details] host_ip parameter is required but missing.")
            return None

        # Resolve period: validate against whitelist, fallback to default
        period = params.period if params.period in PERIOD_TO_SECONDS else DEFAULT_PERIOD
        interval_str = resolve_period_interval(period)
        period_seconds = PERIOD_TO_SECONDS[period]

        logger.debug(
            f"[host_details] Executing query for channel '{channel_id}', "
            f"host '{params.host_ip}' (period: {period}, seconds: {period_seconds})."
        )

        # --- Dynamic Parameter Tracking ---
        # ParameterizedQuery tracks $N placeholders as we add parameters dynamically.
        pq = ParameterizedQuery(start_index=1)

        # Fixed parameters: channel_id ($1), interval ($2), host_ip ($3), period_seconds ($4)
        channel_ph = pq.add_param(channel_id)
        interval_ph = pq.add_param(interval_str)
        host_ip_ph = pq.add_param(params.host_ip)
        pq.add_param(period_seconds)

        # --- Query Assembly ---
        # Simple aggregation query:
        # - Filter by channel_id and time window
        # - Find packets where host_ip is either src or dst
        # - Calculate tx/rx rates based on packet direction relative to host
        query = f"""
        SELECT
            COUNT(*) FILTER (WHERE src_ip = {host_ip_ph}::inet)::float / $4 AS tx_per_sec,
            COUNT(*) FILTER (WHERE dst_ip = {host_ip_ph}::inet)::float / $4 AS rx_per_sec
        FROM packet_flows
        WHERE channel_id = {channel_ph}
        AND time > NOW() - ({interval_ph}::text)::interval
        AND (src_ip = {host_ip_ph}::inet OR dst_ip = {host_ip_ph}::inet)
        """

        # --- Execution ---
        try:
            async with db_pool.acquire() as conn:
                row = await conn.fetchrow(query, *pq.get_params())

                # Handle case where no packets found for this host
                if row is None or (row["tx_per_sec"] == 0 and row["rx_per_sec"] == 0):
                    logger.debug(
                        f"[host_details] No activity found for host '{params.host_ip}' "
                        f"in channel '{channel_id}' over period '{period}'."
                    )
                    # Return zero rates instead of None to maintain consistent payload
                    return {
                        "type": "host_details_update",
                        "channel_id": channel_id,
                        "host_ip": params.host_ip,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "tx_per_sec": 0.0,
                        "rx_per_sec": 0.0,
                    }

                # --- Response Formatting ---
                result = {
                    "type": "host_details_update",
                    "channel_id": channel_id,
                    "host_ip": params.host_ip,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "tx_per_sec": float(row["tx_per_sec"]) if row["tx_per_sec"] else 0.0,
                    "rx_per_sec": float(row["rx_per_sec"]) if row["rx_per_sec"] else 0.0,
                }

                logger.debug(
                    f"[host_details] Success for host '{params.host_ip}' in channel '{channel_id}': "
                    f"tx={result['tx_per_sec']:.2f} pps, rx={result['rx_per_sec']:.2f} pps."
                )
                return result

        except asyncpg.PostgresError as e:
            logger.error(
                f"[host_details] Database error for host '{params.host_ip}' " f"in channel '{channel_id}': {e}",
                exc_info=True,
            )
            raise DatabaseError(message=f"Host details query failed for host '{params.host_ip}'.") from e
        except Exception as e:
            logger.error(
                f"[host_details] Unexpected error for host '{params.host_ip}' " f"in channel '{channel_id}': {e}",
                exc_info=True,
            )
            raise DatabaseError(message=f"Unexpected host details query failure for host '{params.host_ip}'.") from e
