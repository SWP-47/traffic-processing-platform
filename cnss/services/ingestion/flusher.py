# ==============================================================================
# CnSS Background Flusher Module
# Implements a high-performance background asyncio task that periodically
# drains the Redis UDP buffers and executes batch INSERTs into TimescaleDB.
# Minimizes network roundtrips and ensures reliable telemetry persistence.
# ==============================================================================

import asyncio
import json
import logging
from datetime import datetime
from typing import List, Optional, Set, Tuple

from core.config import settings
from core.database import get_db_pool
from core.exceptions import DatabaseError, RedisError
from core.redis.client import get_lua_script, get_redis_client

# --- Module Logger ---
logger = logging.getLogger(__name__)

# --- Constants ---
# Redis key prefix for the high-speed packet buffer lists.
BUFFER_KEY_PREFIX = "udp:buffer:"


# --- Background Flusher Class ---
class BackgroundFlusher:
    """
    Manages the periodic background flushing of packet metadata from Redis
    to the TimescaleDB 'packet_flows' hypertable.
    """

    def __init__(self) -> None:
        """Initializes the flusher state and asyncio task reference."""
        self._task: Optional[asyncio.Task] = None
        # In-memory registry of channels that have active buffers.
        # Populated by the UDPIngestionServer upon receiving valid batches.
        self._active_channels: Set[str] = set()
        # Lock to safely modify the active channels set from concurrent coroutines
        self._lock = asyncio.Lock()

    async def register_channel(self, channel_id: str) -> None:
        """
        Registers a channel as active so the flusher knows to check its buffer.
        Called by the UDPIngestionServer when a new batch arrives.
        
        :param channel_id: The identifier of the channel to register.
        """
        async with self._lock:
            self._active_channels.add(channel_id)

    async def start(self) -> None:
        """Starts the background asyncio task for periodic flushing."""
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run_loop())
            logger.info(
                f"Background Flusher started. Flush interval: {settings.flush_interval_sec}s."
            )

    async def stop(self) -> None:
        """Gracefully cancels the background flusher task."""
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            logger.info("Background Flusher stopped.")

    async def _run_loop(self) -> None:
        """
        Main infinite loop that sleeps for the configured interval and then
        triggers a flush for all registered active channels.
        """
        while True:
            try:
                await asyncio.sleep(settings.flush_interval_sec)
                await self._flush_all_channels()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                # Catch-all to prevent the background task from dying silently
                logger.error(f"Unexpected error in flusher loop: {e}", exc_info=True)
                # Brief sleep to prevent tight error loops
                await asyncio.sleep(1.0)

    async def _flush_all_channels(self) -> None:
        """
        Iterates over a snapshot of active channels and flushes their buffers.
        """
        # Take a snapshot to avoid holding the lock during I/O operations
        async with self._lock:
            channels_snapshot = list(self._active_channels)

        for channel_id in channels_snapshot:
            await self._flush_channel(channel_id)

    async def _flush_channel(self, channel_id: str) -> None:
        """
        Atomically pops all records from the Redis buffer for a specific channel
        and executes a batch INSERT into TimescaleDB.
        
        :param channel_id: The identifier of the channel to flush.
        """
        buffer_key = f"{BUFFER_KEY_PREFIX}{channel_id}"
        
        try:
            # --- Atomic Redis Pop ---
            # Execute the Lua script to read and delete the list in one atomic operation
            pop_script = get_lua_script("atomic_buffer_pop")
            raw_items: List[str] = await pop_script(keys=[buffer_key])

            if not raw_items:
                return

            # --- Data Parsing ---
            # Deserialize JSON strings and convert to tuples for asyncpg executemany
            parsed_records: List[Tuple] = []
            for raw_json in raw_items:
                try:
                    record = json.loads(raw_json)
                    parsed_records.append((
                        datetime.fromisoformat(record["time"]),
                        record["channel_id"],
                        record["direction"],
                        record["src_ip"],
                        record["dst_ip"],
                        record["src_port"],
                        record["dst_port"],
                    ))
                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    logger.error(f"Failed to parse buffered packet record for '{channel_id}': {e}")
                    continue

            if not parsed_records:
                return

            # --- Batch Database Insert ---
            # Use asyncpg's executemany for highly optimized batch insertion
            db_pool = get_db_pool()
            async with db_pool.acquire() as conn:
                await conn.executemany(
                    """
                    INSERT INTO packet_flows (time, channel_id, direction, src_ip, dst_ip, src_port, dst_port)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                    parsed_records
                )
                
            logger.debug(
                f"Channel '{channel_id}': Successfully flushed {len(parsed_records)} "
                f"packets to TimescaleDB."
            )

        except RedisError as e:
            logger.error(f"Redis error while flushing buffer for '{channel_id}': {e}")
        except DatabaseError as e:
            # If DB insert fails, the data is already lost from Redis due to atomic pop.
            # In a strict system, we might need a dead-letter queue, but per architecture,
            # Redis is ephemeral and we accept this trade-off for max IOPS.
            logger.error(f"Database error while flushing buffer for '{channel_id}': {e}")
        except Exception as e:
            logger.error(f"Unexpected error flushing buffer for '{channel_id}': {e}", exc_info=True)