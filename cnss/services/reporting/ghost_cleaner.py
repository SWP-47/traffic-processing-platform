# ==============================================================================
# CnSS Ghost Subscription Cleaner
# Background task that prevents "ghost" subscriptions from consuming database
# resources. When the WebSocket Service crashes, it may leave stale client_id:sub_id
# entries in sub:listeners:{hash} sets. This cleaner validates each listener
# against the ephemeral ws:session:{client_id} key in Redis and removes
# orphaned entries, ensuring the Reporting Worker only executes SQL for
# subscriptions with genuinely active WebSocket clients.
#
# Architecture Reference: §2.2.8 (Ghost Subscription Prevention)
# ==============================================================================
import asyncio
import logging
from typing import Dict, Optional, Set, cast

from core.config import settings
from core.redis.client import get_redis_client

# --- Module Logger ---
logger = logging.getLogger(__name__)

# --- Redis Key Constants ---
# These must match the prefixes used in services/websocket/session.py and
# services/websocket/subscription.py to ensure consistent key resolution.

# Global index of all active subscription hashes (Set).
ACTIVE_HASHES_KEY = "sub:active_hashes"

# Prefix for the listener set of a specific subscription (Set of client_id:sub_id).
LISTENERS_KEY_PREFIX = "sub:listeners:"

# Prefix for the ephemeral WebSocket session hash (Hash with TTL=10s).
SESSION_KEY_PREFIX = "ws:session:"

# Prefix for the subscription registry (String containing JSON definition).
REGISTRY_KEY_PREFIX = "sub:registry:"


# --- Ghost Cleaner Class ---
class GhostCleaner:
    """
    Periodically scans active subscriptions and removes stale client_id:sub_id
    entries from listener sets. If a listener set becomes empty after cleanup,
    the corresponding registry and active hash index entries are deleted to
    stop the Reporting Worker from polling the database.
    """

    def __init__(self) -> None:
        """Initializes the cleaner with the global Redis client instance."""
        self._redis = get_redis_client()
        self._task: Optional[asyncio.Task[None]] = None

    async def start(self) -> None:
        """Starts the background asyncio task for periodic ghost cleanup."""
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._cleanup_loop())
            logger.info(f"Ghost Cleaner started. Cleanup interval: {settings.ghost_cleanup_interval_sec}s.")

    async def stop(self) -> None:
        """Gracefully cancels the ghost cleanup background task."""
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            logger.info("Ghost Cleaner stopped.")

    async def _cleanup_loop(self) -> None:
        """
        Main infinite loop that sleeps for the configured interval and then
        triggers a full scan of active subscriptions for ghost entries.
        """
        while True:
            try:
                await self._scan_and_clean()
                await asyncio.sleep(settings.ghost_cleanup_interval_sec)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                # Catch-all to prevent the background task from dying silently.
                # Ghost cleanup is non-critical; failures here only mean
                # stale entries persist until the next successful cycle.
                logger.error(f"Unexpected error in Ghost Cleaner loop: {e}", exc_info=True)
                await asyncio.sleep(settings.ghost_cleanup_interval_sec)

    async def _scan_and_clean(self) -> None:
        """
        Retrieves all active subscription hashes and validates their
        listener sets against existing WebSocket sessions.
        """
        # --- Retrieve Active Hashes ---
        try:
            active_hashes: Set[str] = cast(Set[str], await self._redis.smembers(ACTIVE_HASHES_KEY))
        except Exception as e:
            logger.error(f"Failed to retrieve active hashes from Redis: {e}")
            return

        if not active_hashes:
            logger.debug("No active subscriptions to scan for ghosts.")
            return

        logger.debug(f"Scanning {len(active_hashes)} active subscription(s) for ghosts...")

        # --- Process Each Subscription ---
        # Iterate sequentially to avoid overwhelming Redis with concurrent
        # EXISTS checks. Given the typical number of active subscriptions
        # (tens to hundreds), sequential processing is efficient enough.
        for query_hash in active_hashes:
            await self._clean_subscription(query_hash)

    async def _clean_subscription(self, query_hash: str) -> None:
        """
        Validates all listeners for a specific subscription hash.
        Removes stale client_id:sub_id entries and cleans up empty subscriptions.
        :param query_hash: The deterministic hash of the subscription.
        """
        listeners_key = f"{LISTENERS_KEY_PREFIX}{query_hash}"

        # --- Retrieve Current Listeners ---
        try:
            listeners: Set[str] = cast(Set[str], await self._redis.smembers(listeners_key))
        except Exception as e:
            logger.error(f"[{query_hash}] Failed to retrieve listeners from '{listeners_key}': {e}")
            return

        if not listeners:
            # No listeners present. This is a "ghost hash" — the listener set
            # is empty but the hash remains in sub:active_hashes.
            # Clean up the orphaned registry and active index entry.
            await self._cleanup_empty_subscription(query_hash)
            return

        # --- Group Listeners by client_id for Batch Session Check ---
        # Parse composite keys (client_id:sub_id) and group by client_id
        # to minimize EXISTS checks (one per unique client_id, not per listener).
        client_to_members: Dict[str, Set[str]] = {}
        for listener in listeners:
            # Split composite key: "client_id:sub_id"
            # SHA-256 hash does not contain ':', so rsplit is safe.
            parts = listener.rsplit(":", 1)
            if len(parts) != 2:
                logger.warning(f"[{query_hash}] Malformed listener entry: '{listener}'. Removing.")
                continue
            client_id, _ = parts
            client_to_members.setdefault(client_id, set()).add(listener)

        # --- Validate Each Unique client_id ---
        stale_members: Set[str] = set()
        for client_id, members in client_to_members.items():
            session_key = f"{SESSION_KEY_PREFIX}{client_id}"
            try:
                # EXISTS returns 1 if the key exists, 0 otherwise.
                # This is an O(1) operation in Redis.
                exists = await self._redis.exists(session_key)
            except Exception as e:
                logger.error(f"[{query_hash}] Failed to check session '{session_key}': {e}")
                # Do not remove on error; assume the session is alive to avoid
                # false positives during transient Redis issues.
                continue

            if not exists:
                # Session key is missing: the WebSocket client has disconnected
                # or the WS Service container crashed and the TTL expired.
                # All members (client_id:sub_id) for this client_id are stale.
                stale_members.update(members)
                logger.debug(
                    f"[{query_hash}] Ghost detected: client '{client_id}' "
                    f"has no active session at '{session_key}'. "
                    f"Marking {len(members)} listener(s) for removal."
                )

        # --- Remove Stale Listeners ---
        if stale_members:
            try:
                # SREM removes one or more members from a set.
                # Returns the number of members that were removed.
                removed_count = await self._redis.srem(listeners_key, *stale_members)
                logger.info(f"[{query_hash}] Removed {removed_count} ghost listener(s): " f"{stale_members}")
            except Exception as e:
                logger.error(f"[{query_hash}] Failed to remove stale listeners from '{listeners_key}': {e}")
                return

        # --- Check if Listener Set is Now Empty ---
        try:
            remaining_count = await self._redis.scard(listeners_key)
        except Exception as e:
            logger.error(f"[{query_hash}] Failed to check listener count for '{listeners_key}': {e}")
            return

        if remaining_count == 0:
            # All listeners were ghosts. Clean up the entire subscription
            # to stop the Reporting Worker from polling the database.
            await self._cleanup_empty_subscription(query_hash)
        else:
            logger.debug(f"[{query_hash}] Ghost cleanup complete. Remaining valid listeners: {remaining_count}.")

    async def _cleanup_empty_subscription(self, query_hash: str) -> None:
        """
        Removes all Redis keys associated with an empty subscription.
        This prevents the Reporting Worker from executing SQL for
        subscriptions that have no active WebSocket clients.
        :param query_hash: The deterministic hash of the subscription.
        """
        registry_key = f"{REGISTRY_KEY_PREFIX}{query_hash}"
        listeners_key = f"{LISTENERS_KEY_PREFIX}{query_hash}"

        try:
            # Use a pipeline for atomic cleanup of all related keys.
            # This prevents race conditions where the Reporting Worker
            # might read the registry after the listener set is deleted.
            pipeline = self._redis.pipeline(transaction=False)
            pipeline.delete(registry_key)
            pipeline.delete(listeners_key)
            pipeline.srem(ACTIVE_HASHES_KEY, query_hash)
            await pipeline.execute()
            logger.info(
                f"[{query_hash}] Empty subscription fully cleaned up. "
                f"Removed registry, listeners, and active hash index."
            )
        except Exception as e:
            logger.error(f"[{query_hash}] Failed to clean up empty subscription: {e}")
