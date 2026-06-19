import asyncio
import json
import logging
from datetime import datetime, timezone
from pydantic import ValidationError
from .models import TelemetryBatch
from .store import state_store
from .config import settings

logger = logging.getLogger(__name__)


class TelemetryUDPProtocol(asyncio.DatagramProtocol):
    def __init__(self):
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport
        logger.info(
            f"UDP Telemetry Listener successfully bound to port {settings.cnss_udp_port}"
        )

    def datagram_received(self, data: bytes, addr):
        logger.debug(
            f"Raw UDP datagram received from {addr[0]}:{addr[1]} ({len(data)} bytes)"
        )

        try:
            text = data.decode("utf-8")
            payload = json.loads(text)
            batch = TelemetryBatch(**payload)
        except UnicodeDecodeError:
            logger.error(f"Received invalid UTF-8 from {addr}. Dropping.")
            return
        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(f"Invalid payload from {addr}: {e}. Dropping.")
            return

        logger.info(
            f"TelemetryBatch received | channel: {batch.channel_id} | "
            f"seq: {batch.sequence} | source: {addr[0]}"
        )

        server_received_at = datetime.now(timezone.utc)

        asyncio.create_task(self._process_batch(batch, server_received_at))

    async def _process_batch(self, batch: TelemetryBatch, received_at: datetime):
        # 1. Update State & Calculate Drops
        await state_store.update_channel_activity(
            channel_id=batch.channel_id,
            incoming_sequence=batch.sequence,
            server_received_at=received_at,
        )

        # 2. Broadcast to WebSocket Listeners
        listeners = await state_store.get_listeners(batch.channel_id)
        if listeners:
            # TODO: Construct telemetry_update payload and send to listeners
            pass


async def start_udp_server(host: str = "0.0.0.0", port: int = 5140):
    """
    Initializes and starts the UDP datagram endpoint.
    Returns the transport object so it can be closed gracefully on shutdown.
    """
    loop = asyncio.get_running_loop()
    transport, protocol = await loop.create_datagram_endpoint(
        TelemetryUDPProtocol, local_addr=(host, port)
    )
    return transport
