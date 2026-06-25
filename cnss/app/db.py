import asyncio
import logging
from datetime import datetime, timezone
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
