# ==============================================================================
# CnSS Reporting Worker Entry Point
# Orchestrates the lifecycle of the background aggregator service.
# Handles initialization of infrastructure, starts periodic polling,
# ghost cleanup, drop flushing, and timeout enforcement tasks,
# and manages graceful shutdown upon OS signals.
# ==============================================================================

import asyncio
import logging
import signal
import sys

from core.database import close_db_pool, init_db_pool
from core.logging import setup_logging
from core.redis.client import close_redis_client, init_redis_client
from services.reporting.drop_flusher import DropFlusher
from services.reporting.ghost_cleaner import GhostCleaner
from services.reporting.poller import Poller
from services.reporting.timeout_enforcer import TimeoutEnforcer
from services.reporting.handlers import HANDLER_REGISTRY


# --- Module Logger ---
logger = logging.getLogger(__name__)

# --- Graceful Shutdown Event ---
# Global event used to signal the main asyncio loop to terminate gracefully.
# When set, the worker will stop all background tasks and teardown resources.
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
async def run_reporting_worker() -> None:
    """
    Main asynchronous entry point for the Reporting Worker.
    Initializes dependencies, starts background tasks, and waits for shutdown.
    """
    # --- Infrastructure Initialization ---
    logger.info("Initializing Reporting Worker infrastructure...")
    
    # Initialize Redis client (required for polling, pub/sub, and state sync)
    await init_redis_client()
    logger.info("Redis client initialized successfully.")
    
    # Initialize TimescaleDB connection pool (required for SQL execution and updates)
    await init_db_pool()
    logger.info("TimescaleDB connection pool initialized successfully.")

    # --- Component Instantiation ---
    # Create the core background processing components.
    ghost_cleaner = GhostCleaner()
    drop_flusher = DropFlusher()
    timeout_enforcer = TimeoutEnforcer()
    
    # The Poller coordinates the 1Hz subscription loop and delegates 
    # ghost cleaning and drop flushing logic to the respective components.
    poller = Poller()
    for target, handler in HANDLER_REGISTRY.items():
        poller.register_handler(target, handler)

    try:
        # --- Background Tasks Startup ---
        # Start the main polling loop and auxiliary maintenance tasks.
        await poller.start()
        logger.info("Poller started. Reading 'sub:active_hashes' every 1 second.")
        
        await ghost_cleaner.start()
        logger.info("Ghost Cleaner started.")
        
        await drop_flusher.start()
        logger.info("Drop Flusher started.")
        
        await timeout_enforcer.start()
        logger.info("Timeout Enforcer started.")

        logger.info("Reporting Worker is fully operational.")

        # --- Main Loop / Wait for Shutdown ---
        # Block the main coroutine until the stop_event is set by a signal handler
        await stop_event.wait()

    except Exception as e:
        logger.critical(f"Fatal error in Reporting Worker: {e}", exc_info=True)
    finally:
        # --- Graceful Teardown Sequence ---
        logger.info("Starting graceful teardown sequence...")
        
        # 1. Stop Background Tasks
        await poller.stop()
        await ghost_cleaner.stop()
        await drop_flusher.stop()
        await timeout_enforcer.stop()
        logger.info("All background tasks stopped.")

        # 2. Close Database Pool
        await close_db_pool()
        logger.info("TimescaleDB connection pool closed.")

        # 3. Close Redis Client
        await close_redis_client()
        logger.info("Redis client closed.")

        logger.info("Reporting Worker shutdown completed successfully.")

# --- Script Entry Point ---
def main() -> None:
    """
    Synchronous entry point. Configures logging and launches the asyncio event loop.
    """
    # Initialize logging configuration before anything else
    setup_logging()
    logger.info("Starting CnSS Reporting Worker...")

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
        # Run the main asynchronous worker lifecycle
        loop.run_until_complete(run_reporting_worker())
    except KeyboardInterrupt:
        # Fallback for environments where SIGINT handler might not trigger
        if not stop_event.is_set():
            stop_event.set()
        loop.run_until_complete(run_reporting_worker())
    finally:
        # Clean up the event loop
        loop.close()
        logger.info("Event loop closed. Exiting process.")

if __name__ == "__main__":
    main()