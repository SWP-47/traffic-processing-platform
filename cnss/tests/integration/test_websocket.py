import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock, MagicMock
from starlette.websockets import WebSocketDisconnect
from app.store import StateStore as InMemoryStateStore
from app.auth import create_access_token
from app.broadcast import broadcast_telemetry_update
from app.models import WSClientSession


class TestWebSocketTelemetry:
    def _get_token(self, role, scope=None):
        token, _, _ = create_access_token(f"{role}_user", role, scope or [])
        return token

    def test_valid_connection(self, client):
        """Valid connection adds listener and accepts."""
        test_store = InMemoryStateStore()
        # Use asyncio.run for setup to avoid manual loop management/closure issues
        asyncio.run(
            test_store.update_channel_activity("test-ch", 1, datetime.now(timezone.utc))
        )
        token = self._get_token("admin")
        url = f"/api/v1/ws/telemetry?token={token}&channel_id=test-ch"
        
        with patch("app.main.state_store", test_store), patch("app.main.get_all_channel_ids_from_db", new_callable=AsyncMock, return_value=["test-ch"]):
            with client.websocket_connect(url) as websocket:
                assert "test-ch" in test_store._channels
                assert len(test_store._channels["test-ch"].listeners) == 1
                # Verify ping/pong keep-alive works
                websocket.send_text("ping")
                data = websocket.receive_text()
                assert data == "pong"

    def test_missing_token(self, client):
        """Missing token -> 4001 invalid_token."""
        with client.websocket_connect(
            "/api/v1/ws/telemetry?channel_id=test-ch"
        ) as websocket:
            with pytest.raises(WebSocketDisconnect) as excinfo:
                websocket.receive_text()
            assert excinfo.value.code == 4001

    def test_invalid_token(self, client):
        """Invalid token -> 4001 invalid_token."""
        with client.websocket_connect(
            "/api/v1/ws/telemetry?token=badtoken&channel_id=test-ch"
        ) as websocket:
            with pytest.raises(WebSocketDisconnect) as excinfo:
                websocket.receive_text()
            assert excinfo.value.code == 4001

    def test_missing_channel_id(self, client):
        """Missing channel_id -> 4002 missing_channel."""
        token = self._get_token("admin")
        with client.websocket_connect(
            f"/api/v1/ws/telemetry?token={token}"
        ) as websocket:
            with pytest.raises(WebSocketDisconnect) as excinfo:
                websocket.receive_text()
            assert excinfo.value.code == 4002

    def test_viewer_forbidden_scope(self, client):
        """Viewer out of scope -> 4003 channel_forbidden."""
        token = self._get_token("viewer", scope=["other-ch"])
        test_store = InMemoryStateStore()
        asyncio.run(
            test_store.update_channel_activity("test-ch", 1, datetime.now(timezone.utc))
        )
        with patch("app.main.state_store", test_store):
            with client.websocket_connect(
                f"/api/v1/ws/telemetry?token={token}&channel_id=test-ch"
            ) as websocket:
                with pytest.raises(WebSocketDisconnect) as excinfo:
                    websocket.receive_text()
                assert excinfo.value.code == 4003

    def test_channel_not_found(self, client):
        """Channel doesn't exist -> 4004 channel_not_found."""
        token = self._get_token("admin")
        test_store = InMemoryStateStore()
        with patch("app.main.state_store", test_store):
            with client.websocket_connect(
                f"/api/v1/ws/telemetry?token={token}&channel_id=non-existent"
            ) as websocket:
                with pytest.raises(WebSocketDisconnect) as excinfo:
                    websocket.receive_text()
                assert excinfo.value.code == 4004


@pytest.mark.asyncio
async def test_broadcast_to_multiple_listeners():
    """Broadcast pushes to all listeners of the channel only."""
    test_store = InMemoryStateStore()
    await test_store.update_channel_activity("test-ch", 1, datetime.now(timezone.utc))

    mock_ws1 = AsyncMock()
    mock_ws2 = AsyncMock()

    # Wrap mocks in WSClientSession to match the new architecture
    session1 = WSClientSession(
        websocket=mock_ws1, user=MagicMock(), channel_id="test-ch"
    )
    session2 = WSClientSession(
        websocket=mock_ws2, user=MagicMock(), channel_id="test-ch"
    )

    await test_store.add_listener("test-ch", session1)
    await test_store.add_listener("test-ch", session2)

    # No more TelemetryBatch or PacketMetadata needed!
    with patch("app.broadcast.state_store", test_store):
        await broadcast_telemetry_update(
            channel_id="test-ch",
            is_active=True,
            packets_in=1,
            packets_out=1,
            dropped_batches=0,
            received_at=datetime.now(timezone.utc),
            window_sec=3.0,  # Verify the new sliding window parameter
        )

    mock_ws1.send_json.assert_called_once()
    mock_ws2.send_json.assert_called_once()
    sent_payload = mock_ws1.send_json.call_args.args[0]
    # Verify metrics
    assert sent_payload["metrics"]["direction_out"]["packets"] == 1
    assert sent_payload["metrics"]["direction_in"]["packets"] == 1
    # Verify the sliding window was correctly translated to window_ms
    assert sent_payload["window_ms"] == 3000
