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

# --- Period to Seconds Mapping ---
# Maps human-readable period strings to their duration in seconds.
# Used to convert packet COUNT(*) into per-second rates.
PERIOD_TO_SECONDS: Dict[str, int] = {
    "5m": 300,
    "15m": 900,
    "1h": 3600,
    "24h": 86400,
    "7d": 604800,
    "30d": 2592000,
}
DEFAULT_PERIOD = "5m"

# --- Sort By Whitelist ---
# Maps user-facing sort_by aliases to actual SQL column names.
# Strict whitelisting prevents SQL injection via ORDER BY clause.
HOST_TOP_PORTS_SORT_WHITELIST: Dict[str, str] = {
    "port": "remote_port",
    "protocol": "remote_port",  # Protocol is derived from port, so sorting by port is equivalent
    "pps": "packets_per_sec",
}

# --- Well-Known UDP Ports ---
# Set of common UDP ports used for protocol inference.
# This is a pragmatic approximation since packet_flows lacks a protocol field.
WELL_KNOWN_UDP_PORTS = {
    53,    # DNS
    67,    # DHCP Server
    68,    # DHCP Client
    69,    # TFTP
    123,   # NTP
    161,   # SNMP
    162,   # SNMP Trap
    514,   # Syslog (UDP variant)
    1194,  # OpenVPN
    51820, # WireGuard
}


# --- Host Top Ports Handler ---
class HostTopPortsHandler(BaseSubscriptionHandler):
    """
    Executes SQL queries for the 'host_top_ports' subscription target.
    Provides a paginated, sortable list of top remote ports that a specific host
    communicates with, including inferred protocol and traffic rates.
    """

    @property
    def target_name(self) -> str:
        """Identifier for this handler, matching SubscribeRequest.target."""
        return "host_top_ports"

    async def execute(
        self, db_pool: asyncpg.Pool, request: SubscribeRequest
    ) -> Optional[Dict[str, Any]]:
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

        # Resolve period: validate against whitelist, fallback to default
        period = params.period if params.period in PERIOD_TO_SECONDS else DEFAULT_PERIOD
        interval_str = resolve_period_interval(period)
        period_seconds = PERIOD_TO_SECONDS[period]

        logger.debug(
            f"[host_top_ports] Executing query for channel '{channel_id}', "
            f"host '{params.host_ip}' (period: {period}, seconds: {period_seconds})."
        )

        # --- Dynamic Parameter Tracking ---
        # ParameterizedQuery tracks $N placeholders as we add parameters dynamically.
        pq = ParameterizedQuery(start_index=1)

        # Fixed parameters: channel_id ($1), interval ($2), host_ip ($3), period_seconds ($4)
        channel_ph = pq.add_param(channel_id)
        interval_ph = pq.add_param(interval_str)
        host_ip_ph = pq.add_param(params.host_ip)
        seconds_ph = pq.add_param(period_seconds)

        # --- ORDER BY, LIMIT, OFFSET ---
        # All use strict whitelisting / parameterized placeholders for safety.
        order_by_sql = build_order_by(
            params.sort_by, params.sort_order, HOST_TOP_PORTS_SORT_WHITELIST
        )
        limit_sql = build_limit_param(params.limit, pq)
        offset_sql = build_offset(params.offset, pq)

        # --- Query Assembly ---
        # 2-stage CTE pipeline ensures clean separation of concerns:
        # - port_flows: filters packets where host_ip participates, extracts remote_port
        # - port_stats: aggregates by remote_port with rate calculation
        # - final SELECT: sorting, pagination, total_count
        query = f"""
        WITH port_flows AS (
            -- Find all packets where host_ip participates
            -- Extract the remote_port (the port of the other side)
            SELECT 
                CASE 
                    WHEN direction = 0 AND dst_ip = {host_ip_ph}::inet THEN src_port
                    WHEN direction = 1 AND src_ip = {host_ip_ph}::inet THEN dst_port
                END AS remote_port,
                time
            FROM packet_flows
            WHERE channel_id = {channel_ph}
                AND time > NOW() - {interval_ph}::interval
                AND (
                    (direction = 0 AND dst_ip = {host_ip_ph}::inet)
                    OR (direction = 1 AND src_ip = {host_ip_ph}::inet)
                )
        ),
        port_stats AS (
            SELECT
                remote_port,
                COUNT(*)::float / {seconds_ph} AS packets_per_sec
            FROM port_flows
            WHERE remote_port IS NOT NULL
            GROUP BY remote_port
        )
        SELECT
            remote_port,
            packets_per_sec,
            COUNT(*) OVER() AS total_count
        FROM port_stats
        {order_by_sql}
        {limit_sql} {offset_sql}
        """

        # --- Execution ---
        try:
            async with db_pool.acquire() as conn:
                rows = await conn.fetch(query, *pq.get_params())

                # --- Result Formatting ---
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
                            "protocol": self._get_protocol_by_port(port_num),
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
                f"[host_top_ports] Database error for host '{params.host_ip}' "
                f"in channel '{channel_id}': {e}",
                exc_info=True,
            )
            raise DatabaseError(
                message=f"Host top ports query failed for host '{params.host_ip}'."
            ) from e
        except Exception as e:
            logger.error(
                f"[host_top_ports] Unexpected error for host '{params.host_ip}' "
                f"in channel '{channel_id}': {e}",
                exc_info=True,
            )
            raise DatabaseError(
                message=f"Unexpected host top ports query failure for host '{params.host_ip}'."
            ) from e

    def _get_protocol_by_port(self, port: int) -> str:
        """
        Determines the likely protocol based on well-known port numbers.
        Defaults to TCP for unrecognized ports.

        This is a pragmatic approximation since the packet_flows schema
        does not include an explicit 'protocol' field.

        :param port: The port number to classify.
        :return: "UDP" for well-known UDP ports, "TCP" otherwise.
        """
        if port in WELL_KNOWN_UDP_PORTS:
            return "UDP"
        return "TCP"