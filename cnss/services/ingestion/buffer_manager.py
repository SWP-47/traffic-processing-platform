# ==============================================================================
# CnSS Buffer Manager Module
# Manages the high-speed Redis Capped List for raw packet metadata buffering.
# Pushes flattened packet records to Redis and enforces strict length limits
# to prevent Out-Of-Memory (OOM) crashes if the database flusher lags.
# ==============================================================================

import json
import logging
from datetime import datetime, timezone
from typing import List

from core.config import settings
from core.contracts.udp_contracts import TelemetryBatch
from core.exceptions import RedisError
from core.redis.client import get_redis_client

# --- Module Logger ---
logger = logging.getLogger(__name__)

# --- Constants ---
# Redis key prefix for the high-speed packet buffer lists.
BUFFER_KEY_PREFIX = "udp:buffer:"


# --- Buffer Manager Class ---
class BufferManager:
    """
    Handles the serialization and Redis ingestion of raw packet metadata.
    Implements a Capped List pattern using explicit LLEN checks, LPUSH,
    and LTRIM to guarantee bounded memory usage per channel.
    """

    def __init__(self) -> None:
        """Initializes the buffer manager with the global Redis client instance."""
        self._redis = get_redis_client()

    def _get_buffer_key(self, channel_id: str) -> str:
        """Constructs the Redis list key for a specific channel's packet buffer."""
        return f"{BUFFER_KEY_PREFIX}{channel_id}"

    async def push_packets(self, batch: TelemetryBatch) -> None:
        """
        Serializes and pushes packet metadata into the Redis capped list.

        Flattens the TelemetryBatch into individual packet records matching
        the 'packet_flows' TimescaleDB schema. Enforces the capped list constraint
        by checking LLEN before LPUSH and using LTRIM to discard the oldest entries
        if the threshold is exceeded.

        :param batch: The validated telemetry batch containing packet metadata.
        """
        # Skip processing if the batch contains no actual packet data (e.g., keep-alive)
        if not batch.packets:
            return

        buffer_key = self._get_buffer_key(batch.channel_id)

        # --- Data Serialization ---
        # Convert the batch timestamp (Unix epoch seconds) to an ISO 8601 UTC string.
        # This ensures seamless insertion into TimescaleDB's TIMESTAMPTZ column later.
        ingestion_time = datetime.fromtimestamp(batch.timestamp, tz=timezone.utc).isoformat()

        # Flatten packets into JSON strings matching the 'packet_flows' table schema
        serialized_records: List[str] = []
        for packet in batch.packets:
            record = {
                "channel_id": batch.channel_id,
                "time": ingestion_time,
                "direction": packet.direction,
                "src_ip": str(packet.src_ip),
                "dst_ip": str(packet.dst_ip),
                "src_port": packet.src_port,
                "dst_port": packet.dst_port,
                "protocol": packet.protocol,
                "size": packet.size,
            }
            serialized_records.append(json.dumps(record))

        try:
            # --- Capped List Enforcement (LLEN Check) ---
            # Explicitly check the current length before pushing to prevent OOM.
            current_len = await self._redis.llen(buffer_key)

            if current_len + len(serialized_records) > settings.redis_udp_buffer_max_len:
                keep_count = settings.redis_udp_buffer_max_len - len(serialized_records)
                if keep_count < 0:
                    # Batch larger than max capacity — drop it
                    return

                # If the incoming batch itself is larger than the max buffer capacity,
                # drop the entire batch to protect the system.
                if keep_count < 0:
                    logger.warning(
                        f"Channel '{batch.channel_id}': Incoming batch size ({len(serialized_records)}) "
                        f"exceeds max buffer capacity ({settings.redis_udp_buffer_max_len}). Dropping batch."
                    )
                    return

                # LTRIM keeps elements from index 0 to keep_count - 1.
                # Since we use LPUSH, the newest items are at the head (index 0).
                # This effectively discards the oldest entries from the tail.
                await self._redis.ltrim(buffer_key, 0, keep_count - 1)
                logger.debug(
                    f"Channel '{batch.channel_id}': Buffer exceeded {settings.redis_udp_buffer_max_len}. "
                    f"Trimmed oldest entries to make room for {len(serialized_records)} new packets."
                )

            # --- Push to Redis ---
            # Push the new serialized records to the head of the list (LPUSH).
            # This ensures the newest packets are at index 0, aligning with the LTRIM logic.
            await self._redis.lpush(buffer_key, *serialized_records)

            logger.debug(
                f"Channel '{batch.channel_id}': Buffered {len(serialized_records)} packets. "
                f"Current buffer length: {current_len + len(serialized_records)}."
            )

        except Exception as e:
            logger.error(f"Failed to push packets to Redis buffer for channel '{batch.channel_id}': {e}")
            raise RedisError(f"Buffer push failed for channel '{batch.channel_id}'") from e
