# ==============================================================================
# CnSS Sequence Tracker Module
# Maintains the last processed sequence number per channel in Redis.
# Handles initial state, drop calculation, and sequence reset detection to
# ensure reliable telemetry ingestion and accurate packet drop metrics.
# ==============================================================================

import logging
from typing import Tuple

from core.config import settings
from core.redis.client import get_redis_client
from core.exceptions import RedisError

# --- Module Logger ---
logger = logging.getLogger(__name__)

# --- Constants ---
# Redis key prefix for storing the last sequence number per channel.
SEQ_KEY_PREFIX = "channel:seq:"


# --- Sequence Tracker Class ---
class SequenceTracker:
    """
    Tracks and validates sequence numbers for incoming telemetry batches.
    Calculates dropped packets and detects sequence resets using Redis.
    """

    def __init__(self) -> None:
        """Initializes the tracker with the global Redis client instance."""
        self._redis = get_redis_client()

    def _get_seq_key(self, channel_id: str) -> str:
        """Constructs the Redis key for a specific channel's sequence."""
        return f"{SEQ_KEY_PREFIX}{channel_id}"

    async def process_sequence(self, channel_id: str, incoming_sequence: int) -> Tuple[int, bool]:
        """
        Processes the incoming sequence number for a given channel.
        
        :param channel_id: The identifier of the channel.
        :param incoming_sequence: The sequence number from the TelemetryBatch.
        :return: A tuple containing (calculated_drops, is_reset).
                 calculated_drops is the number of dropped packets (0 if out-of-order or reset).
                 is_reset is True if a sequence reset was detected.
        """
        seq_key = self._get_seq_key(channel_id)
        
        try:
            # Retrieve the last known sequence number from Redis
            last_sequence_str = await self._redis.get(seq_key)
            
            # --- Initial State Handling ---
            # If the key does not exist, this is a new channel or post-crash state.
            # Store the incoming sequence as the baseline without calculating drops.
            if last_sequence_str is None:
                await self._redis.set(seq_key, incoming_sequence)
                logger.info(f"Initial sequence baseline set for channel '{channel_id}': {incoming_sequence}")
                return 0, False

            last_sequence = int(last_sequence_str)

            # --- Sequence Reset Detection ---
            # Detect abnormal backward jumps indicating a CN reboot or counter reset.
            # Uses the configurable threshold from settings to allow dynamic tuning.
            if last_sequence - incoming_sequence > settings.sequence_reset_threshold:
                logger.warning(
                    f"Sequence reset detected for channel '{channel_id}'. "
                    f"Last: {last_sequence}, Incoming: {incoming_sequence}. Resetting baseline."
                )
                # Forcefully update the sequence baseline
                await self._redis.set(seq_key, incoming_sequence)
                # Reset drop counter for this batch (return 0 drops)
                return 0, True

            # --- Normal Sequence Processing ---
            # If incoming sequence is strictly greater than the expected next sequence,
            # calculate the number of dropped packets in the gap.
            if incoming_sequence > last_sequence + 1:
                dropped = incoming_sequence - (last_sequence + 1)
                # Update the last sequence in Redis to the current incoming value
                await self._redis.set(seq_key, incoming_sequence)
                logger.debug(f"Channel '{channel_id}': {dropped} packets dropped.")
                return dropped, False
            
            # If incoming sequence is less than or equal to the last sequence,
            # it's an out-of-order or duplicate delivery. Ignore it gracefully.
            if incoming_sequence <= last_sequence:
                logger.debug(
                    f"Channel '{channel_id}': Out-of-order/duplicate packet ignored. "
                    f"Last: {last_sequence}, Incoming: {incoming_sequence}"
                )
                return 0, False

            # If incoming_sequence == last_sequence + 1, it's a perfect sequential packet.
            # Update the sequence baseline and return 0 drops.
            await self._redis.set(seq_key, incoming_sequence)
            return 0, False

        except Exception as e:
            # Wrap unexpected Redis errors in our custom exception to maintain
            # a consistent error handling strategy across the ingestion pipeline.
            logger.error(f"Failed to process sequence for channel '{channel_id}': {e}")
            raise RedisError(f"Sequence tracking failed for channel '{channel_id}'") from e