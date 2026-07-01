# ==============================================================================
# CnSS WebSocket Subscription Manager
# Manages the lifecycle of client subscriptions in Redis.
# Handles registration, listener tracking, and cleanup of the subscription
# registry to optimize Reporting Worker database queries.
# ==============================================================================

import logging
from typing import Tuple

from core.contracts.subscriptions import SubscribeRequest
from core.exceptions import RedisError
from core.redis.client import get_redis_client
from services.websocket.session import Session

# --- Module Logger ---
logger = logging.getLogger(__name__)

# --- Constants ---
# Redis key prefix for the subscription registry (stores JSON definition).
REGISTRY_KEY_PREFIX = "sub:registry:"
# Redis key prefix for the listener set (stores connected client IDs).
LISTENERS_KEY_PREFIX = "sub:listeners:"
# Redis key for the global index of active subscription hashes.
ACTIVE_HASHES_KEY = "sub:active_hashes"
# Redis Pub/Sub channel prefix for pushing aggregated data to clients.
PUSH_CHANNEL_PREFIX = "ws:push:"


# --- Subscription Manager Class ---
class SubscriptionManager:
    """
    Orchestrates the registration and removal of WebSocket subscriptions.
    Ensures the Reporting Worker only queries the database for active listeners.
    """

    def __init__(self) -> None:
        """Initializes the manager with the global Redis client instance."""
        self._redis = get_redis_client()

    def _get_registry_key(self, query_hash: str) -> str:
        """Constructs the Redis string key for a subscription's definition."""
        return f"{REGISTRY_KEY_PREFIX}{query_hash}"

    def _get_listeners_key(self, query_hash: str) -> str:
        """Constructs the Redis set key for a subscription's listener client IDs."""
        return f"{LISTENERS_KEY_PREFIX}{query_hash}"

    def _get_push_channel(self, query_hash: str) -> str:
        """Constructs the Redis Pub/Sub channel name for a subscription."""
        return f"{PUSH_CHANNEL_PREFIX}{query_hash}"

    async def subscribe(self, session: Session, request: SubscribeRequest) -> Tuple[str, str]:
        """
        Registers a new subscription for a client.
        Creates the registry entry if it doesn't exist, adds the client to the
        listener set, and indexes the hash for the Reporting Worker.
        
        :param session: The client's ephemeral session object.
        :param request: The validated subscription control message.
        :return: A tuple of (query_hash, pubsub_channel).
        """
        query_hash = request.query_hash
        registry_key = self._get_registry_key(query_hash)
        listeners_key = self._get_listeners_key(query_hash)
        push_channel = self._get_push_channel(query_hash)

        try:
            # Use a pipeline for atomic registration
            pipeline = self._redis.pipeline(transaction=False)

            # 1. Register the subscription definition (NX ensures we don't overwrite existing)
            # The registry stores the full request JSON for the Reporting Worker to parse
            registry_data = request.model_dump_json()
            pipeline.set(registry_key, registry_data, nx=True)

            # 2. Add the client ID to the listener set
            pipeline.sadd(listeners_key, session.client_id)

            # 3. Add the hash to the global active hashes index
            pipeline.sadd(ACTIVE_HASHES_KEY, query_hash)

            await pipeline.execute()

            # 4. Track the subscription in the client's session for GC on disconnect
            await session.add_subscription(query_hash)

            logger.info(
                f"Client '{session.client_id}' subscribed to '{request.target}' "
                f"on channel '{request.channel_id}' (hash: {query_hash})."
            )
            return query_hash, push_channel

        except Exception as e:
            logger.error(f"Failed to register subscription for client '{session.client_id}': {e}")
            raise RedisError(f"Subscription registration failed for client '{session.client_id}'") from e

    async def unsubscribe(self, session: Session, request: SubscribeRequest) -> str:
        """
        Removes a client from a subscription's listener set.
        If the listener set becomes empty, cleans up the registry and active index
        to stop the Reporting Worker from querying the database unnecessarily.
        
        :param session: The client's ephemeral session object.
        :param request: The validated unsubscription control message.
        :return: The query_hash that was unsubscribed from.
        """
        query_hash = request.query_hash
        registry_key = self._get_registry_key(query_hash)
        listeners_key = self._get_listeners_key(query_hash)

        try:
            # 1. Remove the client from the listener set
            await self._redis.srem(listeners_key, session.client_id)

            # 2. Check if the listener set is now empty
            listener_count = await self._redis.scard(listeners_key)
            
            if listener_count == 0:
                # No more clients listening. Clean up to save DB resources.
                pipeline = self._redis.pipeline(transaction=False)
                pipeline.delete(registry_key)
                pipeline.delete(listeners_key)
                pipeline.srem(ACTIVE_HASHES_KEY, query_hash)
                await pipeline.execute()
                
                logger.info(
                    f"Subscription '{query_hash}' has no more listeners. "
                    f"Registry and active index cleaned up."
                )
            else:
                logger.debug(
                    f"Client '{session.client_id}' unsubscribed from '{query_hash}'. "
                    f"Remaining listeners: {listener_count}."
                )

            # 3. Remove the subscription from the client's session tracking
            await session.remove_subscription(query_hash)

            return query_hash

        except Exception as e:
            logger.error(f"Failed to unregister subscription for client '{session.client_id}': {e}")
            raise RedisError(f"Subscription unregistration failed for client '{session.client_id}'") from e