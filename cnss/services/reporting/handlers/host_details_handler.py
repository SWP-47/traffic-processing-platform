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

# --- Default Period ---
# Default aggregation window in seconds if not specified in the subscription request.
# Set to 300 seconds (5 minutes) for a balance between responsiveness and stability.
DEFAULT_PERIOD_SEC = 300.0


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
        - Calculate tx_per_sec: COUNT(src_ip = host_ip) / period_sec
        - Calculate rx_per_sec: COUNT(dst_ip = host_ip) / period_sec

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

        # Resolve period_sec: use provided value or fallback to default (300 seconds = 5 minutes)
        # Pydantic validates period_sec as float, so it's safe for SQL interpolation.
        period_sec = params.period_sec if params.period_sec and params.period_sec > 0 else DEFAULT_PERIOD_SEC
        interval_str = resolve_period_interval(period_sec)

        logger.debug(
            f"[host_details] Executing query for channel '{channel_id}', "
            f"host '{params.host_ip}' (period_sec: {period_sec}, interval: {interval_str})."
        )

        # --- Dynamic Parameter Tracking ---
        # ParameterizedQuery tracks $N placeholders as we add parameters dynamically.
        pq = ParameterizedQuery(start_index=1)

        # Fixed parameters: channel_id ($1), interval ($2), host_ip ($3)
        channel_ph = pq.add_param(channel_id)
        interval_ph = pq.add_param(interval_str)
        host_ip_ph = pq.add_param(params.host_ip)

        # --- Query Assembly ---
        # Simple aggregation query:
        # - Filter by channel_id and time window
        # - Find packets where host_ip is either src or dst
        # - Calculate tx/rx rates based on packet direction relative to host
        #
        # IMPORTANT: period_sec is used directly in division for rate calculation.
        # Since Pydantic validates it as a numeric value (float), this is 100% safe
        # from SQL injection and supports arbitrary custom time windows.
        # --- Execution ---
        try:
            from core.db import db_fetch_host_details_data

            row = await db_fetch_host_details_data(
                host_ip_ph,
                channel_ph,
                interval_ph,
                period_sec,
                pq.get_params(),
                pool=db_pool,
            )

            # Handle case where no packets found for this host
            if row is None or (row["tx_per_sec"] == 0 and row["rx_per_sec"] == 0):
                logger.debug(
                    f"[host_details] No activity found for host '{params.host_ip}' "
                    f"in channel '{channel_id}' over period {period_sec}s."
                )
                # Return zero rates instead of None to maintain consistent payload
                return {
                    "type": "host_details_update",
                    "channel_id": channel_id,
                    "host_ip": params.host_ip,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "tx_per_sec": 0.0,
                    "rx_per_sec": 0.0,
                    "tx_bytes_per_sec": 0.0,
                    "rx_bytes_per_sec": 0.0,
                }

            # --- Response Formatting ---
            result = {
                "type": "host_details_update",
                "channel_id": channel_id,
                "host_ip": params.host_ip,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "tx_per_sec": float(row["tx_per_sec"]) if row["tx_per_sec"] else 0.0,
                "rx_per_sec": float(row["rx_per_sec"]) if row["rx_per_sec"] else 0.0,
                "tx_bytes_per_sec": float(row.get("tx_bytes_per_sec", 0.0)) if row.get("tx_bytes_per_sec") else 0.0,
                "rx_bytes_per_sec": float(row.get("rx_bytes_per_sec", 0.0)) if row.get("rx_bytes_per_sec") else 0.0,
            }

            logger.debug(
                f"[host_details] Success for host '{params.host_ip}' in channel '{channel_id}': "
                f"tx={result['tx_per_sec']:.2f} pps ({result['tx_bytes_per_sec']:.2f} bps), "
                f"rx={result['rx_per_sec']:.2f} pps ({result['rx_bytes_per_sec']:.2f} bps)."
            )
            return result

        except asyncpg.PostgresError as e:
            logger.error(
                f"[host_details] Database error for host '{params.host_ip}' in channel '{channel_id}': {e}",
                exc_info=True,
            )
            raise DatabaseError(message=f"Host details query failed for host '{params.host_ip}'.") from e
        except Exception as e:
            logger.error(
                f"[host_details] Unexpected error for host '{params.host_ip}' in channel '{channel_id}': {e}",
                exc_info=True,
            )
            raise DatabaseError(message=f"Unexpected host details query failure for host '{params.host_ip}'.") from e
