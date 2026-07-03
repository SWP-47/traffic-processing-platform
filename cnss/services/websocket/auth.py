# ==============================================================================
# CnSS WebSocket Authentication Module
# Handles the extraction and validation of JWT tokens and channel identifiers
# from incoming WebSocket upgrade requests. Enforces the connection lifecycle
# security checks as defined in Architecture Section 2.3.1.
# ==============================================================================

import logging
import urllib.parse
from typing import Tuple

from websockets.legacy.server import WebSocketServerProtocol

from core.contracts.auth import TokenPayload
from core.exceptions import (
    AuthError,
    AuthorizationError,
    ClientResponseError,
)
from core.security.jwt import check_token_revocation, decode_access_token
from core.security.scopes import verify_channel_access

# --- Module Logger ---
logger = logging.getLogger(__name__)


# --- Missing Channel Exception ---
# Specific exception for the 4002 WebSocket close code.
# Raised when the required channel_id query parameter is absent from the URL.
class MissingChannelError(ClientResponseError):
    """Raised when the channel_id query parameter is missing from the connection URL."""

    def __init__(self, message: str = "Missing 'channel_id' in connection URL."):
        super().__init__(
            status_code=400,
            error_code="missing_channel",
            message=message,
            ws_close_code=4002,
        )


# --- Query Parameter Extraction ---
def _parse_query_params(websocket) -> dict[str, str]:
    """
    Extracts and parses the query parameters from the WebSocket upgrade request URL.
    """
    # In websockets >= 13.0, the new API groups HTTP request details under `.request`.
    # We use hasattr for backward compatibility with the legacy API if needed.
    path = websocket.request.path if hasattr(websocket, "request") else websocket.path
    
    # e.g., "/ws?token=eyJ...&channel_id=bridge-01"
    parsed = urllib.parse.urlparse(path)
    query_params = urllib.parse.parse_qs(parsed.query)
    # parse_qs returns lists for each key; flatten to single string values
    return {k: v[0] for k, v in query_params.items()}


# --- Main Authentication Function ---
async def authenticate_connection(
    websocket: WebSocketServerProtocol,
) -> Tuple[TokenPayload, str]:
    """
    Performs the full authentication and authorization sequence for a new
    WebSocket connection. This is the single entry point called by the
    WebSocket server during the connection lifecycle.

    Steps:
    1. Extract and validate channel_id presence (4002 on failure).
    2. Extract and validate JWT token presence (4001 on failure).
    3. Decode and verify JWT signature/expiry (4001 on failure).
    4. Check token revocation status in Redis (4001 on failure).
    5. Verify channel scope against JWT claims (4003 on failure).

    :param websocket: The WebSocket connection protocol instance.
    :return: A tuple of (validated TokenPayload, channel_id string).
    :raises ClientResponseError: With appropriate ws_close_code on any failure.
    """
    # --- Step 1: Extract Query Parameters ---
    params = _parse_query_params(websocket)
    logger.debug(f"Connection attempt with query parameters: {list(params.keys())}")

    # --- Step 2: Validate Channel ID Presence ---
    # Architecture §2.3.1: channel_id must be present in the connection URL.
    # Absence results in close code 4002 (missing_channel).
    channel_id = params.get("channel_id")
    if not channel_id:
        logger.warning("WebSocket connection rejected: missing 'channel_id' parameter.")
        raise MissingChannelError()

    # --- Step 3: Validate Token Presence ---
    # Architecture §2.3.1: JWT must be provided for authentication.
    # Absence results in close code 4001 (invalid_token).
    token = params.get("token")
    if not token:
        logger.warning(
            f"WebSocket connection rejected for channel '{channel_id}': missing 'token' parameter."
        )
        raise AuthError(message="Missing 'token' in connection URL.")

    # --- Step 4: Decode and Verify JWT ---
    # Validates signature, expiration, and structure.
    # Raises TokenExpiredError or AuthError on failure (both map to 4001).
    try:
        payload = decode_access_token(token)
    except AuthError:
        logger.warning(
            f"WebSocket connection rejected for channel '{channel_id}': invalid or expired token."
        )
        raise

    # --- Step 5: Check Token Revocation ---
    # Architecture §2.3.1: Check jti against Redis 'jwt:revoked' set.
    # Raises TokenRevokedError if the token has been invalidated (maps to 4001).
    try:
        await check_token_revocation(payload.jti)
    except AuthError:
        logger.warning(
            f"WebSocket connection rejected for channel '{channel_id}': "
            f"token jti='{payload.jti}' has been revoked."
        )
        raise

    # --- Step 6: Verify Channel Scope ---
    # Architecture §2.3.1 & §5.1: Verify the user has access to this channel.
    # Admins bypass scope checks; viewers must have channel_id in their scope.
    # Raises AuthorizationError if access is denied (maps to 4003).
    try:
        verify_channel_access(payload, channel_id)
    except AuthorizationError:
        logger.warning(
            f"WebSocket connection rejected: user '{payload.sub}' (role={payload.role}) "
            f"lacks access to channel '{channel_id}'."
        )
        raise

    # --- Authentication Successful ---
    logger.info(
        f"WebSocket connection authenticated: user='{payload.sub}', "
        f"role={payload.role}, channel='{channel_id}'."
    )
    return payload, channel_id