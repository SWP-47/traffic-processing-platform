from typing import Any, List, Optional, Set
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


class DirectionStats(BaseModel):
    packets: int


class TelemetryBatch(BaseModel):
    channel_id: str
    sequence: int
    window_ms: int
    direction_out: DirectionStats
    direction_in: DirectionStats
    timestamp: datetime


class ChannelState(BaseModel):
    # Pydantic V2 syntax for configuration
    model_config = ConfigDict(arbitrary_types_allowed=True)

    channel_id: str
    is_active: bool = True
    last_activity_timestamp: datetime
    last_sequence: Optional[int] = None

    # Transient field: WebSocket listeners are kept in memory only.
    listeners: Set[Any] = Field(default_factory=set, exclude=True)


class LoginRequest(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    issued_at: str  # ISO 8601 format
    role: str
    scope: List[str]
