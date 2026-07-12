# ==============================================================================
# CnSS Hosts Table Subscription Handler
# Handles SQL execution for the 'hosts_table' subscription target.
# Aggregates packet_flows by host IP over a configurable time period (in seconds),
# computes per-second rates (tx/rx), unique destination counts, and
# classifies hosts as LAN/WAN based on traffic direction and IP role.
#
# LAN/WAN Classification Logic:
# - LAN host: appears as dst_ip when direction=0 (IN) OR as src_ip when direction=1 (OUT)
# - WAN host: appears as src_ip when direction=0 (IN) OR as dst_ip when direction=1 (OUT)
#
# This approach monitors the bridge: LAN hosts communicate with WAN hosts.
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
HOSTS_TABLE_SORT_WHITELIST: Dict[str, str] = {
    "location": "location",
    "ip": "host_ip",
    "unique_destinations": "unique_destinations",
    "tx": "tx_per_sec",
    "rx": "rx_per_sec",
    "last_activity": "last_activity",
}


# --- Hosts Table Handler ---
class HostsTableHandler(BaseSubscriptionHandler):
    """
    Executes SQL queries for the 'hosts_table' subscription target.
    Produces a paginated, filterable list of all observed hosts (LAN and WAN)
    with real-time tx/rx rates, unique destination counts, and LAN/WAN classification.
    """

    @property
    def target_name(self) -> str:
        """Identifier for this handler, matching SubscribeRequest.target."""
        return "hosts_table"

    async def execute(self, db_pool: asyncpg.Pool, request: SubscribeRequest) -> Optional[Dict[str, Any]]:
        """
        Executes the hosts table aggregation query and returns the formatted JSON result.
        Query Strategy (3-stage CTE pipeline):
        1. host_flows CTE: Unfolds each packet into 2 records (host + remote),
           classifying each IP as LAN or WAN based on direction and role.
        2. aggregated CTE: Groups by host_ip, computes LAN/WAN classification,
           unique destinations, tx/rx per-second rates, and last activity timestamp.
        3. Final SELECT: Applies WHERE filters (location, ip), ORDER BY, LIMIT/OFFSET,
           and uses COUNT(*) OVER() to compute total_count for pagination metadata.

        :param db_pool: The asyncpg connection pool.
        :param request: The validated subscription request.
        :return: Dictionary with hosts_table_update payload.
        :raises DatabaseError: On query execution failures.
        """
        # --- Common Validation ---
        self._validate_request(request)

        # --- Parameter Extraction ---
        params = request.params
        channel_id = request.channel_id

        # Resolve period_sec: use provided value or fallback to default (300 seconds = 5 minutes)
        # Pydantic validates period_sec as float, so it's safe for SQL interpolation.
        period_sec = params.period_sec if params.period_sec and params.period_sec > 0 else DEFAULT_PERIOD_SEC
        interval_str = resolve_period_interval(period_sec)

        logger.debug(
            f"[hosts_table] Executing query for channel '{channel_id}' "
            f"(period_sec: {period_sec}, interval: {interval_str})."
        )

        # --- Dynamic Parameter Tracking ---
        # ParameterizedQuery tracks $N placeholders as we add parameters dynamically.
        # Start at $1 since channel_id and interval occupy $1-$2.
        pq = ParameterizedQuery(start_index=1)
        channel_ph = pq.add_param(channel_id)
        interval_ph = pq.add_param(interval_str)

        # --- Dynamic WHERE Filters ---
        # Build filter clauses conditionally based on user-provided params.
        where_clauses: list[str] = []

        # Location filter (LAN/WAN): applied after aggregation
        if params.location:
            location_ph = pq.add_param(params.location.upper())
            where_clauses.append(f"location = {location_ph}")

        # Exact IP match filter: parameterized to prevent SQL injection
        if params.ip:
            ip_ph = pq.add_param(params.ip)
            where_clauses.append(f"host_ip = {ip_ph}::inet")

        # Combine filters with AND; prepend WHERE keyword if any filters exist
        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        # --- ORDER BY, LIMIT, OFFSET ---
        # All use strict whitelisting / parameterized placeholders for safety.
        order_by_sql = build_order_by(params.sort_by, params.sort_order, HOSTS_TABLE_SORT_WHITELIST)
        limit_sql = build_limit_param(params.limit, pq)
        offset_sql = build_offset(params.offset, pq)

        # --- Execution ---
        try:
            from core.db import db_fetch_hosts_table_data

            rows = await db_fetch_hosts_table_data(
                channel_ph,
                interval_ph,
                period_sec,
                where_sql,
                order_by_sql,
                limit_sql,
                offset_sql,
                pq.get_params(),
                pool=db_pool,
            )

            # --- Result Formatting ---
            # Extract hosts and total_count from the paginated result set.
            # total_count is identical across all rows (window function),
            # so we read it once from the first row.
            hosts: list[Dict[str, Any]] = []
            total_count = 0

            for row in rows:
                total_count = int(row["total_count"])
                hosts.append(
                    {
                        "location": row["location"],
                        "ip": str(row["host_ip"]),
                        "unique_destinations": int(row["unique_destinations"]),
                        "tx_per_sec": float(row["tx_per_sec"]),
                        "rx_per_sec": float(row["rx_per_sec"]),
                        "last_activity": (row["last_activity"].isoformat() if row["last_activity"] else None),
                    }
                )

            result = {
                "type": "hosts_table_update",
                "channel_id": channel_id,
                "target": "hosts_table",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "total_count": total_count,
                "hosts": hosts,
            }

            logger.debug(
                f"[hosts_table] Success for '{channel_id}': " f"{len(hosts)} hosts returned (total: {total_count})."
            )
            return result

        except asyncpg.PostgresError as e:
            logger.error(
                f"[hosts_table] Database error for channel '{channel_id}': {e}",
                exc_info=True,
            )
            raise DatabaseError(message=f"Hosts table query failed for channel '{channel_id}'.") from e
        except Exception as e:
            logger.error(
                f"[hosts_table] Unexpected error for channel '{channel_id}': {e}",
                exc_info=True,
            )
            raise DatabaseError(message=f"Unexpected hosts table query failure for channel '{channel_id}'.") from e
