# ==============================================================================
# CnSS Channel State Syncer Module
# Unified background task responsible for all channel state synchronization
# between Redis (ephemeral state) and TimescaleDB (persistent registry).
#
# Responsibilities:
# 1. Scan Redis for active channel state keys (channel:state:{channel_id}).
# 2. For each active channel: atomically flush dropped_delta via Lua script,
#    read last_activity_at, and update the 'channels' table with
#    is_active = TRUE and the exact timestamp from Redis.
# 3. Mass-deactivate channels in TimescaleDB whose last_activity_at exceeds
#    the configured timeout threshold (activity_timeout_ms), setting
#    is_active = FALSE without modifying last_activity_at.
#
#
# Architecture Reference: §2.2.5 (State Synchronization & Timeout Enforcement),
#                         §2.2.7 (Atomic Drop Flushing),
#                         §2.2.9 (Channel Reactivation Lifecycle)
# ==============================================================================

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, Set

import asyncpg

from core.config import settings
from core.database import get_db_pool
from core.db import db_upsert_channel, db_deactivate_timed_out_channels
from core.exceptions import DatabaseError, RedisError
from core.redis.client import get_lua_script, get_redis_client

# --- Module Logger ---
logger = logging.getLogger(__name__)

# --- Constants ---
# Redis key prefix for the ephemeral channel state hash.
# Must match the prefix used in services/ingestion/state_manager.py.
STATE_KEY_PREFIX = "channel:state:"


# --- Channel State Syncer Class ---
class ChannelStateSyncer:
    """
    Unified background task that synchronizes channel state from Redis
    to TimescaleDB and enforces timeout-based deactivation.

    Workflow per tick:
    1. SCAN Redis for all active channel:state:{channel_id} keys.
    2. For each active channel:
       a. Atomically read and reset dropped_delta via Lua script.
       b. Read last_activity_at from Redis hash.
       c. UPDATE channels: set is_active = TRUE, update last_activity_at
          with the exact timestamp from Redis, accumulate dropped packets.
    3. Mass UPDATE: deactivate all channels where is_active = TRUE and
       last_activity_at is older than activity_timeout_ms.
    """

    def __init__(self) -> None:
        """Initializes the syncer with Redis and DB clients."""
        self._redis = get_redis_client()
        self._db_pool = get_db_pool()
        self._task: Optional[asyncio.Task[None]] = None

    async def start(self) -> None:
        """Starts the background asyncio task for periodic state synchronization."""
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._sync_loop())
            logger.info(
                f"Channel State Syncer started. Sync interval:"
                " {settings.reporting_channel_state_syncer_interval_sec}s, "
                f"Timeout threshold: {settings.activity_timeout_ms}ms."
            )

    async def stop(self) -> None:
        """Gracefully cancels the state synchronization background task."""
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            logger.info("Channel State Syncer stopped.")

    async def _sync_loop(self) -> None:
        """
        Main infinite loop that sleeps for the configured interval and then
        triggers a full state synchronization cycle.
        """
        while True:
            try:
                await self._sync_cycle()
                await asyncio.sleep(settings.reporting_channel_state_syncer_interval_sec)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                # Catch-all to prevent the background task from dying silently.
                # State sync is critical but transient failures are recoverable
                # on the next tick.
                logger.error(f"Unexpected error in Channel State Syncer loop: {e}", exc_info=True)
                await asyncio.sleep(settings.reporting_channel_state_syncer_interval_sec)

    async def _sync_cycle(self) -> None:
        """
        Executes a full state synchronization cycle:
        1. Scan Redis for active channels.
        2. Sync each active channel to TimescaleDB.
        3. Mass-deactivate timed-out channels.
        """
        logger.debug("Starting state synchronization cycle...")

        # --- Phase 1: Scan Redis for Active Channels ---
        try:
            active_channel_ids = await self._scan_active_channels()
        except Exception as e:
            logger.error(f"Failed to scan active channels in Redis: {e}")
            return

        logger.debug(f"Found {len(active_channel_ids)} active channel(s) in Redis.")

        # --- Phase 2: Sync Active Channels to TimescaleDB ---
        # Process each active channel sequentially to avoid overwhelming the database.
        synced_count = 0
        for channel_id in active_channel_ids:
            try:
                await self._sync_active_channel(channel_id)
                synced_count += 1
            except Exception as e:
                logger.error(f"Failed to sync channel '{channel_id}': {e}", exc_info=True)

        if synced_count > 0:
            logger.debug(f"Successfully synced {synced_count} active channel(s) to TimescaleDB.")

        # --- Phase 3: Mass-Deactivate Timed-Out Channels ---
        try:
            deactivated_count = await self._deactivate_timed_out_channels()
            if deactivated_count > 0:
                logger.info(
                    f"Deactivated {deactivated_count} timed-out channel(s) "
                    f"(threshold: {settings.activity_timeout_ms}ms)."
                )
        except Exception as e:
            logger.error(f"Failed to deactivate timed-out channels: {e}", exc_info=True)

        logger.debug("State synchronization cycle completed.")

    async def _scan_active_channels(self) -> Set[str]:
        """
        Scans Redis for all keys matching 'channel:state:*' and extracts channel IDs.

        Uses SCAN (non-blocking) instead of KEYS to avoid freezing Redis
        on large datasets. Returns a set of active channel IDs.
        """
        channel_ids: Set[str] = set()
        cursor = 0

        while True:
            cursor, keys = await self._redis.scan(
                cursor=cursor,
                match=f"{STATE_KEY_PREFIX}*",
                count=100,  # Hint for number of keys to return per iteration
            )

            for key in keys:
                # Handle both str and bytes returns from Redis depending on decode_responses
                if isinstance(key, bytes):
                    key = key.decode("utf-8")
                channel_id = key[len(STATE_KEY_PREFIX) :]
                channel_ids.add(channel_id)

            if cursor == 0:
                break

        return channel_ids

    async def _sync_active_channel(self, channel_id: str) -> None:
        """
        Synchronizes a single active channel from Redis to TimescaleDB.

        Steps:
        1. Atomically read and reset dropped_delta via Lua script.
        2. Read last_activity_at from Redis hash.
        3. UPDATE channels: is_active = TRUE, last_activity_at = <timestamp>,
           dropped += delta.

        :param channel_id: The identifier of the channel to sync.
        """
        state_key = f"{STATE_KEY_PREFIX}{channel_id}"
        logger.debug(f"[{channel_id}] Syncing active channel state...")

        try:
            # --- Step 1: Atomic Drop Read & Reset ---
            # Execute Lua script to atomically read and reset dropped_delta.
            # This prevents race conditions where Ingestion Worker increments
            # dropped_delta while we're reading it.
            drop_script = get_lua_script("atomic_drop_flush")
            dropped_delta = await drop_script(keys=[state_key])

            # Ensure dropped_delta is an integer (Redis Lua returns numbers)
            dropped_delta = int(dropped_delta) if dropped_delta else 0
            logger.debug(f"[{channel_id}] Atomic drop read: delta={dropped_delta}")

            # --- Step 2: Read Activity State ---
            # HGETALL retrieves all fields from the state hash.
            # Note: decode_responses=True in Redis client means values are strings.
            state_data = await self._redis.hgetall(state_key)

            if not state_data:
                # State key expired between SCAN and HGETALL. Skip this channel.
                logger.debug(f"[{channel_id}] State key expired before sync. Skipping.")
                return

            last_activity_at_raw = state_data.get("last_activity_at")

            # --- Step 3: Timestamp Conversion ---
            # Convert the Unix timestamp (stored as string by Ingestion Worker)
            # to a timezone-aware datetime object for accurate DB insertion.
            # This ensures last_activity_at reflects the exact moment packets
            # were received, not the time the syncer executes the query.
            last_activity_at: Optional[datetime] = None
            if last_activity_at_raw:
                try:
                    last_activity_at = datetime.fromtimestamp(float(last_activity_at_raw), tz=timezone.utc)
                except (ValueError, TypeError):
                    safe_val = (
                        last_activity_at_raw.decode("utf-8")
                        if isinstance(last_activity_at_raw, bytes)
                        else last_activity_at_raw
                    )
                    logger.warning(f"[{channel_id}] Invalid last_activity_at format in Redis: " f"{safe_val}")

            logger.debug(f"[{channel_id}] Redis state: last_activity_at={last_activity_at}")

            # --- Step 4: Database Update (UPSERT) ---
            # Auto-registers the channel if it doesn't exist yet (first time seen in Redis).
            # If it already exists, accumulates drops and updates activity state.
            await db_upsert_channel(channel_id, True, dropped_delta, last_activity_at, pool=self._db_pool)

            logger.info(
                f"[{channel_id}] Synced: dropped_delta={dropped_delta}, " f"last_activity_at={last_activity_at}."
            )

        except RedisError as e:
            logger.error(f"[{channel_id}] Redis error during sync: {e}")
            raise
        except DatabaseError as e:
            logger.error(f"[{channel_id}] Database error during sync: {e}")
            raise
        except Exception as e:
            logger.error(f"[{channel_id}] Unexpected error during sync: {e}", exc_info=True)
            raise

    async def _deactivate_timed_out_channels(self) -> int:
        """
        Mass-deactivates channels in TimescaleDB whose last_activity_at
        exceeds the configured timeout threshold.

        Sets is_active = FALSE without modifying last_activity_at,
        preserving the historical record of the last known activity.

        :return: The number of channels deactivated.
        """
        logger.debug("Executing mass timeout deactivation query...")
        try:
            return await db_deactivate_timed_out_channels(settings.activity_timeout_ms, pool=self._db_pool)

        except asyncpg.PostgresError as e:
            logger.error(f"Database error during timeout deactivation: {e}", exc_info=True)
            raise DatabaseError("Mass timeout deactivation query failed.") from e
        except Exception as e:
            logger.error(f"Unexpected error during timeout deactivation: {e}", exc_info=True)
            raise DatabaseError("Unexpected failure in timeout deactivation.") from e
