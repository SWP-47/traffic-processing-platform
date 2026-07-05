# ==============================================================================
# CnSS REST API Dependencies
# FastAPI dependency injection functions for authentication, authorization,
# and infrastructure access (Database, Redis).
# ==============================================================================

from typing import Awaitable, Callable

import asyncpg
import redis.asyncio as aioredis
from fastapi import Depends, Path
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.contracts.auth import TokenPayload
from core.database import get_db_pool
from core.redis.client import get_redis_client
from core.security.jwt import check_token_revocation, decode_access_token
from core.security.scopes import verify_channel_access

# --- Security Scheme ---
# FastAPI built-in Bearer token extractor.
# Automatically parses the 'Authorization: Bearer <token>' header.
security_scheme = HTTPBearer()

# --- Infrastructure Dependencies ---


async def get_db() -> asyncpg.Pool:
    """
    Provides the global asyncpg connection pool.
    """
    return get_db_pool()


async def get_redis() -> aioredis.Redis:
    """
    Provides the global Redis client instance.
    """
    return get_redis_client()


# --- Authentication Dependencies ---


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
) -> TokenPayload:
    """
    Extracts, decodes, and validates the JWT from the Authorization header.
    Checks for token revocation in Redis.

    Raises AuthError (401) if the token is invalid, expired, or revoked.
    """
    token = credentials.credentials

    # Decode and verify signature/expiration
    # decode_access_token raises AuthError or TokenExpiredError (subclass of AuthError)
    payload = decode_access_token(token)

    # Check if the token has been revoked (jti in Redis 'jwt:revoked' set)
    # check_token_revocation raises TokenRevokedError (subclass of AuthError)
    await check_token_revocation(payload.jti)

    return payload


# --- Authorization Dependencies ---


def require_channel_access(channel_id_param: str = "channel_id") -> Callable[..., Awaitable[str]]:
    """
    Factory function that returns a dependency to verify channel access.
    Usage: channel_id: str = Depends(require_channel_access("channel_id"))

    Raises AuthorizationError (403) if the user lacks scope permissions.
    """

    async def _verify_access(
        channel_id: str = Path(..., alias=channel_id_param),
        current_user: TokenPayload = Depends(get_current_user),
    ) -> str:
        """
        Verifies that the authenticated user has access to the specified channel.
        """
        # verify_channel_access raises AuthorizationError if access is denied
        verify_channel_access(current_user, channel_id)
        return channel_id

    return _verify_access
