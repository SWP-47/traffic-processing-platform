# ==============================================================================
# CnSS JWT Management Module
# Handles encoding and decoding of JSON Web Tokens (HS256) for stateless 
# authentication and authorization across REST and WebSocket services.
# ==============================================================================

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import jwt

from core.config import settings
from core.exceptions import AuthError, TokenExpiredError, TokenRevokedError
from core.contracts.auth import TokenPayload


# --- Token Creation ---

def create_access_token(subject: str, role: str, scope: List[str]) -> str:
    """
    Generates a signed JWT containing user identity, role, and channel scopes.
    Includes a unique 'jti' claim to support immediate token revocation via Redis.
    """
    now = datetime.now(timezone.utc)
    
    # Construct the payload with standard and custom claims required by the architecture
    payload = {
        "sub": subject,
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(hours=settings.jwt_expiration_hours),
        "role": role,
        "scope": scope,
    }
    
    # Encode and sign the token using the configured secret and algorithm
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

# --- Token Verification ---

def decode_access_token(token: str) -> TokenPayload:
    """
    Verifies the signature and expiration of a JWT, returning a typed TokenPayload.
    """
    try:
        raw_payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        # Validate and construct the typed Pydantic model
        return TokenPayload(**raw_payload)
        
    except jwt.ExpiredSignatureError:
        raise TokenExpiredError() from None
        
    except jwt.InvalidTokenError:
        raise AuthError("Invalid or malformed token.") from None

# --- Revocation Check ---

async def check_token_revocation(jti: str) -> None:
    """
    Checks if the provided JWT ID (jti) exists in the Redis revocation set.
    Raises TokenRevokedError if the token has been invalidated by an admin.
    """
    # Importing here to avoid heavy dependencies at the module level 
    # and to keep the crypto part purely synchronous if needed.
    from core.redis.client import get_redis_client
    
    redis_client = get_redis_client()
    
    # SISMEMBER returns 1 if the jti is in the 'jwt:revoked' set, 0 otherwise
    is_revoked = await redis_client.sismember("jwt:revoked", jti)
    
    if is_revoked:
        raise TokenRevokedError()
