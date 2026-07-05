# ==============================================================================
# CnSS WebSocket Session Manager
# Manages the ephemeral session state for connected WebSocket clients in Redis.
# Enforces strict TTL (10s) and provides heartbeat refresh (5s) to detect
# orphaned connections and prevent memory leaks in the subscription registry.
# ==============================================================================
import logging
import time
from typing import List, cast

from core.contracts.auth import TokenPayload
from core.exceptions import RedisError
from core.redis.client import get_redis_client

# --- Module Logger ---
logger = logging.getLogger(__name__)

# --- Constants ---
# Redis key prefix for the ephemeral WebSocket session hash.
SESSION_KEY_PREFIX = "ws:session:"
# Redis key suffix for the session's active subscription tracking set.
SESSION_SUBS_SUFFIX = ":subs"

# TTL in seconds for the session key.
# If the WebSocket Service crashes, the key expires, preventing orphaned subscriptions.
SESSION_TTL_SEC = 10


# --- Session Class ---
class Session:
    """
    Represents an ephemeral WebSocket client session stored in Redis.
    Tracks client identity, channel access, and active subscriptions for rapid cleanup.
    """

    def __init__(self, client_id: str, channel_id: str, payload: TokenPayload) -> None:
        """
        Initializes the session object with client identity and JWT claims.
        :param client_id: Unique UUID for this WebSocket connection.
        :param channel_id: The channel ID validated during connection upgrade.
        :param payload: The decoded JWT payload containing user identity and role.
        """
        self.client_id = client_id
        self.channel_id = channel_id
        self.user_id = payload.sub
        self.role = payload.role
        self._redis = get_redis_client()

    def _get_session_key(self) -> str:
        """Constructs the Redis hash key for this session."""
        return f"{SESSION_KEY_PREFIX}{self.client_id}"

    def _get_subs_key(self) -> str:
        """Constructs the Redis set key for this session's active subscriptions."""
        return f"{SESSION_KEY_PREFIX}{self.client_id}{SESSION_SUBS_SUFFIX}"

    async def create(self) -> None:
        """
        Creates the ephemeral session in Redis with a strict TTL.
        Stores client identity and initializes the subscription tracking set.
        """
        session_key = self._get_session_key()
        subs_key = self._get_subs_key()

        try:
            # Use a pipeline to batch session creation and TTL enforcement
            pipeline = self._redis.pipeline(transaction=False)

            # Store session metadata in a Hash
            pipeline.hset(
                session_key,
                mapping={
                    "client_id": self.client_id,
                    "channel_id": self.channel_id,
                    "user_id": self.user_id,
                    "role": self.role,
                    "created_at": time.time(),
                },
            )
            # Set strict TTL to prevent orphaned sessions on container crash
            pipeline.expire(session_key, SESSION_TTL_SEC)

            # Initialize the subscription tracking set (ensure clean state)
            pipeline.delete(subs_key)

            await pipeline.execute()
            logger.debug(f"Session created for client '{self.client_id}' with TTL {SESSION_TTL_SEC}s.")
        except Exception as e:
            logger.error(f"Failed to create session for client '{self.client_id}': {e}")
            raise RedisError(f"Session creation failed for client '{self.client_id}'") from e

    async def refresh_ttl(self) -> None:
        """
        Refreshes the session TTL to prevent expiration during active connection.
        Called by the background heartbeat task every 5 seconds.
        """
        session_key = self._get_session_key()
        try:
            # Reset TTL to 10 seconds
            await self._redis.expire(session_key, SESSION_TTL_SEC)
            logger.debug(f"Session TTL refreshed for client '{self.client_id}'.")
        except Exception as e:
            logger.error(f"Failed to refresh TTL for client '{self.client_id}': {e}")
            # Do not raise here; heartbeat failure should not crash the connection handler

    async def destroy(self) -> None:
        """
        Removes the session and its subscription tracking set from Redis.
        Called during graceful disconnect or connection failure.
        """
        session_key = self._get_session_key()
        subs_key = self._get_subs_key()
        try:
            await self._redis.delete(session_key, subs_key)
            logger.debug(f"Session destroyed for client '{self.client_id}'.")
        except Exception as e:
            logger.error(f"Failed to destroy session for client '{self.client_id}': {e}")

    # ==========================================================================
    # Subscription Tracking (Updated for Parallel Subscriptions)
    # ==========================================================================

    async def add_subscription(self, query_hash: str, sub_id: str) -> None:
        """
        Registers a subscription hash in the session's tracking set.
        Stores as 'query_hash:sub_id' to allow multiple parallel subscriptions
        to the same query_hash from the same client.
        :param query_hash: The deterministic hash of the subscription parameters.
        :param sub_id: The client-generated unique identifier for this subscription instance.
        """
        subs_key = self._get_subs_key()
        try:
            # Save the composite key to distinguish parallel subscriptions
            await self._redis.sadd(subs_key, f"{query_hash}:{sub_id}")
            logger.debug(f"Subscription '{query_hash}:{sub_id}' added to session '{self.client_id}'.")
        except Exception as e:
            logger.error(f"Failed to add subscription to session '{self.client_id}': {e}")

    async def remove_subscription(self, query_hash: str, sub_id: str) -> None:
        """
        Removes a specific subscription instance from the session's tracking set.
        :param query_hash: The deterministic hash of the subscription parameters.
        :param sub_id: The client-generated unique identifier for this subscription instance.
        """
        subs_key = self._get_subs_key()
        try:
            await self._redis.srem(subs_key, f"{query_hash}:{sub_id}")
            logger.debug(f"Subscription '{query_hash}:{sub_id}' removed from session '{self.client_id}'.")
        except Exception as e:
            logger.error(f"Failed to remove subscription from session '{self.client_id}': {e}")

    async def get_subscriptions(self) -> List[str]:
        """
        Retrieves all active subscription instances for this session.
        Used by the Garbage Collector during disconnect to clean up listener sets.
        :return: List of strings in format 'query_hash:sub_id'.
        """
        subs_key = self._get_subs_key()
        try:
            members = await self._redis.smembers(subs_key)
            return cast(list[str], list(members)) if members else []
        except Exception as e:
            logger.error(f"Failed to get subscriptions for session '{self.client_id}': {e}")
            return []
