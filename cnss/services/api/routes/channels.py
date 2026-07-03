# ==============================================================================
# CnSS Channel Discovery & Status REST API Routes
# Handles channel listing and individual channel status retrieval.
# Reads directly from the persistent 'channels' table in TimescaleDB
# to provide instant, zero-latency status checks as per Architecture §2.4.
# ==============================================================================

from typing import List

from fastapi import APIRouter, Depends

from core.contracts.auth import TokenPayload
from core.database import get_db_pool
from core.exceptions import ResourceNotFoundError
from core.security.scopes import verify_channel_access
from services.api.deps import get_current_user
from services.api.schemas import ChannelStatus, ChannelsListResponse

# --- Router Configuration ---
# Grouped under /api/v1 prefix. Tags provide OpenAPI documentation grouping.
router = APIRouter(prefix="/api/v1", tags=["Channels"])


# ==============================================================================
# GET /api/v1/channels
# ==============================================================================
@router.get("/channels", response_model=ChannelsListResponse)
async def list_channels(
    current_user: TokenPayload = Depends(get_current_user),
) -> ChannelsListResponse:
    """
    Lists all channels accessible to the authenticated user.
    Admins see all registered channels. Viewers are strictly filtered by their JWT scope.
    """
    db_pool = get_db_pool()
    
    # --- Query Construction ---
    # Admins bypass scope restrictions and can view all channels.
    # Viewers are limited to the channel IDs explicitly granted in their scope.
    if current_user.role == "admin":
        query = "SELECT channel_id, is_active, last_activity_at FROM channels"
        params: List = []
    else:
        # Viewers must have at least one channel in their scope to see anything.
        # If scope is empty, return an empty list immediately to avoid invalid SQL.
        if not current_user.scope:
            return ChannelsListResponse(channels=[], total=0)
        
        query = """
            SELECT channel_id, is_active, last_activity_at 
            FROM channels 
            WHERE channel_id = ANY($1)
        """
        params = [current_user.scope]

    # --- Database Execution ---
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(query, *params)

    # --- Response Formatting ---
    # Map database rows to Pydantic models.
    # 'last_activity_at' from DB is mapped to 'last_activity_timestamp' in schema.
    channels = [
        ChannelStatus(
            channel_id=row["channel_id"],
            is_active=row["is_active"],
            last_activity_timestamp=row["last_activity_at"],
        )
        for row in rows
    ]

    return ChannelsListResponse(channels=channels, total=len(channels))


# ==============================================================================
# GET /api/v1/channel/{channel_id}/status
# ==============================================================================
@router.get("/channel/{channel_id}/status", response_model=ChannelStatus)
async def get_channel_status(
    channel_id: str,
    current_user: TokenPayload = Depends(get_current_user),
) -> ChannelStatus:
    """
    Retrieves the current status of a specific channel.
    Acts as a REST fallback for the WebSocket real-time status indicator.
    
    Raises AuthorizationError (403) if the user lacks scope permissions.
    Raises ResourceNotFoundError (404) if the channel does not exist.
    """
    # --- Authorization Check ---
    # Verify that the authenticated user has access to this specific channel.
    # Raises AuthorizationError if the viewer's scope does not include this channel_id.
    verify_channel_access(current_user, channel_id)

    # --- Database Query ---
    db_pool = get_db_pool()
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT channel_id, is_active, last_activity_at 
            FROM channels 
            WHERE channel_id = $1
            """,
            channel_id,
        )

    # --- Existence Validation ---
    # If the channel is not found in the persistent registry, return 404.
    if row is None:
        raise ResourceNotFoundError(message=f"Channel '{channel_id}' not found.")

    # --- Response Formatting ---
    return ChannelStatus(
        channel_id=row["channel_id"],
        is_active=row["is_active"],
        last_activity_timestamp=row["last_activity_at"],
    )