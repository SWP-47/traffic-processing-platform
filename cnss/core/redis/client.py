# ==============================================================================
# CnSS Redis Client Manager
# Manages the asynchronous Redis connection using redis.asyncio.
# Handles automatic loading of Lua scripts for atomic operations.
# ==============================================================================

from pathlib import Path
from typing import Any

import redis.asyncio as aioredis
from redis.exceptions import RedisError as RedisDriverError

from core.config import settings
from core.exceptions import RedisError

# --- Global Client State ---
# Holds the single instance of the Redis client across the application lifecycle.
_redis_client: aioredis.Redis | None = None

# --- Lua Script Management ---
# Dictionary to hold registered Lua scripts for atomic execution.
# Scripts are loaded into Redis upon client initialization to save roundtrips.
_lua_scripts: dict[str, Any] = {}

# Path to the Lua scripts directory, resolved relative to this file's location.
# This ensures the path is correct regardless of the current working directory.
LUA_SCRIPTS_DIR = Path(__file__).parent / "lua"


# --- Client Lifecycle Management ---


async def init_redis_client() -> aioredis.Redis:
    """
    Initializes the global Redis client and loads Lua scripts.
    Must be called during application startup (e.g., FastAPI lifespan).
    """
    global _redis_client

    # Return existing client if already initialized to prevent duplicate connections
    if _redis_client is not None:
        return _redis_client

    try:
        # Create the async Redis client from the configured URL
        # decode_responses=True ensures strings are returned instead of bytes
        _redis_client = aioredis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)

        # Verify connection to ensure Redis is reachable before proceeding
        await _redis_client.ping()

        # Load Lua scripts into the client for atomic execution
        await _load_lua_scripts()

        return _redis_client
    except RedisDriverError as e:
        raise RedisError(f"Failed to connect to Redis at {settings.redis_url}") from e
    except Exception as e:
        raise RedisError(f"Unexpected error during Redis initialization: {str(e)}") from e


async def _load_lua_scripts() -> None:
    """
    Scans the Lua scripts directory and registers all .lua files with the Redis client.
    This pre-compiles the scripts on the Redis server for faster execution.
    New scripts can be added simply by placing a .lua file in the directory.
    """
    if _redis_client is None:
        return

    # Ensure the scripts directory exists before attempting to scan it
    if not LUA_SCRIPTS_DIR.exists():
        # Directory missing is not a fatal error; just means no scripts are loaded
        return

    # Iterate over all .lua files in the scripts directory
    for lua_file in LUA_SCRIPTS_DIR.glob("*.lua"):
        # Use the filename without extension as the script identifier
        script_name = lua_file.stem

        try:
            # Read the Lua script content from the file system
            lua_content = lua_file.read_text(encoding="utf-8")

            # Register the script with the Redis client for atomic execution
            _lua_scripts[script_name] = _redis_client.register_script(lua_content)
        except RedisDriverError as e:
            raise RedisError(f"Failed to register Lua script '{script_name}'") from e


def get_redis_client() -> aioredis.Redis:
    """
    Retrieves the initialized global Redis client.
    Raises RedisError if the client has not been initialized yet.
    """
    if _redis_client is None:
        raise RedisError("Redis client is not initialized. Call init_redis_client() first.")

    return _redis_client


def get_lua_script(name: str) -> Any:
    """
    Retrieves a registered Lua script by its name (filename without .lua extension).
    Raises RedisError if the script is not found.
    """
    if name not in _lua_scripts:
        raise RedisError(f"Lua script '{name}' is not registered.")

    return _lua_scripts[name]


async def close_redis_client() -> None:
    """
    Closes the global Redis client gracefully.
    Must be called during application shutdown to release resources.
    """
    global _redis_client

    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
        _lua_scripts.clear()
