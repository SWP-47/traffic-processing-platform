# ==============================================================================
# CnSS WebSocket Server Unit Tests
# Validates server lifecycle, connection handling, message routing, and
# heartbeat loop against architectural specifications (architecture.md §2.3).
# ==============================================================================

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from core.contracts.auth import TokenPayload
from core.contracts.subscriptions import SubscribeRequest
from core.exceptions import AuthorizationError, ClientResponseError, ResourceNotFoundError
from services.websocket.auth import MissingChannelError
from services.websocket.server import WebSocketServer


# --- Test Fixtures ---

@pytest.fixture
def mock_register_connection():
    """Provides a mock for the register_connection callback."""
    return MagicMock()


@pytest.fixture
def mock_unregister_connection():
    """Provides a mock for the unregister_connection callback."""
    return MagicMock()


@pytest.fixture
def server(mock_register_connection, mock_unregister_connection):
    """Provides a WebSocketServer instance with mocked callbacks and dependencies."""
    # Mock the internal components that call get_redis_client() in their __init__
    with patch("services.websocket.server.SubscriptionManager") as mock_sub_cls, \
         patch("services.websocket.server.GarbageCollector") as mock_gc_cls, \
         patch("services.websocket.server.SnapshotFetcher") as mock_snapshot_cls:
        
        # Configure mock instances
        mock_sub_instance = AsyncMock()
        mock_sub_instance.subscribe = AsyncMock(return_value=("hash-abc", "ws:push:hash-abc"))
        mock_sub_instance.unsubscribe = AsyncMock(return_value="hash-abc")
        mock_sub_cls.return_value = mock_sub_instance
        
        mock_gc_instance = AsyncMock()
        mock_gc_instance.cleanup = AsyncMock()
        mock_gc_cls.return_value = mock_gc_instance
        
        mock_snapshot_instance = AsyncMock()
        mock_snapshot_instance.fetch_snapshot = AsyncMock(return_value={"data": "snapshot"})
        mock_snapshot_cls.return_value = mock_snapshot_instance
        
        ws_server = WebSocketServer(
            register_connection=mock_register_connection,
            unregister_connection=mock_unregister_connection,
        )
        
        yield ws_server


@pytest.fixture
def mock_websocket():
    """Provides a mocked WebSocket connection."""
    ws = AsyncMock()
    ws.close = AsyncMock()
    ws.send = AsyncMock()
    return ws


@pytest.fixture
def mock_session_instance():
    """Provides a mocked Session instance."""
    session = AsyncMock()
    session.client_id = "client-uuid-123"
    session.channel_id = "bridge-01"
    session.create = AsyncMock()
    session.destroy = AsyncMock()
    session.refresh_ttl = AsyncMock()
    session.add_subscription = AsyncMock()
    session.remove_subscription = AsyncMock()
    return session


@pytest.fixture
def mock_payload():
    """Provides a valid TokenPayload for testing."""
    return TokenPayload(
        sub="user-123",
        jti="jti-456",
        iat=1700000000,
        exp=1800000000,
        role="viewer",
        scope=["bridge-01"],
    )


# --- Message Handling Tests ---

class TestMessageHandling:
    """Tests for the _process_message method."""

    async def test_handle_message_subscribe(
        self, server, mock_websocket, mock_session_instance
    ):
        """
        Architecture §2.3.3: Subscribe messages must be routed to SubscriptionManager.
        """
        # Prepare subscribe message
        subscribe_msg = {
            "action": "subscribe",
            "id": "sub-123",
            "channel_id": "bridge-01",
            "target": "telemetry",
            "params": {},
        }
        
        await server._process_message(mock_websocket, mock_session_instance, json.dumps(subscribe_msg))
        
        # Verify subscribe was called with correct request
        server._sub_manager.subscribe.assert_awaited_once()
        call_args = server._sub_manager.subscribe.call_args[0]
        assert call_args[0] == mock_session_instance
        assert isinstance(call_args[1], SubscribeRequest)
        assert call_args[1].action == "subscribe"
        assert call_args[1].id == "sub-123"

    async def test_handle_message_unsubscribe(
        self, server, mock_websocket, mock_session_instance
    ):
        """
        Architecture §2.3.4: Unsubscribe messages must be routed to SubscriptionManager.
        """
        # Prepare unsubscribe message (must include all required fields for SubscribeRequest)
        unsubscribe_msg = {
            "action": "unsubscribe",
            "id": "sub-123",
            "channel_id": "bridge-01",
            "target": "telemetry",
            "params": {},
        }
        
        await server._process_message(mock_websocket, mock_session_instance, json.dumps(unsubscribe_msg))
        
        # Verify unsubscribe was called with correct request
        server._sub_manager.unsubscribe.assert_awaited_once()
        call_args = server._sub_manager.unsubscribe.call_args[0]
        assert call_args[0] == mock_session_instance
        assert isinstance(call_args[1], SubscribeRequest)
        assert call_args[1].action == "unsubscribe"
        assert call_args[1].id == "sub-123"

    async def test_handle_message_unknown_action(
        self, server, mock_websocket, mock_session_instance
    ):
        """
        Verify that unknown action types are logged but do not crash the handler.
        """
        unknown_msg = {
            "action": "unknown_action",
            "id": "sub-123",
            "channel_id": "bridge-01",
            "target": "telemetry",
            "params": {},
        }
        
        # Should not raise exception
        await server._process_message(mock_websocket, mock_session_instance, json.dumps(unknown_msg))
        
        # Verify neither subscribe nor unsubscribe was called
        server._sub_manager.subscribe.assert_not_awaited()
        server._sub_manager.unsubscribe.assert_not_awaited()

    async def test_handle_message_malformed_json(
        self, server, mock_websocket, mock_session_instance
    ):
        """
        Verify that malformed JSON messages are logged but do not crash the handler.
        """
        malformed_msg = "not a json object"
        
        # Should not raise exception
        await server._process_message(mock_websocket, mock_session_instance, malformed_msg)

    async def test_handle_message_channel_mismatch(
        self, server, mock_websocket, mock_session_instance
    ):
        """
        Architecture §2.3.8: If channel_id in message differs from connection URL,
        the connection must be closed with code 4003.
        """
        # Message with different channel_id than session.channel_id
        mismatch_msg = {
            "action": "subscribe",
            "id": "sub-123",
            "channel_id": "different-channel",  # Differs from session.channel_id
            "target": "telemetry",
            "params": {},
        }
        
        await server._process_message(mock_websocket, mock_session_instance, json.dumps(mismatch_msg))
        
        # Verify connection was closed with 4003
        mock_websocket.close.assert_awaited_once_with(4003, "Subscription channel_id mismatch.")

# --- Heartbeat Loop Tests ---

class TestHeartbeatLoop:
    """Tests for the _heartbeat_loop method."""

    async def test_heartbeat_loop_refreshes_ttl_periodically(self, server, mock_session_instance):
        """
        Architecture §2.3.7: The heartbeat loop must refresh the session TTL
        periodically to prevent premature expiration.
        """
        # Use interval=0 to make the loop run instantly without patching asyncio.sleep
        heartbeat_task = asyncio.create_task(
            server._heartbeat_loop(mock_session_instance, interval=0)
        )

        # Yield control multiple times to let the task execute several iterations
        for _ in range(5):
            await asyncio.sleep(0)

        # Cancel the task
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass

        # Verify refresh_ttl was called at least once
        assert mock_session_instance.refresh_ttl.await_count >= 1

    async def test_heartbeat_loop_handles_refresh_error(self, server, mock_session_instance):
        """
        Verify that heartbeat loop continues running even if refresh_ttl fails.
        """
        # Mock refresh_ttl to raise an exception
        mock_session_instance.refresh_ttl.side_effect = Exception("Redis error")

        # Use interval=0 to make the loop run instantly
        heartbeat_task = asyncio.create_task(
            server._heartbeat_loop(mock_session_instance, interval=0)
        )

        # Yield control multiple times to let the task execute several iterations
        for _ in range(5):
            await asyncio.sleep(0)

        # Cancel the task
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass

        # Verify the loop continued despite errors (refresh_ttl was called multiple times)
        assert mock_session_instance.refresh_ttl.await_count >= 1

# --- Channel Existence Check Tests ---

class TestChannelExistence:
    """Tests for the _check_channel_exists method."""

    async def test_check_channel_exists_true(self, server):
        """
        Verify that _check_channel_exists returns True when channel exists.
        """
        # Mock the database pool
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value={"channel_id": "bridge-01"})
        mock_pool.acquire = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_conn), __aexit__=AsyncMock()))
        
        with patch("services.websocket.server.get_db_pool", return_value=mock_pool):
            result = await server._check_channel_exists("bridge-01")
            assert result is True

    async def test_check_channel_exists_false(self, server):
        """
        Verify that _check_channel_exists returns False when channel does not exist.
        """
        # Mock the database pool
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)
        mock_pool.acquire = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_conn), __aexit__=AsyncMock()))
        
        with patch("services.websocket.server.get_db_pool", return_value=mock_pool):
            result = await server._check_channel_exists("nonexistent-channel")
            assert result is False