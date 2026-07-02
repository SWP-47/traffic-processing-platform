# ==============================================================================
# CnSS Reporting Poller Module
# Implements the 1Hz polling loop for active WebSocket subscriptions.
# Reads active subscription hashes from Redis, checks for active listeners,
# delegates SQL execution to registered handlers, and publishes results
# to Redis Pub/Sub for real-time client updates.
# ==============================================================================

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import asyncpg
from pydantic import ValidationError

from core.contracts.subscriptions import SubscribeRequest
from core.database import get_db_pool
from core.redis.client import get_redis_client

# --- Module Logger ---
logger = logging.getLogger(__name__)

# --- Constants ---
# Redis key for the global index of active subscription hashes.
ACTIVE_HASHES_KEY = "sub:active_hashes"
# Redis key prefix for the subscription registry (stores JSON definition).
REGISTRY_KEY_PREFIX = "sub:registry:"
# Redis key prefix for the listener set (stores connected client IDs).
LISTENERS_KEY_PREFIX = "sub:listeners:"
# Redis Pub/Sub channel prefix for pushing aggregated data to clients.
PUSH_CHANNEL_PREFIX = "ws:push:"

# --- Base Subscription Handler ---
# Abstract base class for subscription-specific SQL handlers.
# New subscription targets (e.g., 'lan_hosts', 'telemetry') must inherit from this
# class and implement the `execute` method to provide safe, parameterized SQL queries.
class BaseSubscriptionHandler(ABC):
    """
    Abstract base class for handling subscription-specific SQL execution.
    Ensures a consistent interface for the Poller to invoke registered handlers.
    """
    
    @abstractmethod
    async def execute(self, db_pool: asyncpg.Pool, request: SubscribeRequest) -> Optional[Dict[str, Any]]:
        """
        Executes the target-specific SQL query and returns the formatted result.
        
        :param db_pool: The asyncpg connection pool for TimescaleDB.
        :param request: The validated subscription request containing target and params.
        :return: A dictionary containing the aggregated data, or None if no data.
        """
        pass

# --- Poller Class ---
class Poller:
    """
    Orchestrates the 1Hz polling loop for active WebSocket subscriptions.
    Manages the registry of subscription handlers and coordinates the flow:
    Redis Hash Discovery -> Listener Check -> SQL Execution -> Pub/Sub Publishing.
    """
    
    def __init__(self) -> None:
        """Initializes the Poller with Redis/DB clients and an empty handler registry."""
        self._redis = get_redis_client()
        self._db_pool = get_db_pool()
        self._task: Optional[asyncio.Task[None]] = None
        
        # Registry mapping target names (e.g., 'telemetry') to their handler instances.
        # This pattern allows easy addition of new subscription types without modifying the Poller.
        self._handlers: Dict[str, BaseSubscriptionHandler] = {}

    def register_handler(self, target: str, handler: BaseSubscriptionHandler) -> None:
        """
        Registers a subscription handler for a specific target type.
        
        :param target: The target name (e.g., 'telemetry', 'lan_hosts').
        :param handler: An instance of a class inheriting from BaseSubscriptionHandler.
        """
        if target in self._handlers:
            logger.warning(f"Handler for target '{target}' is being overwritten.")
        self._handlers[target] = handler
        logger.info(f"Registered subscription handler for target '{target}'.")

    async def start(self) -> None:
        """Starts the background asyncio task for the 1Hz polling loop."""
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._polling_loop())
            logger.info("Poller started. Polling interval: 1.0s.")

    async def stop(self) -> None:
        """Gracefully cancels the polling task."""
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            logger.info("Poller stopped.")

    async def _polling_loop(self) -> None:
        """
        Main infinite loop that sleeps for 1 second and then triggers
        a poll for all active subscriptions.
        """
        while True:
            try:
                await self._tick()
                await asyncio.sleep(1.0)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                # Catch-all to prevent the background task from dying silently
                logger.error(f"Unexpected error in Poller loop: {e}", exc_info=True)
                # Brief sleep to prevent tight error loops
                await asyncio.sleep(1.0)

    async def _tick(self) -> None:
        """
        Executes a single polling cycle:
        1. Retrieves active subscription hashes from Redis.
        2. Processes each subscription individually.
        """
        try:
            # Retrieve all active subscription hashes from the global index
            active_hashes = await self._redis.smembers(ACTIVE_HASHES_KEY)
        except Exception as e:
            logger.error(f"Failed to retrieve active hashes from Redis: {e}")
            return

        if not active_hashes:
            return

        # Process each subscription sequentially to prevent DB overload.
        # Given the 1Hz interval and fast SQL queries, sequential execution is safe.
        for query_hash in active_hashes:
            await self._process_subscription(query_hash)

    async def _process_subscription(self, query_hash: str) -> None:
        """
        Processes a single subscription: checks listeners, fetches registry,
        executes SQL via handler, and publishes results.
        
        :param query_hash: The deterministic hash of the subscription.
        """
        listeners_key = f"{LISTENERS_KEY_PREFIX}{query_hash}"
        
        # --- Optimization: Listener Check ---
        # If no WebSocket clients are listening, skip SQL execution
        # to save database resources.
        try:
            listeners = await self._redis.smembers(listeners_key)
        except Exception as e:
            logger.error(f"Failed to check listeners for hash '{query_hash}': {e}")
            return

        if not listeners:
            # No active listeners. Skip SQL execution.
            # Note: Ghost Cleaner handles stale hashes in active_hashes.
            return

        # --- Retrieve Subscription Registry ---
        registry_key = f"{REGISTRY_KEY_PREFIX}{query_hash}"
        try:
            registry_json = await self._redis.get(registry_key)
        except Exception as e:
            logger.error(f"Failed to retrieve registry for hash '{query_hash}': {e}")
            return

        if not registry_json:
            # Inconsistent state: hash in active set but registry missing.
            logger.warning(f"Registry missing for active hash '{query_hash}'. Skipping.")
            return

        # --- Parse Subscription Request ---
        try:
            request = SubscribeRequest.model_validate_json(registry_json)
        except ValidationError as e:
            logger.error(f"Invalid subscription JSON for hash '{query_hash}': {e}")
            # Optionally remove invalid hash from active set here, but let Ghost Cleaner handle it.
            return

        # --- Route to Registered Handler ---
        handler = self._handlers.get(request.target)
        if not handler:
            logger.warning(f"No handler registered for target '{request.target}' (hash: {query_hash})")
            return

        # --- Execute SQL and Publish ---
        try:
            result = await handler.execute(self._db_pool, request)
            
            if result is not None:
                # Publish the aggregated data to the Redis Pub/Sub channel
                push_channel = f"{PUSH_CHANNEL_PREFIX}{query_hash}"
                payload = json.dumps(result)
                await self._redis.publish(push_channel, payload)
                logger.debug(f"Published update for hash '{query_hash}' to '{push_channel}'.")
                
        except Exception as e:
            logger.error(f"Error executing handler for target '{request.target}' (hash: {query_hash}): {e}", exc_info=True)