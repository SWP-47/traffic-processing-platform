# ==============================================================================
# CnSS WebSocket Pub/Sub Consumer
# Manages the global Redis Pub/Sub subscription for real-time data pushes.
# Listens to all 'ws:push:{query_hash}' channels and routes incoming messages
# to the appropriate connected WebSocket clients based on the listener registry.
# ==============================================================================
import asyncio
import json
import logging
from typing import Any, Callable, Dict, List, Optional

from core.exceptions import RedisError
from core.redis.client import get_redis_client

# --- Module Logger ---
logger = logging.getLogger(__name__)

# --- Constants ---
# Redis Pub/Sub pattern to subscribe to all subscription push channels.
PUSH_CHANNEL_PATTERN = "ws:push:*"

# Prefix length to extract the query_hash from the channel name.
PUSH_CHANNEL_PREFIX_LEN = len("ws:push:")


# --- Pub/Sub Consumer Class ---
class PubSubConsumer:
    """
    Global background task that consumes Redis Pub/Sub messages and routes
    them to connected WebSocket clients. Uses pattern subscription to
    dynamically handle new subscription channels without reconnection.
    """

    def __init__(
        self,
        get_websocket: Callable[[str], Optional[Any]],
    ) -> None:
        """
        Initializes the consumer with a callback to retrieve active WebSocket connections.
        :param get_websocket: Function that returns a WebSocketServerProtocol for a given client_id.
        """
        self._get_websocket = get_websocket
        self._task: Optional[asyncio.Task[None]] = None
        self._pubsub: Optional[Any] = None

    async def start(self) -> None:
        """Starts the background Pub/Sub listener task."""
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._listen_loop())
            logger.info("Pub/Sub Consumer started. Listening for real-time updates.")

    async def stop(self) -> None:
        """Gracefully cancels the Pub/Sub listener task and cleans up resources."""
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._pubsub:
            await self._pubsub.unsubscribe()
            await self._pubsub.close()
            self._pubsub = None
            logger.info("Pub/Sub Consumer stopped.")

    async def _listen_loop(self) -> None:
        """
        Main infinite loop that subscribes to the push channel pattern
        and processes incoming messages.
        """
        redis_client = get_redis_client()
        self._pubsub = redis_client.pubsub()
        try:
            # Subscribe to all channels matching the push pattern
            await self._pubsub.psubscribe(PUSH_CHANNEL_PATTERN)
            logger.debug(f"Subscribed to Pub/Sub pattern: {PUSH_CHANNEL_PATTERN}")

            # Listen for messages indefinitely
            async for message in self._pubsub.listen():
                if message["type"] == "pmessage":
                    await self._handle_message(message)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Fatal error in Pub/Sub Consumer loop: {e}", exc_info=True)
            raise RedisError("Pub/Sub Consumer loop terminated unexpectedly") from e

    async def _handle_message(self, message: Dict[str, Any]) -> None:
        """
        Processes a single Pub/Sub message and routes it to connected clients.
        Injects the client-specific 'sub_id' into the payload as the "id" field.
        :param message: The raw Redis Pub/Sub message dictionary.
        """
        # Extract the query_hash from the channel name (e.g., "ws:push:abc123" -> "abc123")
        channel_name = message["channel"]
        if isinstance(channel_name, bytes):
            channel_name = channel_name.decode("utf-8")
        query_hash = channel_name[PUSH_CHANNEL_PREFIX_LEN:]

        raw_data = message["data"]

        # Parse the JSON payload from the Reporting Worker
        try:
            if isinstance(raw_data, bytes):
                raw_data = raw_data.decode("utf-8")
            payload = json.loads(raw_data)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error(f"Failed to parse Pub/Sub message for hash '{query_hash}': {e}")
            return

        # Retrieve the list of composite listener keys (client_id:sub_id)
        redis_client = get_redis_client()
        listeners_key = f"sub:listeners:{query_hash}"
        try:
            listener_members = await redis_client.smembers(listeners_key)
        except Exception as e:
            logger.error(f"Failed to retrieve listeners for hash '{query_hash}': {e}")
            return

        if not listener_members:
            return

        # Group listeners by client_id to avoid redundant WebSocket lookups
        # Structure: { "client_uuid": ["sub_id_1", "sub_id_2"] }
        grouped_listeners: Dict[str, List[str]] = {}
        for member in listener_members:
            member_str = member.decode("utf-8") if isinstance(member, bytes) else member
            c_id, s_id = member_str.rsplit(":", 1)
            grouped_listeners.setdefault(c_id, []).append(s_id)

        # Route the message to each connected client
        for client_id, sub_ids in grouped_listeners.items():
            websocket = self._get_websocket(client_id)
            if websocket is None:
                # Client disconnected but hasn't been cleaned up from the listener set yet.
                # The Garbage Collector will handle this eventually.
                logger.debug(f"Client '{client_id}' not found in active connections. Skipping.")
                continue

            for sub_id in sub_ids:
                # Inject the sub_id into the payload as the "id" field
                payload_with_id = {**payload, "id": sub_id}
                json_payload = json.dumps(payload_with_id)

                try:
                    await websocket.send(json_payload)
                    logger.debug(f"Pushed update to client '{client_id}' (sub: {sub_id}) for hash '{query_hash}'.")
                except Exception as e:
                    logger.warning(f"Failed to send message to client '{client_id}': {e}")
                    # Do not remove from listener set here; let the connection handler's GC do it.
