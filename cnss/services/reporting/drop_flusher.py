# ==============================================================================
# CnSS Drop Flusher Module
# Background task that atomically flushes dropped packet counters from Redis
# to TimescaleDB and handles channel reactivation. Uses Lua scripts to prevent
# race conditions between the Ingestion Worker (writing drops) and the
# Reporting Worker (reading and resetting drops).
#
# Architecture Reference: §2.2.5 (Atomic Drop Flushing), §2.2.9 (Channel Reactivation)
# ==============================================================================

import asyncio
import logging
from typing import Optional, Set

from core.config import settings
from core.database import get_db_pool
from core.exceptions import DatabaseError, RedisError
from core.redis.client import get_lua_script, get_redis_client

# --- Module Logger ---
logger = logging.getLogger(__name__)

# --- Constants ---
# Redis key prefix for the ephemeral channel state hash.
# Must match the prefix used in services/ingestion/state_manager.py.
STATE_KEY_PREFIX = "channel:state:"


# --- Drop Flusher Class ---
class DropFlusher:
    """
    Periodically flushes dropped packet counters from Redis to TimescaleDB
    and reactivates channels that have received new traffic.
    """

    def __init__(self) -> None:
        """Initializes the flusher with Redis and DB clients."""
        self._redis = get_redis_client()
        self._db_pool = get_db_pool()
        self._task: Optional[asyncio.Task[None]] = None

    async def start(self) -> None:
        """Starts the background asyncio task for periodic drop flushing."""
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._flush_loop())
            logger.info(
                f"Drop Flusher started. Flush interval: {settings.reporting_flush_interval_sec}s."
            )

    async def stop(self) -> None:
        """Gracefully cancels the drop flusher background task."""
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            logger.info("Drop Flusher stopped.")

    async def _flush_loop(self) -> None:
        """
        Main infinite loop that sleeps for the configured interval and then
        triggers a flush for all active channels.
        """
        while True:
            try:
                await self._flush_all_channels()
                await asyncio.sleep(settings.reporting_flush_interval_sec)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                # Catch-all to prevent the background task from dying silently
                logger.error(f"Unexpected error in Drop Flusher loop: {e}", exc_info=True)
                # Brief sleep to prevent tight error loops
                await asyncio.sleep(1.0)

    async def _flush_all_channels(self) -> None:
        """
        Scans Redis for all active channel state keys and flushes their
        dropped counters and activity status to TimescaleDB.
        """
        logger.debug("Starting drop flush cycle...")
        
        # --- Scan for Active Channel State Keys ---
        # Use SCAN to find all keys matching "channel:state:*".
        # This returns only channels that have received traffic in the last 6 seconds
        # (due to TTL enforcement in StateManager).
        try:
            channel_ids = await self._scan_active_channels()
        except Exception as e:
            logger.error(f"Failed to scan active channels: {e}")
            return

        if not channel_ids:
            logger.debug("No active channels to flush.")
            return

        logger.debug(f"Flushing drops and reactivating {len(channel_ids)} channel(s)...")

        # --- Process Each Channel ---
        # Iterate sequentially to avoid overwhelming the database with concurrent updates.
        # Given the 1Hz interval and fast queries, sequential processing is safe.
        for channel_id in channel_ids:
            await self._flush_channel(channel_id)
            
        logger.debug(f"Drop flush cycle completed for {len(channel_ids)} channel(s).")

    async def _scan_active_channels(self) -> Set[str]:
        """
        Scans Redis for all keys matching "channel:state:*" and extracts channel IDs.
        :return: A set of active channel IDs.
        """
        channel_ids: Set[str] = set()
        cursor = 0

        # SCAN is non-blocking and returns results incrementally.
        # This prevents blocking Redis with a large KEYS command.
        while True:
            cursor, keys = await self._redis.scan(
                cursor=cursor,
                match=f"{STATE_KEY_PREFIX}*",
                count=100,  # Hint for number of keys to return per iteration
            )

            for key in keys:
                # Extract channel_id from key (e.g., "channel:state:bridge-01" -> "bridge-01")
                # Handle both str and bytes returns from Redis depending on decode_responses
                if isinstance(key, bytes):
                    key = key.decode("utf-8")
                channel_id = key[len(STATE_KEY_PREFIX):]
                channel_ids.add(channel_id)

            if cursor == 0:
                break

        return channel_ids

    async def _flush_channel(self, channel_id: str) -> None:
        """
        Atomically reads and resets dropped_delta for a channel,
        reads activity status, and updates TimescaleDB.
        :param channel_id: The identifier of the channel to flush.
        """
        state_key = f"{STATE_KEY_PREFIX}{channel_id}"
        logger.debug(f"[{channel_id}] Processing drop flush and state sync...")

        try:
            # --- Atomic Drop Read & Reset ---
            # Execute Lua script to atomically read and reset dropped_delta.
            # This prevents race conditions where Ingestion Worker increments
            # dropped_delta while we're reading it.
            drop_script = get_lua_script("atomic_drop_flush")
            dropped_delta = await drop_script(keys=[state_key])
            
            # Ensure dropped_delta is an integer (Redis Lua returns numbers)
            dropped_delta = int(dropped_delta) if dropped_delta else 0
            logger.debug(f"[{channel_id}] Atomic drop read: delta={dropped_delta}")

            # --- Read Activity Status ---
            # HGETALL retrieves all fields from the state hash:
            # - is_active: 1 if channel received packets, 0 otherwise
            # - last_activity_at: Unix timestamp of last activity
            state_data = await self._redis.hgetall(state_key)

            if not state_data:
                # State key expired between SCAN and HGETALL. Skip.
                logger.debug(f"[{channel_id}] State key expired before flush. Skipping.")
                return

            # Parse Redis hash values (strings) to Python types
            is_active_in_redis = state_data.get("is_active") == "1" or state_data.get("is_active") == 1
            last_activity_at_raw = state_data.get("last_activity_at")
            
            logger.debug(
                f"[{channel_id}] Redis state: is_active={is_active_in_redis}, "
                f"last_activity_at={last_activity_at_raw}"
            )

            # --- Determine if Update is Needed ---
            # Update DB if:
            # 1. There are drops to flush (dropped_delta > 0)
            # 2. Channel is active in Redis (needs reactivation in DB)
            should_update = dropped_delta > 0 or is_active_in_redis

            if not should_update:
                logger.debug(f"[{channel_id}] No drops or activity to flush. Skipping DB update.")
                return

            # --- Database Update ---
            # Perform batched UPDATE on the 'channels' table.
            # - dropped = dropped + $1 (accumulate drops)
            # - is_active = TRUE (reactivate if active in Redis)
            # - last_activity_at = NOW() (update timestamp if active)
            async with self._db_pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE channels
                    SET 
                        dropped = dropped + $1,
                        is_active = CASE WHEN $2::boolean THEN TRUE ELSE is_active END,
                        last_activity_at = CASE WHEN $2::boolean THEN NOW() ELSE last_activity_at END
                    WHERE channel_id = $3
                    """,
                    dropped_delta,
                    is_active_in_redis,
                    channel_id,
                )

            logger.info(
                f"[{channel_id}] Successfully flushed {dropped_delta} drops, "
                f"reactivated={is_active_in_redis}."
            )

        except RedisError as e:
            logger.error(f"[{channel_id}] Redis error during flush: {e}")
        except DatabaseError as e:
            logger.error(f"[{channel_id}] Database error during flush: {e}")
        except Exception as e:
            logger.error(f"[{channel_id}] Unexpected error during flush: {e}", exc_info=True)