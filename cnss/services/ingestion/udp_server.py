# ==============================================================================
# CnSS UDP Ingestion Server
# Implements an asynchronous UDP server using asyncio.DatagramProtocol.
# Receives TelemetryBatch payloads from Communication Nodes, enforces MTU 
# constraints, validates JSON structure, and passes valid batches to the 
# processing pipeline.
# ==============================================================================

import asyncio
import json
import logging
from typing import Optional, Tuple, Callable, Awaitable

from pydantic import ValidationError

from core.config import settings
from core.contracts.udp_contracts import TelemetryBatch
from core.exceptions import ConfigurationError

# --- Module Logger ---
logger = logging.getLogger(__name__)


class UDPIngestionProtocol(asyncio.DatagramProtocol):
    """
    Asyncio protocol implementation for handling incoming UDP datagrams.
    Responsible for raw byte reception, MTU validation, and JSON parsing.
    """

    def __init__(self, on_batch_received: Callable[[TelemetryBatch, Tuple[str, int]], Awaitable[None]]):
        """
        Initializes the protocol with a callback for successfully parsed batches.
        
        :param on_batch_received: Async callback to process TelemetryBatch.
        """
        self.transport: Optional[asyncio.DatagramTransport] = None
        self._on_batch_received = on_batch_received

    def connection_made(self, transport: asyncio.DatagramTransport) -> None:
        """
        Called when the UDP socket is successfully bound and ready to receive data.
        """
        self.transport = transport
        logger.info("UDP socket is ready and listening for incoming datagrams.")

    def datagram_received(self, data: bytes, addr: Tuple[str, int]) -> None:
        """
        Triggered whenever a UDP datagram is received from a Communication Node.
        Performs MTU validation, JSON decoding, and Pydantic model validation.
        """
        # --- MTU Validation ---
        # MTU constraint 
        if len(data) > settings.cnss_udp_mtu:
            logger.warning(
                f"Oversized UDP payload from {addr}. "
                f"Size: {len(data)} bytes, Max allowed: {settings.cnss_udp_mtu} bytes."
            )

        # --- JSON Decoding ---
        try:
            payload = json.loads(data.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.warning(f"Failed to decode UDP payload from {addr}: {e}")
            return

        # --- Pydantic Validation ---
        try:
            batch = TelemetryBatch(**payload)
        except ValidationError as e:
            logger.warning(f"Invalid TelemetryBatch structure from {addr}: {e.errors()}")
            return

        # --- Pass to Processing Pipeline ---
        # Schedule the async callback to hand off the validated batch
        logger.debug(
            f"Scheduling the async callback to hand off "
            f"the validated batch from {addr} (Seq: {batch.sequence})"
            )
        asyncio.create_task(self._on_batch_received(batch, addr))

    def error_received(self, exc: Exception) -> None:
        """
        Called when a previous send or receive operation raises an OSError.
        """
        logger.error(f"UDP protocol error: {exc}")

    def connection_lost(self, exc: Optional[Exception]) -> None:
        """
        Called when the transport is closed.
        """
        if exc:
            logger.warning(f"UDP connection lost with error: {exc}")
        else:
            logger.info("UDP transport closed gracefully.")


class UDPIngestionServer:
    """
    High-level wrapper for the asyncio UDP server.
    Manages the lifecycle of the DatagramProtocol and the underlying transport.
    """

    def __init__(self):
        self.transport: Optional[asyncio.DatagramTransport] = None
        self.protocol: Optional[UDPIngestionProtocol] = None

    async def _handle_batch(self, batch: TelemetryBatch, addr: Tuple[str, int]) -> None:
        """
        Callback invoked by the protocol when a valid TelemetryBatch is received.
        This is the integration point for the Sequence Tracker and Buffer Manager.
        
        :param batch: Validated telemetry data.
        :param addr: Source IP and port of the Communication Node.
        """
        # TODO: Integrate with Sequence Tracker and Buffer Manager in subsequent steps
        logger.debug(
            f"Received valid TelemetryBatch from {addr} | "
            f"Channel: {batch.channel_id} | "
            f"Packets: {len(batch.packets)} | "
            f"Seq: {batch.sequence}"
        )

    async def start(self) -> None:
        """
        Binds the UDP socket and starts listening for incoming datagrams.
        """
        loop = asyncio.get_running_loop()
        
        # Validate port configuration
        if not (0 < settings.cnss_udp_port <= 65535):
            raise ConfigurationError(f"Invalid UDP port configured: {settings.cnss_udp_port}")

        logger.info(f"Binding UDP server to 0.0.0.0:{settings.cnss_udp_port}...")
        
        # Create the UDP endpoint
        transport, protocol = await loop.create_datagram_endpoint(
            lambda: UDPIngestionProtocol(on_batch_received=self._handle_batch),
            local_addr=("0.0.0.0", settings.cnss_udp_port),
        )
        
        self.transport = transport
        self.protocol = protocol
        logger.info(f"UDP Ingestion Server successfully bound to port {settings.cnss_udp_port}.")

    async def stop(self) -> None:
        """
        Gracefully closes the UDP transport and releases the socket.
        """
        if self.transport is not None:
            logger.info("Closing UDP transport...")
            self.transport.close()
            # Wait briefly to ensure the socket is fully closed
            await asyncio.sleep(0.1)
            self.transport = None
            self.protocol = None
            logger.info("UDP transport closed.")