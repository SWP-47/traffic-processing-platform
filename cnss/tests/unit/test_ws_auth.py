# ==============================================================================
# CnSS WebSocket Authentication Unit Tests
# Validates JWT extraction, token revocation checks, and scope enforcement
# against the architectural specifications defined in architecture.md §2.3.1.
# ==============================================================================

from unittest.mock import MagicMock, patch

import pytest
from websockets.legacy.server import WebSocketServerProtocol

from core.contracts.auth import TokenPayload
from core.exceptions import AuthError, AuthorizationError, TokenRevokedError
from services.websocket.auth import MissingChannelError, authenticate_connection

# --- Test Fixtures ---


@pytest.fixture
def mock_websocket():
    """
    Provides a mocked WebSocketServerProtocol with a configurable path.
    IMPORTANT: Use spec=WebSocketServerProtocol to ensure hasattr() works correctly.
    In legacy websockets, WebSocketServerProtocol does NOT have a 'request' attribute,
    so hasattr(websocket, "request") returns False, and auth.py uses websocket.path.
    """
    ws = MagicMock(spec=WebSocketServerProtocol)
    ws.path = "/api/v1/ws/telemetry?token=valid_token&channel_id=bridge-01"
    return ws


@pytest.fixture
def mock_payload():
    """Provides a valid TokenPayload for testing."""
    return TokenPayload(
        sub="user-123",
        jti="jti-456",
        iat=1700000000,
        exp=1800000000,
        role="viewer",
        scope=["bridge-01", "bridge-02"],
    )


# --- Successful Authentication Tests ---


async def test_authenticate_connection_success_viewer(mock_websocket, mock_payload):
    """
    Architecture §2.3.1: Successful authentication for a viewer with valid scope.
    """
    with (
        patch("services.websocket.auth.decode_access_token", return_value=mock_payload),
        patch("services.websocket.auth.check_token_revocation") as mock_revoke,
        patch("services.websocket.auth.verify_channel_access") as mock_scope,
    ):

        payload, channel_id = await authenticate_connection(mock_websocket)

        assert payload == mock_payload
        assert channel_id == "bridge-01"
        mock_revoke.assert_awaited_once_with("jti-456")
        # verify_channel_access is called synchronously in auth.py
        mock_scope.assert_called_once_with(mock_payload, "bridge-01")


async def test_authenticate_connection_success_admin(mock_websocket):
    """
    Architecture §2.3.1: Admin role bypasses scope restrictions.
    """
    admin_payload = TokenPayload(
        sub="admin-123",
        jti="jti-admin",
        iat=1700000000,
        exp=1800000000,
        role="admin",
        scope=[],
    )

    with (
        patch("services.websocket.auth.decode_access_token", return_value=admin_payload),
        patch("services.websocket.auth.check_token_revocation"),
        patch("services.websocket.auth.verify_channel_access") as mock_scope,
    ):

        payload, channel_id = await authenticate_connection(mock_websocket)

        assert payload.role == "admin"
        assert channel_id == "bridge-01"
        # verify_channel_access is still called, but internally it bypasses for admin
        mock_scope.assert_called_once_with(admin_payload, "bridge-01")


# --- Failure Scenarios (Close Codes) ---


async def test_missing_channel_id_returns_4002():
    """
    Architecture §2.3.1: Absence of channel_id results in close code 4002.
    """
    ws = MagicMock(spec=WebSocketServerProtocol)
    ws.path = "/api/v1/ws/telemetry?token=valid_token"

    with pytest.raises(MissingChannelError) as exc_info:
        await authenticate_connection(ws)

    assert exc_info.value.ws_close_code == 4002


async def test_missing_token_returns_4001():
    """
    Architecture §2.3.1: Absence of token results in close code 4001.
    """
    ws = MagicMock(spec=WebSocketServerProtocol)
    ws.path = "/api/v1/ws/telemetry?channel_id=bridge-01"

    with pytest.raises(AuthError) as exc_info:
        await authenticate_connection(ws)

    assert exc_info.value.ws_close_code == 4001


async def test_invalid_or_expired_token_returns_4001(mock_websocket):
    """
    Architecture §2.3.1: Invalid or expired JWT results in close code 4001.
    """
    with patch("services.websocket.auth.decode_access_token", side_effect=AuthError("Expired")):
        with pytest.raises(AuthError) as exc_info:
            await authenticate_connection(mock_websocket)

        assert exc_info.value.ws_close_code == 4001


async def test_revoked_token_returns_4001(mock_websocket, mock_payload):
    """
    Architecture §2.3.1: Token found in 'jwt:revoked' set results in close code 4001.
    """
    with (
        patch("services.websocket.auth.decode_access_token", return_value=mock_payload),
        patch("services.websocket.auth.check_token_revocation", side_effect=TokenRevokedError()),
    ):

        with pytest.raises(TokenRevokedError) as exc_info:
            await authenticate_connection(mock_websocket)

        assert exc_info.value.ws_close_code == 4001


async def test_insufficient_scope_returns_4003(mock_websocket, mock_payload):
    """
    Architecture §2.3.1: Viewer lacking scope for the channel results in close code 4003.
    """
    with (
        patch("services.websocket.auth.decode_access_token", return_value=mock_payload),
        patch("services.websocket.auth.check_token_revocation"),
        patch("services.websocket.auth.verify_channel_access", side_effect=AuthorizationError()),
    ):

        with pytest.raises(AuthorizationError) as exc_info:
            await authenticate_connection(mock_websocket)

        assert exc_info.value.ws_close_code == 4003
