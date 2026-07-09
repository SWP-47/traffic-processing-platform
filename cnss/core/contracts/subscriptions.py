# ==============================================================================
# CnSS WebSocket Subscription Contracts
# Pydantic models for validating incoming WebSocket subscription requests
# and generating deterministic query hashes for Redis deduplication.
# ==============================================================================

import hashlib
import json
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field, computed_field


# --- Standalone Hash Function ---
# Pure function to compute the deterministic hash. Kept separate to allow
# usage outside of model instances if needed (e.g., in tests or utilities).
def compute_query_hash(channel_id: str, target: str, params: Dict[str, Any]) -> str:
    """
    Computes a deterministic SHA-256 hash (truncated to 16 chars) for a subscription.
    Used to deduplicate identical requests from multiple users in Redis.
    """
    # Normalize the dictionary to ensure consistent JSON serialization
    normalized = {"channel_id": channel_id, "target": target, "params": params}
    raw = json.dumps(normalized, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


# --- Subscription Parameters Model ---
# Flexible container for subscription-specific filters and settings.
# Uses extra="allow" to support varying parameters across different targets
class SubscriptionParams(BaseModel):
    """
    Dynamic parameters for a subscription query.
    Allows arbitrary fields to accommodate different subscription targets.
    """

    # Allow any additional fields to be passed through without validation errors
    model_config = {"extra": "allow"}

    # --- Common Sorting & Pagination ---
    sort_by: Optional[str] = Field(default=None, description="Column name to sort results by.")
    sort_order: Optional[Literal["asc", "desc"]] = Field(default=None, description="Sort direction (ASC or DESC).")
    limit: Optional[int] = Field(default=None, ge=1, description="Maximum number of records to return (Page size).")
    offset: Optional[int] = Field(default=None, ge=0, description="Pagination offset.")

    # --- Telemetry Specific ---
    window_sec: Optional[float] = Field(default=None, ge=1.0, description="Aggregation time window in seconds.")

    # --- Hosts Table & Details Specific ---
    period: Optional[Literal["5m", "15m", "1h", "24h", "7d", "30d"]] = Field(
        default=None, description="Duration of the time window for aggregation."
    )
    location: Optional[Literal["LAN", "WAN"]] = Field(
        default=None, description="Filter by network location (LAN or WAN)."
    )

    # --- IP Filtering ---
    ip: Optional[str] = Field(default=None, description="Exact IP address match filter.")
    ip_subnet: Optional[str] = Field(default=None, description="Target IP subnet filter (e.g., '192.168.1.0/24').")

    # --- Host Specific Details ---
    host_ip: Optional[str] = Field(default=None, description="IP address of the specific host.")


# --- Subscription Request Model ---
# Represents the full JSON control message sent by the MUI client over WebSocket.
class SubscribeRequest(BaseModel):
    """
    Incoming WebSocket subscription control message.
    Validates the structure and generates a deterministic hash for Redis caching.
    """

    # Action type: supports both subscribe and unsubscribe lifecycle events
    action: Literal["subscribe", "unsubscribe"] = Field(..., description="Control action to perform.")

    # Client-generated unique identifier
    id: str

    # Target channel identifier (must match the JWT scope and connection URL)
    channel_id: str = Field(..., min_length=1, description="Identifier of the channel to subscribe to.")

    # Data target type (e.g., 'telemetry', 'hosts_table', 'host_details')
    target: str = Field(..., min_length=1, description="Type of data stream to subscribe to.")

    # Dynamic query parameters
    params: SubscriptionParams = Field(default_factory=SubscriptionParams, description="Filter and sorting parameters.")

    # --- Query Hash Property ---
    # Wraps the standalone hash function to provide a convenient property
    # that automatically serializes the Pydantic model into a dictionary.
    @computed_field  # type: ignore[prop-decorator]
    @property
    def query_hash(self) -> str:
        """
        Computes a deterministic hash for this subscription.
        Used to deduplicate identical requests from multiple users.
        """
        # Exclude None values to ensure consistent hashing regardless of omitted optional fields
        params_dict = self.params.model_dump(exclude={"id"})
        return compute_query_hash(channel_id=self.channel_id, target=self.target, params=params_dict)
