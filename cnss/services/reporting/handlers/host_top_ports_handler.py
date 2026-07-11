# ==============================================================================
# CnSS Host Top Ports Subscription Handler
# Handles SQL execution for the 'host_top_ports' subscription target.
# Provides top remote ports and their protocols for a specific host IP address.
#
# Protocol Detection Strategy:
# Since the 'packet_flows' schema does not include a 'protocol' field,
# this handler relies on well-known port mappings to infer the protocol.
# Ports like 53 (DNS), 123 (NTP), 51820 (WireGuard) are classified as UDP,
# while all other ports default to TCP. This is a pragmatic approximation
# that covers the vast majority of network traffic scenarios.
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
# Maps user-facing sort_by aliases to actual SQL column names.
# Strict whitelisting prevents SQL injection via ORDER BY clause.
HOST_TOP_PORTS_SORT_WHITELIST: Dict[str, str] = {
    "port": "remote_port",
    "protocol": "protocol",  # Protocol is now a native column in packet_flows
    "pps": "packets_per_sec",
}

# --- Well-Known UDP Ports ---
# Set of common UDP ports used for protocol inference.
# This is a pragmatic approximation since packet_flows lacks a protocol field.
WELL_KNOWN_UDP_PORTS = {
    53,  # DNS
    67,  # DHCP Server
    68,  # DHCP Client
    69,  # TFTP
    123,  # NTP
    161,  # SNMP
    162,  # SNMP Trap
    514,  # Syslog (UDP variant)
    1194,  # OpenVPN
    51820,  # WireGuard
}


# --- Host Top Ports Handler ---
class HostTopPortsHandler(BaseSubscriptionHandler):
    """
    Executes SQL queries for the 'host_top_ports' subscription target.
    Provides a paginated, sortable list of top remote ports that a specific host
    communicates with, including the actual protocol from the database and traffic rates.
    """

    @property
    def target_name(self) -> str:
        """Identifier for this handler, matching SubscribeRequest.target."""
        return "host_top_ports"

    async def execute(self, db_pool: asyncpg.Pool, request: SubscribeRequest) -> Optional[Dict[str, Any]]:
        """
        Executes the host top ports query and returns the formatted JSON result.
        Query Strategy (2-stage CTE pipeline):
        1. port_flows CTE: Filters packet_flows for packets where host_ip participates,
           extracts the remote_port (the port of the other side of the connection).
        2. port_stats CTE: Groups by remote_port, computes packets_per_sec.
        3. Final SELECT: Applies ORDER BY, LIMIT/OFFSET, and uses COUNT(*) OVER()
           to compute total_count for pagination metadata.

        :param db_pool: The asyncpg connection pool.
        :param request: The validated subscription request.
        :return: Dictionary with host_top_ports_update payload, or None if host_ip missing.
        :raises DatabaseError: On query execution failures.
        """
        # --- Common Validation ---
        self._validate_request(request)

        # --- Parameter Extraction ---
        params = request.params
        channel_id = request.channel_id

        # host_ip is required for this target
        if not params.host_ip:
            logger.warning("[host_top_ports] host_ip parameter is required but missing.")
            return None

        # Resolve period_sec: use provided value or fallback to default (300 seconds = 5 minutes)
        # Pydantic validates period_sec as float, so it's safe for SQL interpolation.
        period_sec = params.period_sec if params.period_sec and params.period_sec > 0 else DEFAULT_PERIOD_SEC
        interval_str = resolve_period_interval(period_sec)

        logger.debug(
            f"[host_top_ports] Executing query for channel '{channel_id}', "
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
        order_by_sql = build_order_by(params.sort_by, params.sort_order, HOST_TOP_PORTS_SORT_WHITELIST)
        limit_sql = build_limit_param(params.limit, pq)
        offset_sql = build_offset(params.offset, pq)

        # --- Execution ---
        try:
            from core.db import db_fetch_host_top_ports_data
            rows = await db_fetch_host_top_ports_data(
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

            # - Result Formatting -
            # Extract ports and total_count from the paginated result set.
            # total_count is identical across all rows (window function),
            # so we read it once from the first row.
            ports: list[Dict[str, Any]] = []
            total_count = 0

            for row in rows:
                total_count = int(row["total_count"])
                port_num = int(row["remote_port"])
                ports.append(
                    {
                        "port": port_num,
                        "protocol": row["protocol"],  # Read directly from the database
                        "packets_per_sec": float(row["packets_per_sec"]),
                    }
                )

            result = {
                "type": "host_top_ports_update",
                "channel_id": channel_id,
                "host_ip": params.host_ip,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "total_count": total_count,
                "ports": ports,
            }

            logger.debug(
                f"[host_top_ports] Success for host '{params.host_ip}' "
                f"in channel '{channel_id}': {len(ports)} ports returned "
                f"(total: {total_count})."
            )
            return result

        except asyncpg.PostgresError as e:
            logger.error(
                f"[host_top_ports] Database error for host '{params.host_ip}' " f"in channel '{channel_id}': {e}",
                exc_info=True,
            )
            raise DatabaseError(message=f"Host top ports query failed for host '{params.host_ip}'.") from e
        except Exception as e:
            logger.error(
                f"[host_top_ports] Unexpected error for host '{params.host_ip}' " f"in channel '{channel_id}': {e}",
                exc_info=True,
            )
            raise DatabaseError(message=f"Unexpected host top ports query failure for host '{params.host_ip}'.") from e
