# ==============================================================================
# CnSS Database Pool Manager
# Manages the asynchronous connection pool for TimescaleDB using asyncpg.
# Provides initialization, retrieval, and teardown of the global connection pool.
# ==============================================================================

import asyncpg

from core.config import settings

from core.exceptions import DatabaseError

# --- Global Pool State ---
# Holds the single instance of the asyncpg connection pool across the application lifecycle.
_db_pool: asyncpg.Pool | None = None


# --- Pool Lifecycle Management ---

async def init_db_pool() -> asyncpg.Pool:
    """
    Initializes the global asyncpg connection pool.
    Must be called during application startup (e.g., FastAPI lifespan).
    """
    global _db_pool
    
    # Return existing pool if already initialized to prevent duplicate connections
    if _db_pool is not None:
        return _db_pool
    
    # asyncpg requires a standard PostgreSQL DSN. 
    # Strip the SQLAlchemy-specific '+asyncpg' driver prefix if present in the config.
    dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    
    # Create the connection pool with optimized settings for high-throughput telemetry ingestion
    _db_pool = await asyncpg.create_pool(
        dsn=dsn,
        min_size=2,
        max_size=20,
        command_timeout=60,
    )
    
    return _db_pool


async def close_db_pool() -> None:
    """
    Closes the global asyncpg connection pool gracefully.
    Must be called during application shutdown to release database resources.
    """
    global _db_pool
    
    if _db_pool is not None:
        await _db_pool.close()
        _db_pool = None


def get_db_pool() -> asyncpg.Pool:
    """
    Retrieves the initialized global connection pool.
    Raises RuntimeError if the pool has not been initialized yet.
    """
    if _db_pool is None:
        raise DatabaseError("Database pool is not initialized. Call init_db_pool() first.")
    
    return _db_pool