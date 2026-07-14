# ==============================================================================
# CnSS Centralized Database Query Module
# Encapsulates all SQL execution logic for the entire codebase (REST API,
# WebSocket Service, and Reporting Worker), enforcing separation of concerns,
# query reusability, and SQL injection safety.
# ==============================================================================

import logging
from datetime import datetime
from typing import Any, Optional

from core.database import get_db_pool

logger = logging.getLogger(__name__)

# --- Health check queries ---


async def db_ping(pool: Optional[Any] = None) -> bool:
    """Verifies that the database pool is healthy and responsive."""
    try:
        db_p = pool or get_db_pool()
        async with db_p.acquire() as conn:
            await conn.fetchval("SELECT 1;")
        return True
    except Exception as e:
        logger.error(f"Database ping failed: {e}", exc_info=True)
        return False


async def db_fetch_channel_counts(pool: Optional[Any] = None) -> tuple[int, int]:
    """Returns (total_channels, active_channels) count."""
    db_p = pool or get_db_pool()
    async with db_p.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE is_active = TRUE) AS active
            FROM channels;
        """)
        if row:
            return row["total"], row["active"]
        return 0, 0


# --- Authentication queries ---


async def db_fetch_user_by_username(username: str, pool: Optional[Any] = None) -> Optional[dict[str, Any]]:
    """Fetches a user profile by username."""
    db_p = pool or get_db_pool()
    async with db_p.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, username, password_hash, role FROM users WHERE username = $1",
            username,
        )
        return dict(row) if row else None


async def db_fetch_user_by_id(user_id: Any, pool: Optional[Any] = None) -> Optional[dict[str, Any]]:
    """Fetches user information (id, username, role) by user ID."""
    db_p = pool or get_db_pool()
    async with db_p.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, username, role FROM users WHERE id = $1",
            user_id,
        )
        return dict(row) if row else None


async def db_fetch_user_scopes(user_id: Any, pool: Optional[Any] = None) -> list[str]:
    """Fetches list of permitted channel scopes for a viewer user."""
    db_p = pool or get_db_pool()
    async with db_p.acquire() as conn:
        rows = await conn.fetch(
            "SELECT channel_id FROM user_channel_scopes WHERE user_id = $1",
            user_id,
        )
        return [str(row["channel_id"]) for row in rows]


async def db_fetch_all_channels(pool: Optional[Any] = None) -> list[str]:
    """Fetches all registered channel IDs."""
    db_p = pool or get_db_pool()
    async with db_p.acquire() as conn:
        rows = await conn.fetch("SELECT channel_id FROM channels")
        return [str(row["channel_id"]) for row in rows]


async def db_fetch_user_profile(user_id: Any, pool: Optional[Any] = None) -> Optional[dict[str, Any]]:
    """
    Fetches complete user profile including id, username, role, and scope.
    For admin users, scope includes all registered channels.
    For viewer users, scope includes only assigned channels from user_channel_scopes.
    """
    db_p = pool or get_db_pool()
    async with db_p.acquire() as conn:
        # Fetch user data
        user_row = await conn.fetchrow(
            "SELECT id, username, role FROM users WHERE id = $1",
            user_id,
        )
        if not user_row:
            return None
        
        # Fetch scope based on role
        scope: list[str] = []
        if user_row["role"] == "admin":
            # Admin: scope includes all registered channels
            scope = await db_fetch_all_channels(pool=db_p)
        else:
            # Viewer: scope includes only assigned channels
            scope = await db_fetch_user_scopes(user_id, pool=db_p)
        
        return {
            "id": str(user_row["id"]),
            "username": user_row["username"],
            "role": user_row["role"],
            "scope": scope,
        }


# --- Channel & Discovery queries ---


async def db_fetch_channel_status(channel_id: str, pool: Optional[Any] = None) -> Optional[dict[str, Any]]:
    """Fetches active status and last activity timestamp for a channel."""
    db_p = pool or get_db_pool()
    async with db_p.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT channel_id, is_active, last_activity_at FROM channels WHERE channel_id = $1",
            channel_id,
        )
        return dict(row) if row else None


async def db_list_channels(channel_ids: Optional[list[str]] = None, pool: Optional[Any] = None) -> list[dict[str, Any]]:
    """
    Lists registered channels. If channel_ids list is provided,
    filters the results to only include those channel IDs.
    """
    db_p = pool or get_db_pool()
    async with db_p.acquire() as conn:
        if channel_ids is None:
            rows = await conn.fetch("SELECT channel_id, is_active, last_activity_at FROM channels")
        else:
            rows = await conn.fetch(
                "SELECT channel_id, is_active, last_activity_at FROM channels WHERE channel_id = ANY($1)",
                channel_ids,
            )
        return [dict(row) for row in rows]


# --- History queries ---


async def db_channel_exists(channel_id: str, pool: Optional[Any] = None) -> bool:
    """Returns True if the channel exists in the database registry."""
    row = await db_fetch_channel_status(channel_id, pool=pool)
    return row is not None


async def db_fetch_channel_history(
    channel_id: str, start_time: datetime, end_time: datetime, interval_sec: int, pool: Optional[Any] = None
) -> list[dict[str, Any]]:
    """Lazy-loads historical telemetry data for a channel."""
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
    db_p = pool or get_db_pool()
    async with db_p.acquire() as conn:
        rows = await conn.fetch(query, start_time, end_time, interval_sec, channel_id)
        return [dict(row) for row in rows]


async def db_fetch_host_history(
    channel_id: str,
    host_ip: str,
    start_time: datetime,
    end_time: datetime,
    interval_sec: int,
    pool: Optional[Any] = None,
) -> list[dict[str, Any]]:
    """Lazy-loads historical telemetry Rx/Tx data for a specific host."""
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
    db_p = pool or get_db_pool()
    async with db_p.acquire() as conn:
        rows = await conn.fetch(query, start_time, end_time, interval_sec, host_ip, channel_id)
        return [dict(row) for row in rows]


# --- Ingestion / State syncing queries ---


async def db_upsert_channel(
    channel_id: str,
    is_active: bool,
    dropped_delta: int,
    last_activity_at: Optional[datetime],
    pool: Optional[Any] = None,
) -> None:
    """Inserts or updates a channel's activity status and accumulated packet drop count."""
    db_p = pool or get_db_pool()
    async with db_p.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO channels (channel_id, is_active, dropped, last_activity_at)
            VALUES ($3, $2, $1, $4)
            ON CONFLICT (channel_id) DO UPDATE SET
                dropped = channels.dropped + EXCLUDED.dropped,
                is_active = EXCLUDED.is_active,
                last_activity_at = CASE
                    WHEN EXCLUDED.last_activity_at IS NOT NULL
                    THEN EXCLUDED.last_activity_at
                    ELSE channels.last_activity_at
                END
            """,
            dropped_delta,
            is_active,
            channel_id,
            last_activity_at,
        )


async def db_deactivate_timed_out_channels(activity_timeout_ms: int, pool: Optional[Any] = None) -> int:
    """Updates channels to is_active=FALSE if their last activity has timed out."""
    query = """
        UPDATE channels
        SET is_active = FALSE
        WHERE is_active = TRUE
          AND last_activity_at < NOW() - ($1 * INTERVAL '1 millisecond')
    """
    db_p = pool or get_db_pool()
    async with db_p.acquire() as conn:
        status = await conn.execute(query, activity_timeout_ms)
        if status:
            return int(status.split()[-1])
        return 0


# --- Dynamic Reporting / WebSocket snapshot queries ---


async def db_execute_fetch(query: str, params: list[Any], pool: Optional[Any] = None) -> list[dict[str, Any]]:
    """General helper to execute dynamic SELECT queries with parameters."""
    db_p = pool or get_db_pool()
    async with db_p.acquire() as conn:
        rows = await conn.fetch(query, *params)
        return [dict(row) for row in rows]


async def db_execute_fetchrow(query: str, params: list[Any], pool: Optional[Any] = None) -> Optional[dict[str, Any]]:
    """General helper to execute dynamic SELECT query returning a single row."""
    db_p = pool or get_db_pool()
    async with db_p.acquire() as conn:
        row = await conn.fetchrow(query, *params)
        return dict(row) if row else None


# --- Target-Specific Reporting / Snapshot Query Functions ---


async def db_fetch_telemetry_data(
    channel_id: str, window_sec: float, pool: Optional[Any] = None
) -> Optional[dict[str, Any]]:
    """Queries aggregated telemetry packet rates for a channel over a given window."""
    query = """
        SELECT
            c.is_active,
            c.dropped,
            COALESCE(SUM(t.packets_in), 0) AS total_in,
            COALESCE(SUM(t.packets_out), 0) AS total_out,
            COUNT(DISTINCT t.bucket) AS bucket_count,
            MAX(t.bucket) AS latest_bucket
        FROM channels c
        LEFT JOIN telemetry_1s t
            ON c.channel_id = t.channel_id
            AND t.bucket > NOW() - ($1 * INTERVAL '1 second') - INTERVAL '1 second'
            AND t.bucket <= NOW() - INTERVAL '1 second'
        WHERE c.channel_id = $2
        GROUP BY c.channel_id, c.is_active, c.dropped;
    """
    return await db_execute_fetchrow(query, [window_sec, channel_id], pool=pool)


async def db_fetch_hosts_table_data(
    channel_ph: str,
    interval_ph: str,
    period_sec: float,
    where_sql: str,
    order_by_sql: str,
    limit_sql: str,
    offset_sql: str,
    params: list[Any],
    pool: Optional[Any] = None,
) -> list[dict[str, Any]]:
    """Queries and aggregates host flow traffic statistics for a channel."""
    query = f"""
    WITH host_flows AS (
        SELECT
            CASE WHEN direction = 0 THEN dst_ip ELSE src_ip END AS host_ip,
            CASE WHEN direction = 0 THEN src_ip ELSE dst_ip END AS remote_ip,
            'LAN' AS host_location,
            CASE WHEN direction = 1 THEN 1 ELSE 0 END AS is_tx,
            CASE WHEN direction = 0 THEN 1 ELSE 0 END AS is_rx,
            time
        FROM packet_flows
        WHERE channel_id = {channel_ph} AND time > NOW() - ({interval_ph}::text)::interval
        UNION ALL
        SELECT
            CASE WHEN direction = 0 THEN src_ip ELSE dst_ip END AS host_ip,
            CASE WHEN direction = 0 THEN dst_ip ELSE src_ip END AS remote_ip,
            'WAN' AS host_location,
            CASE WHEN direction = 0 THEN 1 ELSE 0 END AS is_tx,
            CASE WHEN direction = 1 THEN 1 ELSE 0 END AS is_rx,
            time
        FROM packet_flows
        WHERE channel_id = {channel_ph} AND time > NOW() - ({interval_ph}::text)::interval
    ),
    aggregated AS (
        SELECT
            host_ip,
            CASE
                WHEN SUM(CASE WHEN host_location = 'LAN' THEN 1 ELSE 0 END) >=
                    SUM(CASE WHEN host_location = 'WAN' THEN 1 ELSE 0 END)
                THEN 'LAN'
                ELSE 'WAN'
            END AS location,
            COUNT(DISTINCT remote_ip) AS unique_destinations,
            SUM(is_tx)::float / {period_sec} AS tx_per_sec,
            SUM(is_rx)::float / {period_sec} AS rx_per_sec,
            MAX(time) AS last_activity
        FROM host_flows
        GROUP BY host_ip
    )
    SELECT
        host_ip,
        location,
        unique_destinations,
        tx_per_sec,
        rx_per_sec,
        last_activity,
        COUNT(*) OVER() AS total_count
    FROM aggregated
    {where_sql}
    {order_by_sql}
    {limit_sql} {offset_sql}
    """
    return await db_execute_fetch(query, params, pool=pool)


async def db_fetch_host_top_destinations_data(
    host_ip_ph: str,
    channel_ph: str,
    interval_ph: str,
    period_sec: float,
    order_by_sql: str,
    limit_sql: str,
    offset_sql: str,
    params: list[Any],
    pool: Optional[Any] = None,
) -> list[dict[str, Any]]:
    """Queries top destination IPs for a specific host in a channel."""
    query = f"""
    WITH host_flows AS (
        SELECT
            CASE
                WHEN direction = 0 AND dst_ip = {host_ip_ph}::inet THEN src_ip
                WHEN direction = 1 AND src_ip = {host_ip_ph}::inet THEN dst_ip
            END AS remote_ip,
            CASE
                WHEN (direction = 0 AND src_ip = CASE
                    WHEN direction = 0 AND dst_ip = {host_ip_ph}::inet THEN src_ip
                    WHEN direction = 1 AND src_ip = {host_ip_ph}::inet THEN dst_ip
                END) OR (direction = 1 AND dst_ip = CASE
                    WHEN direction = 0 AND dst_ip = {host_ip_ph}::inet THEN src_ip
                    WHEN direction = 1 AND src_ip = {host_ip_ph}::inet THEN dst_ip
                END) THEN 'WAN'
                ELSE 'LAN'
            END AS location,
            time
        FROM packet_flows
        WHERE channel_id = {channel_ph}
        AND time > NOW() - ({interval_ph}::text)::interval
        AND (
            (direction = 0 AND dst_ip = {host_ip_ph}::inet)
            OR (direction = 1 AND src_ip = {host_ip_ph}::inet)
        )
    ),
    destination_stats AS (
        SELECT
            remote_ip,
            CASE
                WHEN SUM(CASE WHEN location = 'LAN' THEN 1 ELSE 0 END) >=
                    SUM(CASE WHEN location = 'WAN' THEN 1 ELSE 0 END)
                THEN 'LAN'
                ELSE 'WAN'
            END AS location,
            COUNT(*)::float / {period_sec} AS received_per_sec,
            MAX(time) AS last_seen
        FROM host_flows
        WHERE remote_ip IS NOT NULL
        GROUP BY remote_ip
    )
    SELECT
        remote_ip,
        location,
        received_per_sec,
        last_seen,
        COUNT(*) OVER() AS total_count
    FROM destination_stats
    {order_by_sql}
    {limit_sql} {offset_sql}
    """
    return await db_execute_fetch(query, params, pool=pool)


async def db_fetch_host_details_data(
    host_ip_ph: str,
    channel_ph: str,
    interval_ph: str,
    period_sec: float,
    params: list[Any],
    pool: Optional[Any] = None,
) -> Optional[dict[str, Any]]:
    """Queries detailed packet rates (Rx/Tx) for a specific host in a channel."""
    query = f"""
    SELECT
        COUNT(*) FILTER (WHERE src_ip = {host_ip_ph}::inet)::float / {period_sec} AS tx_per_sec,
        COUNT(*) FILTER (WHERE dst_ip = {host_ip_ph}::inet)::float / {period_sec} AS rx_per_sec
    FROM packet_flows
    WHERE channel_id = {channel_ph}
    AND time > NOW() - ({interval_ph}::text)::interval
    AND (src_ip = {host_ip_ph}::inet OR dst_ip = {host_ip_ph}::inet)
    """
    return await db_execute_fetchrow(query, params, pool=pool)


async def db_fetch_host_top_ports_data(
    host_ip_ph: str,
    channel_ph: str,
    interval_ph: str,
    period_sec: float,
    order_by_sql: str,
    limit_sql: str,
    offset_sql: str,
    params: list[Any],
    pool: Optional[Any] = None,
) -> list[dict[str, Any]]:
    """Queries top remote ports and protocols for a specific host in a channel."""
    query = f"""
    WITH port_flows AS (
        SELECT
            CASE
                WHEN direction = 0 AND dst_ip = {host_ip_ph}::inet THEN src_port
                WHEN direction = 1 AND src_ip = {host_ip_ph}::inet THEN dst_port
            END AS remote_port,
            protocol,
            time
        FROM packet_flows
        WHERE channel_id = {channel_ph}
          AND time > NOW() - ({interval_ph}::text)::interval
          AND ((direction = 0 AND dst_ip = {host_ip_ph}::inet)
            OR (direction = 1 AND src_ip = {host_ip_ph}::inet))
    ),
    port_stats AS (
        SELECT
            remote_port,
            protocol,
            COUNT(*)::float / {period_sec} AS packets_per_sec
        FROM port_flows
        WHERE remote_port IS NOT NULL
        GROUP BY remote_port, protocol
    )
    SELECT
        remote_port,
        protocol,
        packets_per_sec,
        COUNT(*) OVER() AS total_count
    FROM port_stats
    {order_by_sql}
    {limit_sql} {offset_sql}
    """
    return await db_execute_fetch(query, params, pool=pool)
