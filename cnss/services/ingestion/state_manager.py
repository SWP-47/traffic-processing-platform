# ==============================================================================
# CnSS State Manager Module
# Orchestrates the Fast Path state updates in Redis for active channels.
# Handles activity tracking, drop accumulation, and TTL enforcement to ensure
# sub-millisecond status availability for the REST and WebSocket services.
# ==============================================================================

import logging
import time

from core.contracts.udp_contracts import TelemetryBatch
from core.exceptions import RedisError
from core.redis.client import get_redis_client
from services.ingestion.sequence_tracker import SequenceTracker

# --- Module Logger ---
logger = logging.getLogger(__name__)

# --- Constants ---
# Redis key prefix for the ephemeral channel state hash.
STATE_KEY_PREFIX = "channel:state:"

# TTL in seconds for the channel state key.
# If the CN dies and stops sending batches, the key expires, naturally indicating inactivity.
STATE_KEY_TTL_SEC = 6


# --- State Manager Class ---
class StateManager:
    """
    Manages the ephemeral Redis state for channel activity and drop tracking.
    Acts as the Fast Path orchestrator, updating Redis immediately upon batch receipt.
    """

    def __init__(self, sequence_tracker: SequenceTracker) -> None:
        """
        Initializes the state manager with the Redis client and sequence tracker.
        
        :param sequence_tracker: Instance of SequenceTracker for drop calculation.
        """
        self._redis = get_redis_client()
        self._tracker = sequence_tracker

    def _get_state_key(self, channel_id: str) -> str:
        """Constructs the Redis hash key for a specific channel's state."""
        return f"{STATE_KEY_PREFIX}{channel_id}"

    async def process_batch(self, batch: TelemetryBatch) -> None:
        """
        Processes a validated TelemetryBatch and updates the Redis state buffer.
        
        This method executes the Fast Path logic:
        1. Calculates dropped packets via SequenceTracker.
        2. Updates last_activity_at and is_active ONLY IF the batch contains packets.
        3. Accumulates dropped_delta.
        4. Refreshes the key TTL to 6 seconds.
        
        :param batch: The validated telemetry batch from the Communication Node.
        """
        state_key = self._get_state_key(batch.channel_id)
        
        # --- Sequence Tracking ---
        # Calculate drops and detect sequence resets before updating state
        dropped, is_reset = await self._tracker.process_sequence(
            batch.channel_id, batch.sequence
        )
        
        # --- Redis Pipeline Construction ---
        # Use a pipeline to batch Redis commands, minimizing network roundtrips
        # and ensuring high-throughput processing for the Fast Path.
        # transaction=False is sufficient here as we only need atomicity per-key, 
        # and avoiding MULTI/EXEC overhead improves IOPS.
        pipeline = self._redis.pipeline(transaction=False)
        
        # Accumulate dropped packets if any were detected in the sequence gap
        if dropped > 0:
            pipeline.hincrby(state_key, "dropped_delta", dropped)
            logger.debug(f"Channel '{batch.channel_id}': Accumulating {dropped} dropped packets.")
            
        # --- Activity Tracking & Reactivation ---
        # Empty keep-alive batches must NOT reset the activity timeout or reactivate the channel.
        # Only batches with actual packet metadata update the timestamp and active flag.
        if len(batch.packets) > 0:
            current_timestamp = time.time()
            # Use mapping to combine multiple HSET fields into a single Redis command
            pipeline.hset(
                state_key,
                mapping={
                    "last_activity_at": current_timestamp,
                    "is_active": 1,
                }
            )
            
        # --- TTL Enforcement ---
        # Refresh the TTL on every valid batch receipt.
        # If the CN dies, this key will expire in 6 seconds, marking the channel inactive.
        pipeline.expire(state_key, STATE_KEY_TTL_SEC)
        
        # --- Execution ---
        try:
            await pipeline.execute()
        except Exception as e:
            logger.error(f"Failed to execute state update pipeline for channel '{batch.channel_id}': {e}")
            raise RedisError(f"State update failed for channel '{batch.channel_id}'") from e