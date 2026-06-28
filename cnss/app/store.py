import asyncio
import logging
from typing import List, Set, Optional, Dict
from datetime import datetime, timezone
from .models import ChannelState, WSClientSession

logger = logging.getLogger(__name__)


class StateStore:
    def __init__(self):
        self._channels: Dict[str, ChannelState] = {}
        self._lock = asyncio.Lock()

    async def get_channel(self, channel_id: str) -> Optional[ChannelState]:
        async with self._lock:
            return self._channels.get(channel_id)

    async def get_all_channels(self) -> List[ChannelState]:
        async with self._lock:
            return list(self._channels.values())

    async def get_or_create_channel(self, channel_id: str) -> ChannelState:
        async with self._lock:
            if channel_id not in self._channels:
                logger.info(f"Auto-creating new channel: {channel_id}")
                self._channels[channel_id] = ChannelState(
                    channel_id=channel_id,
                    last_activity_timestamp=datetime.now(timezone.utc),
                    last_sequence=None,
                )
            return self._channels[channel_id]

    async def remove_channel(self, channel_id: str) -> bool:
        async with self._lock:
            if channel_id in self._channels:
                del self._channels[channel_id]
                logger.info(
                    f"Channel {channel_id} removed from registry (Garbage Collected)."
                )
                return True
            return False

    async def update_channel_activity(
        self, channel_id: str, incoming_sequence: int, server_received_at: datetime
    ) -> int:
        async with self._lock:
            if channel_id not in self._channels:
                self._channels[channel_id] = ChannelState(
                    channel_id=channel_id,
                    last_activity_timestamp=server_received_at,
                    last_sequence=incoming_sequence,
                    dropped_batches=0,
                )
                return 0

            channel = self._channels[channel_id]
            dropped_batches = 0
            if channel.last_sequence is not None:
                if incoming_sequence > channel.last_sequence + 1:
                    dropped_batches = incoming_sequence - (channel.last_sequence + 1)
                    channel.dropped_batches += dropped_batches
                    logger.warning(
                        f"Channel {channel_id}: Detected {dropped_batches} dropped batches."
                    )

                if incoming_sequence > channel.last_sequence:
                    channel.last_sequence = incoming_sequence
            else:
                channel.last_sequence = incoming_sequence

            channel.last_activity_timestamp = server_received_at
            return dropped_batches

    async def get_and_reset_dropped_batches(self, channel_id: str) -> int:
        async with self._lock:
            if channel_id in self._channels:
                dropped = self._channels[channel_id].dropped_batches
                self._channels[channel_id].dropped_batches = 0
                return dropped
            return 0

    async def add_listener(self, channel_id: str, listener: WSClientSession) -> bool:
        async with self._lock:
            if channel_id in self._channels:
                self._channels[channel_id].listeners.add(listener)
                return True
            return False

    async def remove_listener(self, channel_id: str, listener: WSClientSession) -> bool:
        async with self._lock:
            if channel_id in self._channels:
                self._channels[channel_id].listeners.discard(listener)
                return True
            return False

    async def get_listeners(self, channel_id: str) -> Set[WSClientSession]:
        async with self._lock:
            if channel_id in self._channels:
                return self._channels[channel_id].listeners.copy()
            return set()

    async def get_subscribers_by_target(
        self, channel_id: str, target: str
    ) -> List[WSClientSession]:
        async with self._lock:
            if channel_id in self._channels:
                return [
                    session
                    for session in self._channels[channel_id].listeners
                    if target in session.subscriptions
                ]
            return []


state_store = StateStore()
