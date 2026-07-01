# ==============================================================================
# CnSS WebSocket Garbage Collector
# Handles cleanup of Redis subscription state upon client disconnect.
# Removes the client from all active listener sets and deletes the subscription
# registry key if a listener set becomes empty, preventing the Reporting Worker
# from executing unnecessary SQL queries for abandoned subscriptions.
# ==============================================================================

import logging
from typing import List

from core.exceptions import RedisError
from core.redis.client import get_redis_client

# --- Module Logger ---
logger = logging.getLogger(__name__)

# --- Constants ---
# Redis key prefix for the session's active subscription tracking set.
# This set holds all query_hash values the client is currently subscribed to.
SESSION_SUBS_KEY_PREFIX = "ws:session:"
SESSION_SUBS_KEY_SUFFIX = ":subs"

# Redis key prefixes for the subscription registry and listener sets.
# These must match the constants in services/websocket/subscription.py.
REGISTRY_KEY_PREFIX = "sub:registry:"
LISTENERS_KEY_PREFIX = "sub:listeners:"

# Redis key for the global index of active subscription hashes.
# Used by the Reporting Worker to discover which subscriptions need SQL execution.
ACTIVE_HASHES_KEY = "sub:active_hashes"


# --- Garbage Collector Class ---
class GarbageCollector:
    """
    Orchestrates the cleanup of Redis subscription state when a WebSocket
    client disconnects (gracefully or due to container crash).
    Ensures no orphaned listener entries remain in Redis.
    """

    def __init__(self) -> None:
        """Initializes the garbage collector with the global Redis client."""
        self._redis = get_redis_client()

    def _get_session_subs_key(self, client_id: str) -> str:
        """Constructs the Redis set key for a client's active subscription hashes."""
        return f"{SESSION_SUBS_KEY_PREFIX}{client_id}{SESSION_SUBS_KEY_SUFFIX}"

    def _get_registry_key(self, query_hash: str) -> str:
        """Constructs the Redis string key for a subscription's definition."""
        return f"{REGISTRY_KEY_PREFIX}{query_hash}"

    def _get_listeners_key(self, query_hash: str) -> str:
        """Constructs the Redis set key for a subscription's listener client IDs."""
        return f"{LISTENERS_KEY_PREFIX}{query_hash}"

    async def cleanup(self, client_id: str) -> None:
        """
        Performs full cleanup for a disconnected client.
        Steps:
        1. Retrieve all active subscription hashes from the client's session tracking set.
        2. For each subscription, remove the client from the listener set.
        3. If a listener set becomes empty, delete the registry and active hash index.

        :param client_id: The UUID of the disconnected WebSocket client.
        """
        try:
            # --- Retrieve Active Subscriptions ---
            # The session tracking set (ws:session:{client_id}:subs) holds all
            # query_hashes this client was subscribed to. This enables rapid cleanup
            # without scanning all listener sets in Redis.
            session_subs_key = self._get_session_subs_key(client_id)
            query_hashes: List[str] = []

            members = await self._redis.smembers(session_subs_key)
            if members:
                query_hashes = list(members)

            if not query_hashes:
                logger.debug(f"No active subscriptions to clean up for client '{client_id}'.")
                return

            logger.info(
                f"Garbage collecting {len(query_hashes)} subscription(s) for client '{client_id}'."
            )

            # --- Process Each Subscription ---
            # Iterate over all subscriptions and remove the client from each listener set.
            # If a listener set becomes empty, clean up the registry to stop DB queries.
            for query_hash in query_hashes:
                await self._cleanup_subscription(client_id, query_hash)

        except Exception as e:
            # GC failure should not crash the connection handler.
            # Log the error and continue; orphaned entries will be cleaned up
            # by the Reporting Worker's Ghost Subscription Prevention mechanism.
            logger.error(f"Garbage collection failed for client '{client_id}': {e}")

    async def _cleanup_subscription(self, client_id: str, query_hash: str) -> None:
        """
        Removes a client from a specific subscription's listener set.
        If the set becomes empty, deletes the registry and active hash index entry.

        :param client_id: The UUID of the disconnected client.
        :param query_hash: The deterministic hash of the subscription.
        """
        listeners_key = self._get_listeners_key(query_hash)
        registry_key = self._get_registry_key(query_hash)

        try:
            # --- Remove Client from Listener Set ---
            # SREM returns 1 if the member was removed, 0 if it was not present.
            # This handles the case where the client already unsubscribed gracefully.
            removed = await self._redis.srem(listeners_key, client_id)
            if not removed:
                logger.debug(
                    f"Client '{client_id}' was not in listener set for '{query_hash}'."
                )
                return

            # --- Check if Listener Set is Empty ---
            # If no clients are listening, the Reporting Worker should skip SQL execution
            # for this subscription to save database resources.
            listener_count = await self._redis.scard(listeners_key)

            if listener_count == 0:
                # --- Delete Registry and Active Hash Index ---
                # Use a pipeline for atomic cleanup of all related keys.
                # This prevents race conditions where the Reporting Worker
                # might read the registry after the listener set is deleted.
                pipeline = self._redis.pipeline(transaction=False)
                pipeline.delete(registry_key)
                pipeline.delete(listeners_key)
                pipeline.srem(ACTIVE_HASHES_KEY, query_hash)
                await pipeline.execute()

                logger.info(
                    f"Subscription '{query_hash}' has no more listeners. "
                    f"Registry and active index cleaned up by GC."
                )
            else:
                logger.debug(
                    f"Client '{client_id}' removed from '{query_hash}'. "
                    f"Remaining listeners: {listener_count}."
                )

        except Exception as e:
            # Do not re-raise; partial GC is better than no GC.
            # The Reporting Worker's Ghost Subscription Prevention will handle
            # stale entries by checking if ws:session:{client_id} exists.
            logger.error(
                f"Failed to clean up subscription '{query_hash}' for client '{client_id}': {e}"
            )