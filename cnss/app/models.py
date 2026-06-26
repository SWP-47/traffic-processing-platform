from typing import Any, List, Optional, Set
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Dict, TYPE_CHECKING
import json

if TYPE_CHECKING:
    from fastapi import WebSocket
    from .auth import TokenPayload

class PacketMetadata(BaseModel):
    direction: int  # 0 = IN, 1 = OUT
    src_ip: str  # IPv4/IPv6
    dst_ip: str  # IPv4/IPv6
    src_port: int
    dst_port: int


class TelemetryBatch(BaseModel):
    channel_id: str
    timestamp: int  # Unix epoch seconds (window start)
    sequence: int
    window_ms: int
    packets: List[PacketMetadata]

class WSClientSession:
    """Tracks WebSocket connection, user context, and active subscriptions."""
    def __init__(self, websocket: 'WebSocket', user: 'TokenPayload', channel_id: str):
        self.websocket = websocket
        self.user = user
        self.channel_id = channel_id
        # e.g., {"lan_hosts": {"sort_by": "sent", "limit": 5}}
        self.subscriptions: Dict[str, Dict[str, Any]] = {}

    def __hash__(self):
        return hash(self.websocket)

    def __eq__(self, other):
        if isinstance(other, WSClientSession):
            return self.websocket == other.websocket
        return False

class ChannelState(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    channel_id: str
    is_active: bool = True
    last_activity_timestamp: datetime
    last_sequence: Optional[int] = None
    dropped_batches: int = 0
    listeners: Set[WSClientSession] = Field(default_factory=set, exclude=True)


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

class WSControlMessage(BaseModel):
    action: str
    target: Optional[str] = None
    sort_by: Optional[str] = None
    limit: Optional[int] = 5

class HostEntry(BaseModel):
    ip: str
    sent_per_sec: float
    received_per_sec: float
    last_seen: str

class HostsUpdate(BaseModel):
    type: str = "hosts_update"
    target: str
    channel_id: str
    timestamp: str
    hosts: List[HostEntry]

class HistoryPoint(BaseModel):
    timestamp: str
    packets_in_per_sec: float
    packets_out_per_sec: float
    is_active: bool

class HistoryResponse(BaseModel):
    channel_id: str
    period: str
    interval_sec: int
    points: List[HistoryPoint]