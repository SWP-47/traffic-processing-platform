# ==============================================================================
# CnSS System Health REST API Route
# Provides a comprehensive health check endpoint that verifies the connectivity
# and status of core infrastructure components (TimescaleDB, Redis) and
# aggregates channel statistics for the Management User Interface (MUI).
# ==============================================================================

from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from core.contracts.auth import TokenPayload
from core.database import get_db_pool
from core.exceptions import UnhealthyError
from core.redis.client import get_redis_client
from services.api.deps import get_current_user
from services.api.schemas import HealthResponse

# --- Router Configuration ---
# Grouped under /api/v1 prefix. Tags provide OpenAPI documentation grouping.
router = APIRouter(prefix="/api/v1", tags=["System"])


# ==============================================================================
# GET /api/v1/health
# ==============================================================================
@router.get("/health", response_model=HealthResponse)
async def health_check(
    current_user: TokenPayload = Depends(get_current_user),
) -> HealthResponse:
    """
    Verifies internal component and database connectivity.
    Returns a detailed status of TimescaleDB, Redis, and channel statistics.
    
    Raises UnhealthyError (503) if any core component is unreachable or in an error state.
    """
    components: dict[str, str] = {}
    
    # --- Database Connectivity Check ---
    # Executes a lightweight query to verify the asyncpg connection pool is healthy
    # and TimescaleDB is responsive.
    try:
        db_pool = get_db_pool()
        async with db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1;")
        components["database"] = "active"
    except Exception:
        components["database"] = "error"

    # --- Redis Connectivity Check ---
    # Sends a PING command to verify the ephemeral Redis instance is reachable.
    try:
        redis_client = get_redis_client()
        await redis_client.ping()
        components["redis"] = "active"
    except Exception:
        components["redis"] = "error"

    # --- Channel Statistics Aggregation ---
    # Queries the persistent 'channels' registry to provide the MUI with
    # a quick overview of the monitoring landscape (total vs. active channels).
    channels_active = 0
    channels_total = 0
    try:
        db_pool = get_db_pool()
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT 
                    COUNT(*) AS total, 
                    COUNT(*) FILTER (WHERE is_active = TRUE) AS active 
                FROM channels;
                """
            )
            channels_total = row["total"]
            channels_active = row["active"]
        components["channels"] = "active"
    except Exception:
        components["channels"] = "error"

    # --- Overall Status Evaluation ---
    # If any critical component is in an error state, the entire service is
    # considered unhealthy, and a 503 response is returned.
    if any(status == "error" for status in components.values()):
        raise UnhealthyError(
            message="One or more core components are in an error state."
        )

    # --- Response Formatting ---
    # Construct the final health payload with UTC timestamps for consistency.
    return HealthResponse(
        status="healthy",
        components=components,
        channels_active=channels_active,
        channels_total=channels_total,
        timestamp=datetime.now(timezone.utc),
    )