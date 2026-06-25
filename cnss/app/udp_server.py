import asyncio
import json
import logging
from datetime import datetime, timezone

from pydantic import ValidationError

from .models import TelemetryBatch
from .store import state_store
from .config import settings
from .broadcast import broadcast_telemetry_update
from .db import insert_packet_flows  # ← NEW

logger = logging.getLogger(__name__)


class TelemetryUDPProtocol(asyncio.DatagramProtocol):
    def __init__(self):
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport
        logger.info(f"UDP Telemetry Listener bound to port {settings.cnss_udp_port}")

    def datagram_received(self, data: bytes, addr):
        logger.debug(f"Raw UDP datagram from {addr[0]}:{addr[1]} ({len(data)} bytes)")
        try:
            text = data.decode("utf-8")
            payload = json.loads(text)
            batch = TelemetryBatch(**payload)
        except UnicodeDecodeError:
            logger.error(f"Invalid UTF-8 from {addr}. Dropping.")
            return
        except (json.JSONDecodeError, ValidationError) as exc:
            logger.error(f"Invalid payload from {addr}: {exc}. Dropping.")
            return

        logger.info(
            f"TelemetryBatch | ch={batch.channel_id} seq={batch.sequence} "
            f"packets={len(batch.packets)} src={addr[0]}"
        )
        server_received_at = datetime.now(timezone.utc)
        asyncio.create_task(self._process_batch(batch, server_received_at))

    async def _process_batch(self, batch: TelemetryBatch, received_at: datetime):
        # in-memory sequence tracking (no DB query)
        dropped = await state_store.update_channel_activity(
            channel_id=batch.channel_id,
            incoming_sequence=batch.sequence,
            server_received_at=received_at,
        )
        try:
            # persist to TimescaleDB
            await insert_packet_flows(
                channel_id=batch.channel_id,
                timestamp=batch.timestamp,
                packets=batch.packets,
            )
        except Exception as exc:
            logger.error(
                f"Database insert failed for channel {batch.channel_id}: {exc}. Batch dropped gracefully."
            )


async def start_udp_server(host: str = "0.0.0.0", port: int = settings.cnss_udp_port):
    loop = asyncio.get_running_loop()
    transport, protocol = await loop.create_datagram_endpoint(
        TelemetryUDPProtocol, local_addr=(host, port)
    )
    return transport
