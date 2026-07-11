# ==============================================================================
# CnSS WebSocket Initial Snapshot Fetcher
# Executes read-only queries against TimescaleDB to provide the initial state
# for a newly subscribed client. This prevents the "cold start" gap where
# the client would otherwise wait for the next Pub/Sub update from the Reporting Worker.
# ==============================================================================

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from core.contracts.subscriptions import SubscriptionParams
from core.database import get_db_pool
from core.db import (
    db_fetch_host_details_data,
    db_fetch_host_top_destinations_data,
    db_fetch_host_top_ports_data,
    db_fetch_hosts_table_data,
    db_fetch_telemetry_data,
)
from core.exceptions import ResourceNotFoundError
from core.query_builder import (
    ParameterizedQuery,
    build_ip_exact_filter,
    build_limit_param,
    build_offset,
    build_order_by,
    resolve_period_interval,
)

# --- Module Logger ---
logger = logging.getLogger(__name__)

# --- Whitelists for Sort Ordering ---
HOSTS_TABLE_SORT_WHITELIST = {
    "location": "location",
    "ip": "host_ip",
    "unique_destinations": "unique_destinations",
    "tx": "tx_per_sec",
    "rx": "rx_per_sec",
    "last_activity": "last_activity",
}

HOST_TOP_DESTINATIONS_SORT_WHITELIST = {
    "ip": "remote_ip",
    "location": "location",
    "received": "received_per_sec",
    "last_seen": "last_seen",
}

HOST_TOP_PORTS_SORT_WHITELIST = {
    "port": "remote_port",
    "protocol": "protocol",
    "pps": "packets_per_sec",
}


# --- Snapshot Fetcher Class ---
class SnapshotFetcher:
    """
    Executes target-specific SQL queries to generate the initial state snapshot.
    Utilizes core db modules directly to ensure separation of concerns between WS and Reporting.
    """

    async def fetch_snapshot(
        self, channel_id: str, target: str, params: SubscriptionParams, request_id: str = "snapshot-placeholder"
    ) -> Dict[str, Any]:
        """
        Routes the snapshot request to target-specific query helpers.

        :param channel_id: The channel identifier to query.
        :param target: The data stream type (e.g., 'telemetry', 'hosts_table').
        :param params: The subscription parameters (filters, limits, windows).
        :param request_id: Client subscription identifier.
        :return: A dictionary containing the initial snapshot data.
        :raises ResourceNotFoundError: If the target type is not supported.
        """
        db_pool = get_db_pool()

        if target == "telemetry":
            window_sec = params.window_sec if params.window_sec and params.window_sec > 0 else 5.0
            row = await db_fetch_telemetry_data(channel_id, window_sec, pool=db_pool)

            if row is None:
                is_active = False
                total_in = 0
                total_out = 0
                pps_in = 0
                pps_out = 0
                actual_window_sec = 0.0
                dropped = 0
                latest_bucket = None
            else:
                is_active = row["is_active"]
                total_in = int(row["total_in"])
                total_out = int(row["total_out"])
                dropped = int(row["dropped"])
                bucket_count = int(row["bucket_count"])
                latest_bucket = row["latest_bucket"]
                if bucket_count == 0:
                    pps_in = 0
                    pps_out = 0
                    actual_window_sec = 0.0
                else:
                    actual_window_sec = float(bucket_count)
                    pps_in = int(total_in / actual_window_sec)
                    pps_out = int(total_out / actual_window_sec)

            now = datetime.now(timezone.utc)
            return {
                "type": "telemetry_update",
                "id": request_id,
                "channel_id": channel_id,
                "is_active": is_active,
                "window_ms": int(actual_window_sec * 1000),
                "dropped_batches": dropped,
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

        elif target == "hosts_table":
            period_sec = params.period_sec if params.period_sec and params.period_sec > 0 else 300.0
            interval_str = resolve_period_interval(period_sec)
            pq = ParameterizedQuery(start_index=1)
            channel_ph = pq.add_param(channel_id)
            interval_ph = pq.add_param(interval_str)

            filters = []
            if params.location:
                loc_val = "LAN" if params.location.upper() == "LAN" else "WAN"
                filters.append(f"location = {pq.add_param(loc_val)}")
            if params.ip:
                filters.append(build_ip_exact_filter(params.ip, "host_ip", pq))

            where_sql = f"WHERE {' AND '.join(filters)}" if filters else ""
            order_by_sql = build_order_by(params.sort_by, params.sort_order, HOSTS_TABLE_SORT_WHITELIST)
            limit_sql = build_limit_param(params.limit, pq)
            offset_sql = build_offset(params.offset, pq)

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

            hosts = []
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
                        "last_activity": row["last_activity"].isoformat() if row["last_activity"] else None,
                    }
                )

            return {
                "type": "hosts_table_update",
                "id": request_id,
                "channel_id": channel_id,
                "target": "hosts_table",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "total_count": total_count,
                "hosts": hosts,
            }

        elif target == "host_details":
            if not params.host_ip:
                raise ResourceNotFoundError(message="Missing 'host_ip' parameter for host_details.")
            period_sec = params.period_sec if params.period_sec and params.period_sec > 0 else 300.0
            interval_str = resolve_period_interval(period_sec)
            pq = ParameterizedQuery(start_index=1)
            channel_ph = pq.add_param(channel_id)
            interval_ph = pq.add_param(interval_str)
            host_ip_ph = pq.add_param(params.host_ip)

            row = await db_fetch_host_details_data(
                host_ip_ph,
                channel_ph,
                interval_ph,
                period_sec,
                pq.get_params(),
                pool=db_pool,
            )

            if row is None or (row["tx_per_sec"] == 0 and row["rx_per_sec"] == 0):
                tx_per_sec = 0.0
                rx_per_sec = 0.0
            else:
                tx_per_sec = float(row["tx_per_sec"]) if row["tx_per_sec"] else 0.0
                rx_per_sec = float(row["rx_per_sec"]) if row["rx_per_sec"] else 0.0

            return {
                "type": "host_details_update",
                "id": request_id,
                "channel_id": channel_id,
                "host_ip": params.host_ip,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "tx_per_sec": tx_per_sec,
                "rx_per_sec": rx_per_sec,
            }

        elif target == "host_top_destinations":
            if not params.host_ip:
                raise ResourceNotFoundError(message="Missing 'host_ip' parameter for host_top_destinations.")
            period_sec = params.period_sec if params.period_sec and params.period_sec > 0 else 300.0
            interval_str = resolve_period_interval(period_sec)
            pq = ParameterizedQuery(start_index=1)
            channel_ph = pq.add_param(channel_id)
            interval_ph = pq.add_param(interval_str)
            host_ip_ph = pq.add_param(params.host_ip)

            order_by_sql = build_order_by(params.sort_by, params.sort_order, HOST_TOP_DESTINATIONS_SORT_WHITELIST)
            limit_sql = build_limit_param(params.limit, pq)
            offset_sql = build_offset(params.offset, pq)

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

            destinations = []
            total_count = 0
            for row in rows:
                total_count = int(row["total_count"])
                destinations.append(
                    {
                        "ip": str(row["remote_ip"]),
                        "location": row["location"],
                        "received_per_sec": float(row["received_per_sec"]),
                        "last_seen": row["last_seen"].isoformat() if row["last_seen"] else None,
                    }
                )

            return {
                "type": "host_top_destinations_update",
                "id": request_id,
                "channel_id": channel_id,
                "host_ip": params.host_ip,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "total_count": total_count,
                "destinations": destinations,
            }

        elif target == "host_top_ports":
            if not params.host_ip:
                raise ResourceNotFoundError(message="Missing 'host_ip' parameter for host_top_ports.")
            period_sec = params.period_sec if params.period_sec and params.period_sec > 0 else 300.0
            interval_str = resolve_period_interval(period_sec)
            pq = ParameterizedQuery(start_index=1)
            channel_ph = pq.add_param(channel_id)
            interval_ph = pq.add_param(interval_str)
            host_ip_ph = pq.add_param(params.host_ip)

            order_by_sql = build_order_by(params.sort_by, params.sort_order, HOST_TOP_PORTS_SORT_WHITELIST)
            limit_sql = build_limit_param(params.limit, pq)
            offset_sql = build_offset(params.offset, pq)

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

            ports = []
            total_count = 0
            for row in rows:
                total_count = int(row["total_count"])
                ports.append(
                    {
                        "port": int(row["remote_port"]),
                        "protocol": row["protocol"],
                        "packets_per_sec": float(row["packets_per_sec"]),
                    }
                )

            return {
                "type": "host_top_ports_update",
                "id": request_id,
                "channel_id": channel_id,
                "host_ip": params.host_ip,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "total_count": total_count,
                "ports": ports,
            }

        else:
            logger.warning(f"Unsupported snapshot target: '{target}'")
            raise ResourceNotFoundError(message=f"Target '{target}' is not supported for snapshots.")
