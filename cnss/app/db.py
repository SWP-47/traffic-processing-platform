import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import List

import asyncpg

from .config import settings
from .models import PacketMetadata

logger = logging.getLogger(__name__)

pool: asyncpg.Pool | None = None
_pool_lock = asyncio.Lock()


async def init_db_pool() -> None:
    """
    Create the asyncpg connection pool.
    Failures are logged but do NOT crash the process.
    """
    global pool
    try:
        logger.info(f"Initializing database connection pool → {settings.database_url}")
        pool = await asyncpg.create_pool(
            dsn=settings.database_url,
            min_size=settings.database_pool_min_size,
            max_size=settings.database_pool_max_size,
        )
        logger.info("Database connection pool ready.")
    except Exception as exc:
        logger.error(
            f"Failed to initialize database pool: {exc}. "
            "DB inserts will fail until the pool is available."
        )
        pool = None


async def close_db_pool() -> None:
    global pool
    if pool:
        await pool.close()
        logger.info("Database connection pool closed.")
        pool = None


async def insert_packet_flows(
    channel_id: str,
    timestamp: int,
    packets: List[PacketMetadata],
) -> None:
    """
    Batch INSERT raw packet metadata into the packet_flows hypertable.
    Uses executemany for a single network roundtrip.
    On any failure the batch is dropped and the error is logged.
    """

    # Lazy re-init if pool was unavailable at startup or was lost
    if not pool:
        async with _pool_lock:
            if not pool:
                try:
                    logger.info("Attempting to re-initialize database pool…")
                    await init_db_pool()
                except Exception as exc:
                    logger.error(f"Pool still unavailable: {exc}. Dropping batch.")
                    return

    if not pool:
        return

    if not packets:
        logger.debug(f"No packets to insert for channel {channel_id}")
        return

    batch_time = datetime.fromtimestamp(timestamp, tz=timezone.utc)

    rows = [
        (
            batch_time,
            channel_id,
            p.direction,
            p.src_ip,
            p.dst_ip,
            p.src_port,
            p.dst_port,
        )
        for p in packets
    ]

    try:
        await pool.executemany(
            """
            INSERT INTO packet_flows
                (time, channel_id, direction, src_ip, dst_ip, src_port, dst_port)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            rows,
        )
        logger.debug(
            f"Inserted {len(packets)} packets for channel {channel_id} "
            f"(seq window starting at {timestamp})"
        )
    except Exception as exc:
        # log and drop do NOT crash the UDP listener
        logger.error(
            f"Database insert failed for channel {channel_id} "
            f"(seq ~{rows[0][0]}): {exc}. Batch dropped gracefully."
        )


async def get_reporting_data() -> tuple[dict, dict]:
    """
    Fetches aggregated metrics for the last 1 second and the last seen time per channel.
    Returns: (metrics_dict, last_seen_map)
    """
    if not pool:
        return {}, {}
    try:
        window_interval = f"{settings.reporting_window_sec} seconds"

        metrics_rows = await pool.fetch(f"""
            SELECT channel_id, direction, COUNT(*) as count
            FROM packet_flows
            WHERE time > NOW() - INTERVAL '{window_interval}'
            GROUP BY channel_id, direction
        """)

        last_seen_rows = await pool.fetch("""
            SELECT channel_id, MAX(time) as last_seen
            FROM packet_flows
            GROUP BY channel_id
        """)

        metrics = {}
        for row in metrics_rows:
            ch_id = row["channel_id"]
            if ch_id not in metrics:
                metrics[ch_id] = {0: 0, 1: 0}
            metrics[ch_id][row["direction"]] = row["count"]

        last_seen_map = {row["channel_id"]: row["last_seen"] for row in last_seen_rows}

        return metrics, last_seen_map
    except Exception as e:
        logger.error(f"Failed to fetch reporting data: {e}")
        return {}, {}


async def get_all_channels_from_db() -> list[dict]:
    if not pool:
        return []
    try:
        # DISTINCT ON + ORDER BY (channel_id, time DESC)
        rows = await pool.fetch("""
            SELECT DISTINCT ON (channel_id)
                   channel_id,
                   time AS last_activity_timestamp
            FROM packet_flows
            ORDER BY channel_id, time DESC
        """)
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Failed to fetch channels from DB: {e}")
        return []


async def get_all_channel_ids_from_db() -> list[str]:
    """
    Fetches all distinct channels from the DB
    """
    if not pool:
        return []
    try:
        rows = await pool.fetch("""
            SELECT channel_id
            FROM packet_flows
            GROUP BY channel_id
        """)
        return [row["channel_id"] for row in rows]
    except Exception as e:
        logger.error(f"Failed to fetch channels from DB: {e}")
        return []


async def get_channel_status_from_db(channel_id: str) -> dict | None:
    """
    Fetches the last activity timestamp for a specific channel.
    Returns None if the channel has no records in the DB.
    """
    if not pool:
        return None
    try:
        row = await pool.fetchrow(
            """
            SELECT MAX(time) as last_activity_timestamp
            FROM packet_flows
            WHERE channel_id = $1
        """,
            channel_id,
        )
        if row and row["last_activity_timestamp"]:
            return {
                "channel_id": channel_id,
                "last_activity_timestamp": row["last_activity_timestamp"],
            }
        return None
    except Exception as e:
        logger.error(f"Failed to fetch channel status from DB: {e}")
        return None


async def get_health_metrics_from_db() -> dict:
    """
    Fetches total and active channel counts from the DB.
    Active channels are those with MAX(time) within the activity_timeout_ms window.
    """
    if not pool:
        return {"channels_total": 0, "channels_active": 0}
    try:
        rows = await pool.fetch("""
            SELECT channel_id, MAX(time) as last_activity_timestamp
            FROM packet_flows
            GROUP BY channel_id
        """)
        total = len(rows)
        active = 0
        now = datetime.now(timezone.utc)
        timeout_td = timedelta(milliseconds=settings.activity_timeout_ms)

        for row in rows:
            last_seen = row["last_activity_timestamp"]
            if last_seen:
                if last_seen.tzinfo is None:
                    last_seen = last_seen.replace(tzinfo=timezone.utc)
                if (now - last_seen) <= timeout_td:
                    active += 1

        return {"channels_total": total, "channels_active": active}
    except Exception as e:
        logger.error(f"Failed to fetch health metrics from DB: {e}")
        return {"channels_total": 0, "channels_active": 0}


async def is_db_healthy() -> bool:
    """
    Checks if the database connection pool is active and responsive.
    """
    if not pool:
        return False
    try:
        await pool.fetchval("SELECT 1")
        return True
    except Exception:
        return False


async def get_channel_history(channel_id: str, period: str) -> tuple[int, list[dict]]:
    """
    Fetches aggregated history points. Returns (interval_sec, points).
    Fills gaps with 0.0 to ensure a continuous time series for charts.
    """
    if not pool:
        return 60, []

    # Dynamically calculate optimal time_bucket interval based on period
    period_map = {
        "1h": 3,
        "24h": 60,
        "7d": 7 * 60,
        "30d": 30 * 60,
    }
    period_sql_map = {
        "1h": "1 hour",
        "24h": "24 hours",
        "7d": "7 days",
        "30d": "30 days",
    }

    interval_sec = period_map.get(period, 60)
    period_sql = period_sql_map.get(period, "24 hours")

    try:
        query = f"""
            WITH time_buckets AS (
                SELECT DISTINCT time_bucket('{interval_sec} seconds', gs) AS bucket
                FROM generate_series(
                    NOW() - INTERVAL '{period_sql}',
                    NOW(),
                    INTERVAL '{interval_sec} seconds'
                ) AS gs
            ),
            aggregated_data AS (
                SELECT
                    time_bucket('{interval_sec} seconds', time) AS bucket,
                    SUM(CASE WHEN direction = 0 THEN 1 ELSE 0 END)::float / {interval_sec} AS packets_in_per_sec,
                    SUM(CASE WHEN direction = 1 THEN 1 ELSE 0 END)::float / {interval_sec} AS packets_out_per_sec
                FROM packet_flows
                WHERE channel_id = $1 AND time > NOW() - INTERVAL '{period_sql}'
                GROUP BY bucket
            )
            SELECT
                tb.bucket,
                COALESCE(ad.packets_in_per_sec, 0.0) AS packets_in_per_sec,
                COALESCE(ad.packets_out_per_sec, 0.0) AS packets_out_per_sec
            FROM time_buckets tb
            LEFT JOIN aggregated_data ad ON tb.bucket = ad.bucket
            ORDER BY tb.bucket;
        """
        rows = await pool.fetch(query, channel_id)

        points = []
        for row in rows:
            p_in = float(row["packets_in_per_sec"])
            p_out = float(row["packets_out_per_sec"])
            points.append(
                {
                    "timestamp": row["bucket"].isoformat().replace("+00:00", "Z"),
                    "packets_in_per_sec": p_in,
                    "packets_out_per_sec": p_out,
                    "is_active": (p_in + p_out) > 0,
                }
            )
        return interval_sec, points
    except Exception as e:
        logger.error(f"Failed to fetch history for {channel_id}: {e}")
        return interval_sec, []


async def get_top_hosts(
    channel_id: str, target: str, sort_by: str, limit: int, window_sec: float
) -> list[dict]:
    """
    Fetches top LAN/WAN hosts based on direction mapping.
    """
    if not pool:
        return []

    # Prevent SQL injection for sort column
    sort_col_map = {
        "sent": "sent_per_sec",
        "received": "received_per_sec",
        "last_seen": "last_seen",
    }
    sort_col = sort_col_map.get(sort_by, "sent_per_sec")

    # LAN/WAN Direction Mapping
    if target == "lan_hosts":
        sent_dir, sent_ip_col = 1, "src_ip"  # OUT: LAN -> WAN
        recv_dir, recv_ip_col = 0, "dst_ip"  # IN: WAN -> LAN
    elif target == "wan_hosts":
        sent_dir, sent_ip_col = 0, "src_ip"  # IN: WAN -> LAN
        recv_dir, recv_ip_col = 1, "dst_ip"  # OUT: LAN -> WAN
    else:
        return []

    query = f"""
        WITH sent AS (
            SELECT {sent_ip_col} AS ip, COUNT(*)::float / $1 AS sent_per_sec, MAX(time) AS last_seen
            FROM packet_flows
            WHERE channel_id = $2 AND direction = $3 AND time > NOW() - make_interval(secs => $1::float)
            GROUP BY {sent_ip_col}
        ),
        received AS (
            SELECT {recv_ip_col} AS ip, COUNT(*)::float / $1 AS received_per_sec, MAX(time) AS last_seen
            FROM packet_flows
            WHERE channel_id = $2 AND direction = $4 AND time > NOW() - make_interval(secs => $1::float)
            GROUP BY {recv_ip_col}
        )
        SELECT
            COALESCE(s.ip, r.ip) AS ip,
            COALESCE(s.sent_per_sec, 0) AS sent_per_sec,
            COALESCE(r.received_per_sec, 0) AS received_per_sec,
            GREATEST(
                COALESCE(s.last_seen, '1970-01-01'::timestamptz),
                COALESCE(r.last_seen, '1970-01-01'::timestamptz)
            ) AS last_seen
        FROM sent s
        FULL OUTER JOIN received r ON s.ip = r.ip
        ORDER BY {sort_col} DESC
        LIMIT $5
    """

    try:
        rows = await pool.fetch(
            query, window_sec, channel_id, sent_dir, recv_dir, limit
        )
        return [
            {
                "ip": row["ip"],
                "sent_per_sec": float(row["sent_per_sec"]),
                "received_per_sec": float(row["received_per_sec"]),
                "last_seen": (
                    row["last_seen"].isoformat().replace("+00:00", "Z")
                    if row["last_seen"]
                    else None
                ),
            }
            for row in rows
        ]
    except Exception as e:
        logger.error(f"Failed to fetch top hosts for {channel_id} ({target}): {e}")
        return []
