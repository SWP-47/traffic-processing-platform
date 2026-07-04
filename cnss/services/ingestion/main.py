# ==============================================================================
# CnSS Ingestion Worker Entry Point
# Orchestrates the lifecycle of the high-performance UDP telemetry ingestion
# service. Handles initialization of infrastructure (Redis, TimescaleDB),
# starts the UDP server, and manages graceful shutdown upon OS signals.
# ==============================================================================

import asyncio
import logging
import signal
import sys

from core.config import settings
from core.database import close_db_pool, init_db_pool
from core.logging import setup_logging
from core.redis.client import close_redis_client, init_redis_client
from services.ingestion.buffer_manager import BufferManager
from services.ingestion.flusher import BackgroundFlusher
from services.ingestion.sequence_tracker import SequenceTracker
from services.ingestion.state_manager import StateManager
from services.ingestion.udp_server import UDPIngestionServer

# --- Module Logger ---
logger = logging.getLogger(__name__)

# --- Graceful Shutdown Event ---
# Global event used to signal the main asyncio loop to terminate gracefully.
# When set, the worker will stop accepting new UDP packets and teardown resources.
stop_event = asyncio.Event()


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


# --- Main Worker Lifecycle ---
async def run_ingestion_worker() -> None:
    """
    Main asynchronous entry point for the Ingestion Worker.
    Initializes dependencies, starts the UDP listener, and waits for shutdown.
    """
    # --- Infrastructure Initialization ---
    logger.info("Initializing Ingestion Worker infrastructure...")

    # Initialize Redis client (required for Sequence Tracking and Buffering)
    await init_redis_client()
    logger.info("Redis client initialized successfully.")

    # Initialize TimescaleDB connection pool (required for Background Flush)
    await init_db_pool()
    logger.info("TimescaleDB connection pool initialized successfully.")

    # --- Component Instantiation ---
    # Create the core processing components and wire them together.
    sequence_tracker = SequenceTracker()
    state_manager = StateManager(sequence_tracker=sequence_tracker)
    buffer_manager = BufferManager()
    background_flusher = BackgroundFlusher()

    # --- Background Flusher Startup ---
    # Start the background task that periodically flushes Redis buffers to TimescaleDB.
    await background_flusher.start()
    logger.info("Background Flusher started.")

    # --- UDP Server Startup ---
    # Pass the processing components to the UDP server for batch handling.
    udp_server = UDPIngestionServer(
        state_manager=state_manager, buffer_manager=buffer_manager, flusher=background_flusher
    )

    try:
        await udp_server.start()
        logger.info("Ingestion Worker is fully operational and listening for UDP traffic.")

        # --- Main Loop / Wait for Shutdown ---
        # Block the main coroutine until the stop_event is set by a signal handler
        await stop_event.wait()

    except Exception as e:
        logger.critical(f"Fatal error in Ingestion Worker: {e}", exc_info=True)
    finally:
        # --- Graceful Teardown Sequence ---
        logger.info("Starting graceful teardown sequence...")

        # 1. Stop UDP Server (closes socket, stops receiving new datagrams)
        await udp_server.stop()
        logger.info("UDP server stopped.")

        # 2. Stop Background Flusher (cancels the periodic flush task)
        await background_flusher.stop()
        logger.info("Background Flusher stopped.")

        # 3. Close Database Pool (terminates active TimescaleDB connections)
        await close_db_pool()
        logger.info("TimescaleDB connection pool closed.")

        # 4. Close Redis Client (terminates Redis connections)
        await close_redis_client()
        logger.info("Redis client closed.")

        logger.info("Ingestion Worker shutdown completed successfully.")


# --- Script Entry Point ---
def main() -> None:
    """
    Synchronous entry point. Configures logging and launches the asyncio event loop.
    """
    # Initialize logging configuration before anything else
    setup_logging()
    logger.info(f"Starting CnSS Ingestion Worker (UDP Port: {settings.cnss_udp_port})...")

    # Create the main asyncio event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Register OS signal handlers for graceful shutdown
    # Note: Windows does not support SIGTERM or add_signal_handler natively in the same way
    if sys.platform != "win32":
        loop.add_signal_handler(signal.SIGINT, _handle_sigint)
        loop.add_signal_handler(signal.SIGTERM, _handle_sigterm)
    else:
        logger.warning("Running on Windows: OS signal handlers for graceful shutdown are disabled.")

    try:
        # Run the main asynchronous worker lifecycle
        loop.run_until_complete(run_ingestion_worker())
    except KeyboardInterrupt:
        # Fallback for environments where SIGINT handler might not trigger
        if not stop_event.is_set():
            stop_event.set()
        loop.run_until_complete(run_ingestion_worker())
    finally:
        # Clean up the event loop
        loop.close()
        logger.info("Event loop closed. Exiting process.")


if __name__ == "__main__":
    main()
