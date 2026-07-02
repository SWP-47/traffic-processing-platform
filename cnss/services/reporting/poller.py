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
from services.reporting.handlers.base import BaseSubscriptionHandler

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
        logger.debug("Poller initialized with Redis and DB clients.")

    def register_handler(self, target: str, handler: BaseSubscriptionHandler) -> None:
        """
        Registers a subscription handler for a specific target type.
        
        :param target: The target name (e.g., 'telemetry', 'lan_hosts').
        :param handler: An instance of a class inheriting from BaseSubscriptionHandler.
        """
        if target in self._handlers:
            logger.warning(f"Handler for target '{target}' is being overwritten.")
        self._handlers[target] = handler
        logger.debug(f"Registered subscription handler for target '{target}'.")
        logger.info(f"Registered subscription handler for target '{target}'.")

    async def start(self) -> None:
        """Starts the background asyncio task for the 1Hz polling loop."""
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._polling_loop())
            logger.debug("Poller background task created.")
            logger.info("Poller started. Polling interval: 1.0s.")

    async def stop(self) -> None:
        """Gracefully cancels the polling task."""
        if self._task and not self._task.done():
            logger.debug("Cancelling Poller background task...")
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            logger.debug("Poller background task cancelled successfully.")
            logger.info("Poller stopped.")

    async def _polling_loop(self) -> None:
        """
        Main infinite loop that sleeps for 1 second and then triggers
        a poll for all active subscriptions.
        """
        logger.debug("Polling loop started.")
        while True:
            try:
                logger.debug("Starting polling tick...")
                await self._tick()
                logger.debug("Polling tick completed. Sleeping for 1.0s...")
                await asyncio.sleep(1.0)
            except asyncio.CancelledError:
                logger.debug("Polling loop received cancellation signal.")
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
        logger.debug("Executing polling tick...")
        try:
            # Retrieve all active subscription hashes from the global index
            active_hashes = await self._redis.smembers(ACTIVE_HASHES_KEY)
            logger.debug(f"Retrieved {len(active_hashes) if active_hashes else 0} active subscription hashes from Redis.")
        except Exception as e:
            logger.error(f"Failed to retrieve active hashes from Redis: {e}")
            return

        if not active_hashes:
            logger.debug("No active subscriptions found. Tick completed.")
            return

        # Process each subscription sequentially to prevent DB overload.
        # Given the 1Hz interval and fast SQL queries, sequential execution is safe.
        logger.debug(f"Processing {len(active_hashes)} subscription(s)...")
        for query_hash in active_hashes:
            await self._process_subscription(query_hash)
        
        logger.debug(f"Tick completed. Processed {len(active_hashes)} subscription(s).")

    async def _process_subscription(self, query_hash: str) -> None:
        """
        Processes a single subscription: checks listeners, fetches registry,
        executes SQL via handler, and publishes results.
        
        :param query_hash: The deterministic hash of the subscription.
        """
        logger.debug(f"[{query_hash}] Starting subscription processing...")
        listeners_key = f"{LISTENERS_KEY_PREFIX}{query_hash}"
        
        # --- Optimization: Listener Check ---
        # Architecture §2.2.3: If no WebSocket clients are listening, skip SQL execution
        # to save database resources.
        logger.debug(f"[{query_hash}] Checking listeners at key: {listeners_key}")
        try:
            listeners = await self._redis.smembers(listeners_key)
            listener_count = len(listeners) if listeners else 0
            logger.debug(f"[{query_hash}] Found {listener_count} listener(s).")
        except Exception as e:
            logger.error(f"[{query_hash}] Failed to check listeners: {e}")
            return

        if not listeners:
            # No active listeners. Skip SQL execution.
            # Note: Ghost Cleaner handles stale hashes in active_hashes.
            logger.debug(f"[{query_hash}] No active listeners. Skipping SQL execution.")
            return

        # --- Retrieve Subscription Registry ---
        registry_key = f"{REGISTRY_KEY_PREFIX}{query_hash}"
        logger.debug(f"[{query_hash}] Fetching registry from key: {registry_key}")
        try:
            registry_json = await self._redis.get(registry_key)
        except Exception as e:
            logger.error(f"[{query_hash}] Failed to retrieve registry: {e}")
            return

        if not registry_json:
            # Inconsistent state: hash in active set but registry missing.
            logger.warning(f"[{query_hash}] Registry missing for active hash. Skipping.")
            return
        
        logger.debug(f"[{query_hash}] Registry retrieved. Size: {len(registry_json)} bytes.")

        # --- Parse Subscription Request ---
        logger.debug(f"[{query_hash}] Parsing subscription request...")
        try:
            request = SubscribeRequest.model_validate_json(registry_json)
            logger.debug(f"[{query_hash}] Parsed request: target='{request.target}', channel='{request.channel_id}'")
        except ValidationError as e:
            logger.error(f"[{query_hash}] Invalid subscription JSON: {e}")
            # Optionally remove invalid hash from active set here, but let Ghost Cleaner handle it.
            return

        # --- Route to Registered Handler ---
        logger.debug(f"[{query_hash}] Looking up handler for target '{request.target}'...")
        handler = self._handlers.get(request.target)
        if not handler:
            logger.warning(f"[{query_hash}] No handler registered for target '{request.target}'")
            logger.debug(f"[{query_hash}] Available handlers: {list(self._handlers.keys())}")
            return
        
        logger.debug(f"[{query_hash}] Handler found: {handler.__class__.__name__}")

        # --- Execute SQL and Publish ---
        logger.debug(f"[{query_hash}] Executing SQL query via handler...")
        try:
            result = await handler.execute(self._db_pool, request)
            
            if result is None:
                logger.debug(f"[{query_hash}] Handler returned None. No data to publish.")
                return
            
            # Serialize result for publishing
            payload = json.dumps(result)
            logger.debug(f"[{query_hash}] Handler returned data. Payload size: {len(payload)} bytes.")
            
            # Publish the aggregated data to the Redis Pub/Sub channel
            push_channel = f"{PUSH_CHANNEL_PREFIX}{query_hash}"
            logger.debug(f"[{query_hash}] Publishing to channel: {push_channel}")
            await self._redis.publish(push_channel, payload)
            logger.debug(f"[{query_hash}] Successfully published update to '{push_channel}'.")
            logger.info(f"[{query_hash}] Published telemetry update ({len(payload)} bytes) to {listener_count} listener(s).")
                
        except Exception as e:
            logger.error(f"[{query_hash}] Error executing handler for target '{request.target}': {e}", exc_info=True)