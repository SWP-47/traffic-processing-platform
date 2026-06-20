import jwt
import time
from datetime import datetime, timezone
from typing import List

from fastapi import Depends, HTTPException, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from .config import settings

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime
import jwt
# MOCK USER STORE & AUTHENTICATION

MOCK_USERS = {
    "admin": {
        "password": "admin123",
        "role": "admin",
        "scope": [],  # Admin scope is dynamically populated at login
    },
    "viewer": {
        "password": "viewer123",
        "role": "viewer",
        "scope": ["bridge-berlin-01", "bridge-prague-01"],
    },
}


def authenticate_user(username: str, password: str) -> dict | None:
    """Validates credentials against the mock store."""
    user = MOCK_USERS.get(username)
    if not user or user["password"] != password:
        return None
    return user


def create_access_token(
    username: str, role: str, scope: list[str]
) -> tuple[str, int, str]:
    """
    Generates an HS256 signed JWT (AC 4 & AC 5).
    Returns: (token_string, expires_in_seconds, issued_at_iso_string)
    """
    now_ts = int(time.time())
    exp_ts = now_ts + settings.jwt_expiration_seconds
    payload = {
        "sub": username,
        "iat": now_ts,
        "exp": exp_ts,
        "role": role,
        "scope": scope,
    }
    token = jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )
    # Format issued_at as ISO 8601
    issued_at_iso = (
        datetime.fromtimestamp(now_ts, tz=timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )
    return token, settings.jwt_expiration_seconds, issued_at_iso


# TOKEN DECODING & FASTAPI DEPENDENCIES


class TokenPayload(BaseModel):
    sub: str
    iat: int
    exp: int
    role: str
    scope: List[str]


def decode_token(token: str) -> TokenPayload:
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        sub = payload.get("sub")
        role = payload.get("role")
        scope = payload.get("scope", [])
        if sub is None or role is None:
            raise jwt.InvalidTokenError("Missing required claims")
        return TokenPayload(
            sub=sub,
            iat=payload.get("iat"),
            exp=payload.get("exp"),
            role=role,
            scope=scope,
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail={"error": "unauthorized", "message": "Invalid or expired token."},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail={"error": "unauthorized", "message": "Invalid or expired token."},
        )


# FastAPI Dependencies
# We set auto_error=False to prevent HTTPBearer from raising a 403 Forbidden
# when the Authorization header is missing. We handle it manually to return 401.
security = HTTPBearer(auto_error=False)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

async def get_current_user(authorization: str = Header(default=None)) -> TokenPayload:
    """
    Validates the JWT token and returns the TokenPayload.
    Enforces AC 1, AC 2.
    """
    # AC 1: Check for missing or malformed Authorization header
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "unauthorized", "message": "Invalid or expired token."}
        )
    
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "unauthorized", "message": "Invalid or expired token."}
        )

    # Decode and Validate Token (AC 2)
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        sub = payload.get("sub")
        role = payload.get("role")
        scope = payload.get("scope", [])
        
        if sub is None or role is None:
            raise jwt.InvalidTokenError("Missing required claims")
            
        return TokenPayload(sub=sub, iat=payload.get("iat"), exp=payload.get("exp"), role=role, scope=scope)
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "unauthorized", "message": "Invalid or expired token."}
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "unauthorized", "message": "Invalid or expired token."}
        )


async def get_ws_user(token: str = Query(...)) -> TokenPayload:
    return decode_token(token)
