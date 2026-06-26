from abc import ABC, abstractmethod
from typing import List, Set, Any, Optional
from datetime import datetime
from ..models import ChannelState
from ..models import WSClientSession


class StateStore(ABC):
    """
    Abstract interface for CnSS state management.
    """

    @abstractmethod
    async def get_channel(self, channel_id: str) -> Optional[ChannelState]:
        """Retrieve a channel's state. Returns None if not found."""
        pass

    @abstractmethod
    async def get_all_channels(self) -> List[ChannelState]:
        """Retrieve all known channels (for REST API /health and /channels)."""
        pass

    @abstractmethod
    async def get_or_create_channel(self, channel_id: str) -> ChannelState:
        """Fetch channel or initialize a new one (AC 2)."""
        pass

    @abstractmethod
    async def update_channel_activity(
        self, channel_id: str, incoming_sequence: int, server_received_at: datetime
    ) -> int:
        """
        Updates sequence and activity timestamp.
        Returns the number of dropped batches (AC 3 & AC 4).
        """
        pass

    @abstractmethod
    async def add_listener(self, channel_id: str, listener: Any) -> bool:
        """Add a WebSocket listener to a channel."""
        pass

    @abstractmethod
    async def remove_listener(self, channel_id: str, listener: Any) -> bool:
        """Remove a WebSocket listener from a channel."""
        pass

    @abstractmethod
    async def get_listeners(self, channel_id: str) -> Set[Any]:
        """Get a copy of the listeners set for broadcasting."""
        pass

    @abstractmethod
    async def set_channel_inactive(self, channel_id: str) -> bool:
        """Mark a channel as inactive."""
        pass

    @abstractmethod
    async def remove_channel(self, channel_id: str) -> bool:
        """Remove a channel from the registry."""
        pass

    # Replace set_channel_inactive with set_channel_active and add get_and_reset_dropped_batches
    @abstractmethod
    async def get_and_reset_dropped_batches(self, channel_id: str) -> int:
        """Fetch and reset the dropped batches counter for a channel."""
        pass

    @abstractmethod
    async def set_channel_active(self, channel_id: str, is_active: bool) -> bool:
        """Set the active status of a channel."""
        pass

    @abstractmethod
    async def add_listener(self, channel_id: str, listener: WSClientSession) -> bool:
        """Add a WebSocket session to a channel."""
        pass

    @abstractmethod
    async def remove_listener(self, channel_id: str, listener: WSClientSession) -> bool:
        """Remove a WebSocket session from a channel."""
        pass

    @abstractmethod
    async def get_listeners(self, channel_id: str) -> Set[WSClientSession]:
        """Get a copy of the sessions set for broadcasting."""
        pass

    @abstractmethod
    async def get_subscribers_by_target(self, channel_id: str, target: str) -> List[WSClientSession]:
        """Get all sessions subscribed to a specific target (e.g., 'lan_hosts')."""
        pass
