# ==============================================================================
# CnSS REST API Pydantic Schemas
# Defines the request and response models for the REST API endpoints.
# Ensures strict validation and consistent JSON serialization across
# authentication, channel discovery, health checks, and historical data retrieval.
# ==============================================================================
from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# --- Authentication Schemas ---
# Models for login, token refresh, and logout operations.
class LoginRequest(BaseModel):
    """
    Request payload for user authentication.
    """

    username: str = Field(..., min_length=1, max_length=50, description="Unique username for authentication.")
    password: str = Field(..., min_length=1, description="Plaintext password for verification.")


class TokenResponse(BaseModel):
    """
    Response payload containing the issued JWT access token and metadata.
    """

    access_token: str = Field(..., description="Signed JWT access token.")
    token_type: str = Field(default="Bearer", description="Token type identifier.")
    expires_in: int = Field(..., description="Token lifetime in seconds.")
    issued_at: datetime = Field(..., description="ISO 8601 timestamp of token issuance.")
    role: Literal["admin", "viewer"] = Field(..., description="User role for authorization.")
    scope: List[str] = Field(default_factory=list, description="List of accessible channel IDs.")


class RefreshTokenResponse(BaseModel):
    """
    Response payload for a successful token refresh operation.
    """

    access_token: str = Field(..., description="New signed JWT access token.")
    token_type: str = Field(default="Bearer", description="Token type identifier.")
    expires_in: int = Field(..., description="Token lifetime in seconds.")
    issued_at: datetime = Field(..., description="ISO 8601 timestamp of token issuance.")


class LogoutResponse(BaseModel):
    """
    Response payload confirming successful session termination.
    """

    message: str = Field(default="Successfully logged out.", description="Human-readable success message.")


# --- System Health & Discovery Schemas ---
# Models for health checks and channel registry discovery.
class HealthResponse(BaseModel):
    """
    Response payload for the system health check endpoint.
    """

    status: Literal["healthy", "unhealthy"] = Field(..., description="Overall system health status.")
    components: Dict[str, str] = Field(..., description="Status of individual internal components.")
    channels_active: int = Field(..., description="Number of currently active channels.")
    channels_total: int = Field(..., description="Total number of registered channels.")
    timestamp: datetime = Field(..., description="ISO 8601 timestamp of the health check.")


class ChannelStatus(BaseModel):
    """
    Represents the current state of a single monitored channel.
    """

    channel_id: str = Field(..., description="Unique identifier of the channel.")
    is_active: bool = Field(..., description="Indicates if the channel is currently receiving traffic.")
    last_activity_timestamp: Optional[datetime] = Field(
        None, description="ISO 8601 timestamp of the last received telemetry batch."
    )


class ChannelsListResponse(BaseModel):
    """
    Response payload containing a filtered list of accessible channels.
    """

    channels: List[ChannelStatus] = Field(..., description="Array of channel status objects.")
    total: int = Field(..., description="Total number of channels returned.")


# --- Historical Data Schemas ---
# Models for lazy-loading time-series data for line charts.
class HistoryPoint(BaseModel):
    """
    A single aggregated data point in a time-series history response.
    """

    timestamp: datetime = Field(..., description="ISO 8601 timestamp of the data point.")
    packets_in_per_sec: float = Field(..., description="Aggregated incoming packet rate.")
    packets_out_per_sec: float = Field(..., description="Aggregated outgoing packet rate.")
    is_active: Optional[bool] = Field(
        None, description="Channel activity status at this specific timestamp (Channel History only)."
    )


class ChannelHistoryResponse(BaseModel):
    """
    Response payload for channel-level historical telemetry data.
    """

    channel_id: str = Field(..., description="Identifier of the queried channel.")
    # Replaced string Enum 'period' with numeric 'period_sec' for arbitrary time windows
    period_sec: int = Field(..., description="Requested period duration in seconds.")
    start_time: datetime = Field(..., description="Actual start of the returned time range.")
    end_time: datetime = Field(..., description="Actual end of the returned time range.")
    interval_sec: int = Field(..., description="Calculated time bucket size in seconds.")
    points: List[HistoryPoint] = Field(..., description="Array of aggregated data points.")


class HostHistoryPoint(BaseModel):
    """
    A single aggregated data point for a specific host's history.
    """

    timestamp: datetime = Field(..., description="ISO 8601 timestamp of the data point.")
    packets_in_per_sec: float = Field(..., description="Aggregated incoming packet rate for the host.")
    packets_out_per_sec: float = Field(..., description="Aggregated outgoing packet rate for the host.")


class HostHistoryResponse(BaseModel):
    """
    Response payload for host-level historical Rx/Tx rate data.
    """

    channel_id: str = Field(..., description="Identifier of the queried channel.")
    host_ip: str = Field(..., description="IP address of the queried host.")
    # Replaced string Enum 'period' with numeric 'period_sec' for arbitrary time windows
    period_sec: int = Field(..., description="Requested period duration in seconds.")
    start_time: datetime = Field(..., description="Actual start of the returned time range.")
    end_time: datetime = Field(..., description="Actual end of the returned time range.")
    interval_sec: int = Field(..., description="Calculated time bucket size in seconds.")
    points: List[HostHistoryPoint] = Field(..., description="Array of aggregated data points.")


# --- Error Response Schema ---
# Standardized error format for all REST API failures.
class ErrorResponse(BaseModel):
    """
    Standardized JSON error response structure.
    Maps directly to the CnSS custom exception hierarchy in core.exceptions.
    """

    error: str = Field(..., description="Machine-readable error code (e.g., 'unauthorized', 'not_found').")
    message: str = Field(..., description="Human-readable description of the error.")
