# ==============================================================================
# CnSS Authentication REST API Routes
# Handles user login, token refresh, and logout operations.
# Implements JWT-based stateless authentication with HttpOnly refresh tokens
# stored in browser cookies to mitigate XSS attacks (Architecture §5.3).
# ==============================================================================

from datetime import datetime, timezone

from fastapi import APIRouter, Cookie, Response

from core.config import settings
from core.contracts.auth import RefreshTokenPayload
from core.db import (
    db_fetch_user_by_username,
    db_fetch_user_scopes,
    db_fetch_all_channels,
)
from core.exceptions import AuthError, InvalidCredentialsError
from core.redis.client import get_redis_client
from core.security.jwt import (
    check_token_revocation,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)
from core.security.passwords import verify_password
from services.api.schemas import (
    LoginRequest,
    LogoutResponse,
    RefreshTokenResponse,
    TokenResponse,
)

# --- Router Configuration ---
# All auth endpoints are grouped under /api/v1/auth prefix.
# Tags provide OpenAPI documentation grouping in Swagger UI.
router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

# --- Cookie Configuration Constants ---
# These values MUST match the API specification (api.md §3.1) for secure cookie handling.
# The cookie name is shared across login, refresh, and logout endpoints.
REFRESH_TOKEN_COOKIE_NAME = "refresh_token"

# Refresh token lifetime: 7 days in seconds (matches JWT refresh token 'exp' claim).
# This is intentionally longer than the access token (24h) to enable silent renewal.
REFRESH_TOKEN_MAX_AGE = 7 * 24 * 60 * 60

# Restrict cookie transmission to the refresh endpoint path only (defense in depth).
# This prevents the cookie from being sent to other API endpoints unnecessarily,
# reducing the attack surface for CSRF and token leakage.
REFRESH_TOKEN_PATH = "/api/v1/auth/refresh"


# ==============================================================================
# POST /api/v1/auth/login
# ==============================================================================
@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    response: Response,
) -> TokenResponse:
    """
    Authenticates a user with username/password and issues a JWT access token.
    Sets a long-lived refresh token as an HttpOnly cookie for session management.

    Raises InvalidCredentialsError (401) if username or password is incorrect.
    The error message is intentionally generic to prevent user enumeration.
    """
    # --- Step 1: Fetch user by username ---
    # Query only the fields needed for authentication to minimize data transfer.
    user_row = await db_fetch_user_by_username(request.username)

    # User not found — raise invalid credentials (do not reveal account existence).
    if user_row is None:
        raise InvalidCredentialsError()

    # --- Step 2: Verify password against Argon2id hash ---
    # verify_password uses constant-time comparison to prevent timing attacks.
    if not verify_password(request.password, user_row["password_hash"]):
        raise InvalidCredentialsError()

    user_id = str(user_row["id"])
    role = user_row["role"]

    # --- Step 3: Fetch channel scopes for viewer role ---
    # Admins bypass scope restrictions entirely (Architecture §5.1).
    # Their scope list remains empty, and verify_channel_access() grants unrestricted access.
    scope: list[str] = []
    if role == "viewer":
        scope = await db_fetch_user_scopes(user_row["id"])
    elif role == "admin":
        # Fetch all registered channels for admin
        scope = await db_fetch_all_channels()

    # --- Step 4: Generate JWT tokens ---
    # Access token: short-lived (24h), stored in MUI memory (Architecture §5.3).
    # Refresh token: long-lived (7d), stored in HttpOnly cookie (Architecture §5.3).
    access_token = create_access_token(subject=user_id, role=role, scope=scope)
    refresh_token = create_refresh_token(subject=user_id, role=role, scope=scope)

    # --- Step 5: Set refresh token as HttpOnly cookie ---
    # Security flags:
    #   - httponly=True: Prevents JavaScript access (XSS mitigation).
    #   - secure=True: Ensures transmission only over HTTPS (Architecture §5.3).
    #   - samesite="strict": Prevents CSRF attacks by blocking cross-site requests.
    #   - path: Restricted to /api/v1/auth/refresh (defense in depth).
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        path=REFRESH_TOKEN_PATH,
        max_age=REFRESH_TOKEN_MAX_AGE,
    )

    # --- Step 6: Build and return response ---
    # issued_at uses UTC timezone to ensure consistent ISO 8601 formatting.
    now = datetime.now(timezone.utc)
    return TokenResponse(
        access_token=access_token,
        token_type="Bearer",
        expires_in=settings.jwt_expiration_hours * 3600,
        issued_at=now,
        role=role,
        scope=scope,
    )


# ==============================================================================
# POST /api/v1/auth/refresh
# ==============================================================================
@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh(
    refresh_token: str | None = Cookie(default=None),
) -> RefreshTokenResponse:
    """
    Issues a new short-lived access token using the HttpOnly refresh token cookie.
    Validates the refresh token signature, expiration, type claim, and revocation status.

    Raises AuthError (401) if the refresh token is missing, invalid, expired, or revoked.
    """
    # --- Step 1: Validate cookie presence ---
    # Absence of the cookie indicates no active session or prior logout.
    if not refresh_token:
        raise AuthError(message="Refresh token is missing, invalid, expired, or revoked.")

    # --- Step 2: Decode and validate the refresh token ---
    # decode_refresh_token performs:
    #   - HS256 signature verification using the configured secret key.
    #   - Expiration ('exp' claim) check.
    #   - Type claim validation (must be "refresh" to prevent access token misuse).
    # Raises AuthError or TokenExpiredError on any validation failure.
    payload: RefreshTokenPayload = decode_refresh_token(refresh_token)

    # --- Step 3: Check revocation status in Redis ---
    # Verifies that the token's jti (JWT ID) is NOT in the 'jwt:revoked' set.
    # Raises TokenRevokedError (subclass of AuthError) if the token was invalidated
    # by a previous logout operation (Architecture §5.3 Revocation Flow).
    await check_token_revocation(payload.jti)

    # --- Step 4: Issue new access token ---
    # Reuse identity (sub), role, and scope from the refresh token payload
    # to avoid an additional database query. The refresh token acts as a
    # secure, server-signed credential that vouches for the user's identity.
    new_access_token = create_access_token(
        subject=payload.sub,
        role=payload.role,
        scope=payload.scope,
    )

    # --- Step 5: Build and return response ---
    now = datetime.now(timezone.utc)
    return RefreshTokenResponse(
        access_token=new_access_token,
        token_type="Bearer",
        expires_in=settings.jwt_expiration_hours * 3600,
        issued_at=now,
    )


# ==============================================================================
# POST /api/v1/auth/logout
# ==============================================================================
@router.post("/logout", response_model=LogoutResponse)
async def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
) -> LogoutResponse:
    """
    Invalidates the current session by revoking the refresh token in Redis
    and clearing the HttpOnly cookie from the client.

    This endpoint is idempotent: it succeeds even if no refresh token is present,
    if the token is malformed, or if it has already been revoked. This ensures
    the client always receives a clean logout state regardless of edge cases.
    """
    # --- Step 1: Revoke the refresh token if present ---
    if refresh_token:
        try:
            # Decode without expiration verification to allow revoking expired tokens.
            # This ensures that even if the token's 'exp' has passed, its jti is still
            # added to the revocation set for audit consistency and to prevent reuse
            # in edge cases where the client clock is out of sync.
            payload = decode_refresh_token(refresh_token, verify_exp=False)

            # Add jti to the Redis revocation set ('jwt:revoked').
            # SADD is idempotent — adding an already-revoked jti is a no-op.
            redis_client = get_redis_client()
            await redis_client.sadd("jwt:revoked", payload.jti)
        except Exception:
            # If decoding fails (malformed token, invalid signature, wrong type),
            # we still proceed to clear the cookie. This ensures the client
            # always receives a clean logout response and cookie removal.
            pass

    # --- Step 2: Clear the refresh token cookie ---
    # delete_cookie sets max_age=0 and expires=0, instructing the browser
    # to immediately discard the cookie. The same security flags (httponly,
    # secure, samesite, path) must match the original set_cookie call
    # to ensure the browser correctly identifies and removes the cookie.
    response.delete_cookie(
        key=REFRESH_TOKEN_COOKIE_NAME,
        path=REFRESH_TOKEN_PATH,
        httponly=True,
        secure=True,
        samesite="strict",
    )

    return LogoutResponse()
