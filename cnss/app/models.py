from typing import Any, List, Optional, Set
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

class PacketMetadata(BaseModel):
    direction: int      # 0 = IN, 1 = OUT
    src_ip: str         # IPv4/IPv6
    dst_ip: str         # IPv4/IPv6
    src_port: int
    dst_port: int


class TelemetryBatch(BaseModel):
    channel_id: str
    timestamp: int          # Unix epoch seconds (window start)
    sequence: int
    window_ms: int
    packets: List[PacketMetadata]

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
