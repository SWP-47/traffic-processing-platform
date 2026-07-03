# ==============================================================================
# CnSS WebSocket Service Entry Point
# Orchestrates the lifecycle of the persistent client connection management
# and subscription routing gateway. Handles initialization of infrastructure,
# starts the WebSocket server and Pub/Sub consumer, and manages graceful
# shutdown upon OS signals.
# ==============================================================================

# CRITICAL: Apply logging patch BEFORE any other imports
# to fix compatibility issues with passlib and uvicorn.
import core.logging_patch  # noqa: F401

import asyncio
import logging
import signal
import sys
from typing import Dict, Optional

from websockets.legacy.server import WebSocketServerProtocol

from core.config import settings
from core.database import close_db_pool, init_db_pool
from core.logging import setup_logging
from core.redis.client import close_redis_client, init_redis_client
from services.websocket.pubsub_consumer import PubSubConsumer
from services.websocket.server import WebSocketServer

# --- Module Logger ---
logger = logging.getLogger(__name__)

# --- Graceful Shutdown Event ---
# Global event used to signal the main asyncio loop to terminate gracefully.
# When set, the service will stop accepting new WebSocket connections and teardown resources.
stop_event = asyncio.Event()

# --- Active WebSocket Connections Registry ---
# Thread-safe dictionary mapping client_id to WebSocketServerProtocol.
# Used by PubSubConsumer to route messages to the correct client.
# Note: asyncio is single-threaded, so no explicit lock is needed for dict operations.
_active_connections: Dict[str, WebSocketServerProtocol] = {}


# --- Connection Registry Accessors ---
def register_connection(client_id: str, websocket: WebSocketServerProtocol) -> None:
    """
    Registers an active WebSocket connection in the global registry.
    Called by WebSocketServer when a new client successfully authenticates.
    """
    _active_connections[client_id] = websocket
    logger.debug(f"Connection registered: {client_id} (total: {len(_active_connections)})")


def unregister_connection(client_id: str) -> None:
    """
    Removes a WebSocket connection from the global registry.
    Called by WebSocketServer when a client disconnects (gracefully or due to error).
    """
    if _active_connections.pop(client_id, None):
        logger.debug(f"Connection unregistered: {client_id} (total: {len(_active_connections)})")


def get_connection(client_id: str) -> Optional[WebSocketServerProtocol]:
    """
    Retrieves an active WebSocket connection by client_id.
    Used by PubSubConsumer to route messages to the correct client.
    Returns None if the client is not connected.
    """
    return _active_connections.get(client_id)


# --- Signal Handling ---
def _handle_sigint() -> None:
    """
    Callback for SIGINT (Ctrl+C). Triggers the graceful shutdown sequence.
    """
    logger.warning("Received SIGINT. Initiating graceful shutdown...")
    stop_event.set()


def _handle_sigterm() -> None:
    """
    Callback for SIGTERM (Docker stop / Kubernetes). Triggers graceful shutdown.
    """
    logger.warning("Received SIGTERM. Initiating graceful shutdown...")
    stop_event.set()


# --- Main Service Lifecycle ---
async def run_websocket_service() -> None:
    """
    Main asynchronous entry point for the WebSocket Service.
    Initializes dependencies, starts the WebSocket listener and Pub/Sub consumer,
    and waits for shutdown.
    """
    # --- Infrastructure Initialization ---
    logger.info("Initializing WebSocket Service infrastructure...")

    # Initialize Redis client (required for Pub/Sub, session tracking, and revocation checks)
    await init_redis_client()
    logger.info("Redis client initialized successfully.")

    # Initialize TimescaleDB connection pool (required for initial snapshots and history queries)
    await init_db_pool()
    logger.info("TimescaleDB connection pool initialized successfully.")

    # --- Component Instantiation ---
    # Create the core WebSocket server component with connection registry accessors
    ws_server = WebSocketServer(
        register_connection=register_connection,
        unregister_connection=unregister_connection,
    )

    # Create the Pub/Sub consumer with a callback to lookup active connections
    pubsub_consumer = PubSubConsumer(get_websocket=get_connection)

    try:
        # --- WebSocket Server Startup ---
        await ws_server.start()
        logger.info(
            f"WebSocket Service is fully operational and listening on "
            f"{settings.cnss_host}:{settings.cnss_ws_port}."
        )

        # --- Pub/Sub Consumer Startup ---
        await pubsub_consumer.start()
        logger.info("Pub/Sub Consumer started. Listening for real-time updates from Reporting Worker.")

        # --- Main Loop / Wait for Shutdown ---
        # Block the main coroutine until the stop_event is set by a signal handler
        await stop_event.wait()

    except Exception as e:
        logger.critical(f"Fatal error in WebSocket Service: {e}", exc_info=True)
    finally:
        # --- Graceful Teardown Sequence ---
        logger.info("Starting graceful teardown sequence...")

        # 1. Stop Pub/Sub Consumer (cancels the listener task)
        await pubsub_consumer.stop()
        logger.info("Pub/Sub Consumer stopped.")

        # 2. Stop WebSocket Server (closes active connections and stops accepting new ones)
        await ws_server.stop()
        logger.info("WebSocket server stopped.")

        # 3. Close Database Pool (terminates active TimescaleDB connections)
        await close_db_pool()
        logger.info("TimescaleDB connection pool closed.")

        # 4. Close Redis Client (terminates Redis connections)
        await close_redis_client()
        logger.info("Redis client closed.")

        # 5. Clear the connection registry
        _active_connections.clear()
        logger.info("Connection registry cleared.")

        logger.info("WebSocket Service shutdown completed successfully.")


# --- Script Entry Point ---
def main() -> None:
    """
    Synchronous entry point. Configures logging and launches the asyncio event loop.
    """
    # Initialize logging configuration before anything else
    setup_logging()

    logger.info(
        f"Starting CnSS WebSocket Service (HTTP/WS Port: {settings.cnss_ws_port})..."
    )

    # Create the main asyncio event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Register OS signal handlers for graceful shutdown
    if sys.platform != "win32":
        loop.add_signal_handler(signal.SIGINT, _handle_sigint)
        loop.add_signal_handler(signal.SIGTERM, _handle_sigterm)
    else:
        logger.warning("Running on Windows: OS signal handlers for graceful shutdown are disabled.")

    try:
        # Run the main asynchronous service lifecycle
        loop.run_until_complete(run_websocket_service())
    except KeyboardInterrupt:
        # Fallback for environments where SIGINT handler might not trigger
        if not stop_event.is_set():
            stop_event.set()
        loop.run_until_complete(run_websocket_service())
    finally:
        # Clean up the event loop
        loop.close()
        logger.info("Event loop closed. Exiting process.")


if __name__ == "__main__":
    main()