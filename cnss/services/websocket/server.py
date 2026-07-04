# ==============================================================================
# CnSS WebSocket Server Module
# Orchestrates the lifecycle of persistent WebSocket connections.
# Handles HTTP-to-WS upgrades, authentication, session management,
# heartbeat enforcement, and message routing to the subscription engine.
# ==============================================================================

import asyncio
import json
import logging
import uuid
from typing import Any, Callable, Tuple

import websockets
import websockets.legacy.server
from pydantic import ValidationError

# Import serve, WebSocketServer, and WebSocketServerProtocol from the legacy module
from websockets.legacy.server import (
    WebSocketServerProtocol,
    serve,
)

from core.config import settings
from core.contracts.auth import TokenPayload
from core.contracts.subscriptions import SubscribeRequest
from core.database import get_db_pool
from core.exceptions import (
    ClientResponseError,
    ResourceNotFoundError,
)
from services.websocket.auth import MissingChannelError, authenticate_connection
from services.websocket.gc import GarbageCollector
from services.websocket.session import Session
from services.websocket.snapshot import SnapshotFetcher
from services.websocket.subscription import SubscriptionManager

# --- Module Logger ---
logger = logging.getLogger(__name__)


# --- WebSocket Server Class ---
class WebSocketServer:
    """
    Main entry point for the WebSocket service.
    Manages the server lifecycle and delegates connection handling.
    """

    def __init__(
        self,
        register_connection: Callable[[str, WebSocketServerProtocol], None],
        unregister_connection: Callable[[str], None],
    ) -> None:
        """
        Initializes the server components and dependency injections.

        :param register_connection: Callback to register active WebSocket connections.
        :param unregister_connection: Callback to remove connections from the registry.
        """
        self._server: websockets.legacy.server.WebSocketServer | None = None
        self._sub_manager = SubscriptionManager()
        self._gc = GarbageCollector()
        self._snapshot_fetcher = SnapshotFetcher()
        self._register_connection = register_connection
        self._unregister_connection = unregister_connection

    # --- Server Lifecycle ---

    async def start(self) -> None:
        """
        Starts the WebSocket server and binds to the configured host/port.
        Uses the 'websockets' library to handle the HTTP upgrade and protocol.
        """
        logger.info(f"Starting WebSocket server on {settings.cnss_host}:{settings.cnss_ws_port}...")

        # websockets.serve handles the HTTP handshake and upgrades to WS.
        # We pass the '_handler' method to process each new connection.
        self._server = await serve(
            self._handler,
            settings.cnss_host,
            settings.cnss_ws_port,
            # Enable library-level pings to detect dead connections at the transport layer.
            # Session-level TTL is handled separately in Redis.
            ping_interval=20,
            ping_timeout=20,
        )
        logger.info("WebSocket server started successfully.")

    async def stop(self) -> None:
        """
        Gracefully shuts down the WebSocket server.
        Closes all active connections and stops accepting new ones.
        """
        if self._server:
            logger.info("Stopping WebSocket server...")
            self._server.close()
            await self._server.wait_closed()
            logger.info("WebSocket server stopped.")

    # --- Connection Handler ---

    async def _handler(self, websocket: WebSocketServerProtocol) -> None:
        """
        Main coroutine for each connected client.
        Orchestrates authentication, session creation, message processing, and cleanup.
        """
        client_id = str(uuid.uuid4())
        session: Session | None = None
        heartbeat_task: asyncio.Task[Any] | None = None

        try:
            # --- Phase 1: Authentication & Validation ---
            # Extracts and validates JWT and channel_id from the connection URL.
            # Raises ClientResponseError if validation fails (mapped to 4001-4004).
            payload, channel_id = await self._authenticate_connection(websocket)

            # --- Phase 2: Session Initialization ---
            # Creates an ephemeral session in Redis with a strict TTL.
            session = Session(client_id=client_id, channel_id=channel_id, payload=payload)
            await session.create()

            # --- Phase 3: Connection Registration ---
            # Register the connection in the global registry for Pub/Sub routing.
            self._register_connection(client_id, websocket)

            # --- Phase 4: Heartbeat Task ---
            # Start background task to refresh session TTL every 5 seconds.
            heartbeat_task = asyncio.create_task(self._heartbeat_loop(session))

            # --- Phase 5: Message Processing Loop ---
            # Listens for incoming JSON control messages (subscribe/unsubscribe).
            async for raw_message in websocket:
                # websockets can yield bytes for binary frames; decode to str for JSON parsing
                if isinstance(raw_message, bytes):
                    raw_message = raw_message.decode("utf-8")

                await self._process_message(websocket, session, raw_message)

        except ClientResponseError as e:
            # Handle expected validation errors with specific WS close codes.
            logger.warning(f"Connection rejected for client {client_id}: {e.message} (Code: {e.ws_close_code})")
            await websocket.close(e.ws_close_code or 1011, e.message)

        except websockets.exceptions.ConnectionClosed:
            # Client disconnected normally or network dropped.
            logger.debug(f"Client {client_id} disconnected.")

        except Exception as e:
            # Handle unexpected internal errors.
            logger.error(f"Internal error for client {client_id}: {e}", exc_info=True)
            await websocket.close(1011, "Internal Server Error")

        finally:
            # --- Phase 6: Cleanup ---
            # Ensure resources are released regardless of how the connection ended.
            self._unregister_connection(client_id)

            if heartbeat_task:
                heartbeat_task.cancel()
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    pass

            if session:
                # GC handles listener set cleanup; session.destroy() removes the session hash.
                await self._gc.cleanup(client_id)
                await session.destroy()

    # --- Helper Methods ---

    async def _authenticate_connection(self, websocket: WebSocketServerProtocol) -> Tuple[TokenPayload, str]:
        """
        Validates the connection request: JWT, Channel ID, Scope, and Existence.
        Delegates JWT/Scope logic to 'auth.py' and performs Channel Existence check here.
        """
        # 1. Delegate JWT and Scope validation to the auth module.
        # Expected to raise AuthError (4001) or AuthorizationError (4003).
        payload, channel_id = await authenticate_connection(websocket)

        # 2. Check for missing channel_id (if auth module didn't catch it).
        if not channel_id:
            raise MissingChannelError()

        # 3. Confirm Channel Existence (Architecture 2.3.1).
        # We check the persistent 'channels' table to allow connections to inactive channels.
        # If the channel was never registered, we reject with 4004.
        if not await self._check_channel_exists(channel_id):
            raise ResourceNotFoundError(
                message=f"Channel '{channel_id}' does not exist.",
            )

        return payload, channel_id

    async def _check_channel_exists(self, channel_id: str) -> bool:
        """
        Verifies if the channel_id exists in the persistent registry.
        Uses the database pool for a reliable check.
        """
        pool = get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT 1 FROM channels WHERE channel_id = $1", channel_id)
            return row is not None

    async def _heartbeat_loop(self, session: Session, interval: float = 5.0) -> None:
        """
        Background task to keep the session alive in Redis.
        Refreshes the TTL every `interval` seconds (Architecture 2.3.7).
        Continues running even if refresh_ttl fails to prevent orphaned connections.
        :param session: The ephemeral session object.
        :param interval: Sleep interval in seconds (default 5.0, overridable for testing).
        """
        try:
            while True:
                await asyncio.sleep(interval)
                try:
                    await session.refresh_ttl()
                except Exception as e:
                    # Log the error but continue the loop
                    # Architecture §2.3.7: heartbeat failure should not crash the connection handler
                    logger.error(f"Failed to refresh TTL for session '{session.client_id}': {e}")
        except asyncio.CancelledError:
            # Expected when the connection closes
            pass

    async def _process_message(self, websocket: WebSocketServerProtocol, session: Session, raw_message: str) -> None:
        """
        Parses, validates, and routes incoming JSON control messages.
        """
        try:
            data = json.loads(raw_message)
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON received from {session.client_id}")
            return

        try:
            # Validate against Pydantic contract.
            request = SubscribeRequest(**data)
        except ValidationError as e:
            logger.warning(f"Invalid subscription payload from {session.client_id}: {e}")
            return

        # --- Subscription Scope Validation (Architecture 2.3.8) ---
        # The channel_id in the message MUST match the one from the connection URL.
        if request.channel_id != session.channel_id:
            logger.warning(
                f"Channel mismatch for {session.client_id}: " f"URL={session.channel_id}, Msg={request.channel_id}"
            )
            # Close connection with 4003 as per architecture.
            await websocket.close(4003, "Subscription channel_id mismatch.")
            return

        # --- Route to Subscription Manager ---
        if request.action == "subscribe":
            await self._handle_subscribe(websocket, session, request)
        elif request.action == "unsubscribe":
            await self._sub_manager.unsubscribe(session, request)

    async def _handle_subscribe(
        self,
        websocket: WebSocketServerProtocol,
        session: Session,
        request: SubscribeRequest,
    ) -> None:
        """
        Handles the subscribe action with strict Initial Snapshot ordering.
        Architecture §2.3.4 mandates:
        1. SUBSCRIBE ws:push:{query_hash} in Redis (register in listener set).
        2. Execute read-only query against TimescaleDB (Initial Snapshot).
        3. Push Initial Snapshot to the client.
        This order prevents the race condition where a Pub/Sub update arrives
        between the DB query and the Redis subscription, which would cause
        the client to miss the update.
        """
        # --- Step 1: Register subscription in Redis ---
        # Adds client to sub:listeners:{hash}, writes sub:registry:{hash},
        # and indexes hash in sub:active_hashes for the Reporting Worker.
        query_hash, push_channel = await self._sub_manager.subscribe(session, request)
        logger.debug(
            f"Client '{session.client_id}' registered for '{push_channel}' " f"(hash: {query_hash}, id: {request.id})."
        )

        # --- Step 2: Fetch Initial Snapshot from TimescaleDB ---
        # Executes a read-only query to get the current state of the subscription.
        # This is the "cold start" data that prevents the client from waiting
        # up to 1 second for the first Reporting Worker tick.
        try:
            snapshot = await self._snapshot_fetcher.fetch_snapshot(
                channel_id=request.channel_id,
                target=request.target,
                params=request.params,
            )
        except ResourceNotFoundError as e:
            logger.warning(f"Snapshot fetch failed for client '{session.client_id}': {e.message}")
            # Do not close connection; the client may still receive updates via Pub/Sub.
            return
        except Exception as e:
            logger.error(
                f"Unexpected error fetching snapshot for client '{session.client_id}': {e}",
                exc_info=True,
            )
            return

        # --- Step 3: Push Initial Snapshot to the client ---
        try:
            # Inject the client-provided 'id' into the snapshot payload
            # so the MUI can associate this initial state with the correct subscription.
            if isinstance(snapshot, dict):
                snapshot["id"] = request.id

            await websocket.send(json.dumps(snapshot))
            logger.debug(
                f"Initial snapshot sent to client '{session.client_id}' " f"for '{request.target}' (id: {request.id})."
            )
        except Exception as e:
            logger.error(f"Failed to send initial snapshot to client '{session.client_id}': {e}")
