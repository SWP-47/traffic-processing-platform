# ==============================================================================
# CnSS WebSocket Initial Snapshot Fetcher
# Executes read-only queries against TimescaleDB to provide the initial state
# for a newly subscribed client. This prevents the "cold start" gap where
# the client would otherwise wait for the next Pub/Sub update from the Reporting Worker.
# ==============================================================================

import logging
from typing import Any, Dict

from core.contracts.subscriptions import SubscriptionParams
from core.database import get_db_pool
from core.exceptions import DatabaseError, ResourceNotFoundError

# --- Module Logger ---
logger = logging.getLogger(__name__)


# --- Snapshot Fetcher Class ---
class SnapshotFetcher:
    """
    Executes target-specific SQL queries to generate the initial state snapshot.
    Each subscription target (e.g., 'telemetry', 'lan_hosts') has a dedicated handler.
    """

    async def fetch_snapshot(
        self, channel_id: str, target: str, params: SubscriptionParams
    ) -> Dict[str, Any]:
        """
        Routes the snapshot request to the appropriate target-specific handler.
        
        :param channel_id: The channel identifier to query.
        :param target: The data stream type (e.g., 'telemetry', 'lan_hosts').
        :param params: The subscription parameters (filters, limits, windows).
        :return: A dictionary containing the initial snapshot data.
        :raises ResourceNotFoundError: If the target type is not supported.
        """
        if target == "telemetry":
            return await self._fetch_telemetry_snapshot(channel_id, params)
        elif target == "lan_hosts":
            return await self._fetch_lan_hosts_snapshot(channel_id, params)
        else:
            logger.warning(f"Unsupported snapshot target: '{target}'")
            raise ResourceNotFoundError(message=f"Target '{target}' is not supported for snapshots.")

    async def _fetch_telemetry_snapshot(
        self, channel_id: str, params: SubscriptionParams
    ) -> Dict[str, Any]:
        """
        Fetches the initial telemetry state for a channel.
        Combines persistent channel metadata with recent aggregated packet rates
        from the TimescaleDB continuous aggregate (telemetry_1s).
        
        :param channel_id: The channel identifier.
        :param params: Subscription parameters (e.g., window_sec).
        :return: Dictionary with channel status and recent packet rates.
        """
        # Default aggregation window is 5 seconds if not specified
        window_sec = params.window_sec or 5.0
        
        db_pool = get_db_pool()
        try:
            async with db_pool.acquire() as conn:
                # Query combines the persistent 'channels' registry with the
                # real-time 'telemetry_1s' continuous aggregate for packet rates.
                # Uses asyncpg parameterized interval calculation ($1 * INTERVAL '1 second').
                row = await conn.fetchrow(
                    """
                    SELECT 
                        c.channel_id,
                        c.is_active,
                        c.dropped,
                        c.last_activity_at,
                        COALESCE(SUM(t.packets_in), 0) AS packets_in,
                        COALESCE(SUM(t.packets_out), 0) AS packets_out
                    FROM channels c
                    LEFT JOIN telemetry_1s t 
                        ON c.channel_id = t.channel_id 
                        AND t.bucket > NOW() - ($1 * INTERVAL '1 second')
                    WHERE c.channel_id = $2
                    GROUP BY c.channel_id, c.is_active, c.dropped, c.last_activity_at
                    """,
                    window_sec,
                    channel_id,
                )
                
                if row is None:
                    raise ResourceNotFoundError(message=f"Channel '{channel_id}' not found for telemetry snapshot.")
                
                # Format the response to match the expected WebSocket payload structure
                return {
                    "type": "telemetry_update",
                    "channel_id": row["channel_id"],
                    "is_active": row["is_active"],
                    "dropped": row["dropped"],
                    "last_activity_at": row["last_activity_at"].isoformat() if row["last_activity_at"] else None,
                    "packets_in": int(row["packets_in"]),
                    "packets_out": int(row["packets_out"]),
                    "window_sec": window_sec,
                }
        except ResourceNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to fetch telemetry snapshot for channel '{channel_id}': {e}")
            raise DatabaseError(f"Telemetry snapshot query failed for channel '{channel_id}'") from e

    async def _fetch_lan_hosts_snapshot(
        self, channel_id: str, params: SubscriptionParams
    ) -> Dict[str, Any]:
        """
        Fetches the initial LAN hosts table for a channel.
        Aggregates packet flows by host IP over the specified time window.
        
        :param channel_id: The channel identifier.
        :param params: Subscription parameters (e.g., window_sec, limit, sort_by).
        :return: Dictionary with a list of host records.
        """
        window_sec = params.window_sec or 5.0
        limit = params.limit or 50
        
        db_pool = get_db_pool()
        try:
            async with db_pool.acquire() as conn:
                # Aggregate packet flows by host IP.
                # Uses CASE to determine the 'local' host based on traffic direction.
                rows = await conn.fetch(
                    """
                    SELECT 
                        CASE WHEN direction = 0 THEN dst_ip ELSE src_ip END AS host_ip,
                        COUNT(*) AS total_packets,
                        SUM(CASE WHEN direction = 0 THEN 1 ELSE 0 END) AS rx_packets,
                        SUM(CASE WHEN direction = 1 THEN 1 ELSE 0 END) AS tx_packets
                    FROM packet_flows
                    WHERE channel_id = $1 
                      AND time > NOW() - ($2 * INTERVAL '1 second')
                    GROUP BY host_ip
                    ORDER BY total_packets DESC
                    LIMIT $3
                    """,
                    channel_id,
                    window_sec,
                    limit,
                )
                
                # Format the response
                hosts = [
                    {
                        "ip": str(row["host_ip"]),
                        "total_packets": int(row["total_packets"]),
                        "rx_packets": int(row["rx_packets"]),
                        "tx_packets": int(row["tx_packets"]),
                    }
                    for row in rows
                ]
                
                return {
                    "type": "lan_hosts_update",
                    "channel_id": channel_id,
                    "hosts": hosts,
                    "window_sec": window_sec,
                }
        except Exception as e:
            logger.error(f"Failed to fetch LAN hosts snapshot for channel '{channel_id}': {e}")
            raise DatabaseError(f"LAN hosts snapshot query failed for channel '{channel_id}'") from e