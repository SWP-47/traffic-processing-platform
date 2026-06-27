import pytest
import json
from unittest.mock import patch, AsyncMock
from app.store.memory import InMemoryStateStore
from app.auth import create_access_token
from datetime import datetime, timezone


class TestWebSocketHosts:
    def _get_token(self, role="admin"):
        token, _, _ = create_access_token(f"{role}_user", role, [])
        return token

    @pytest.mark.asyncio
    async def test_subscribe_sends_initial_snapshot(self, client):
        """Subscribing updates session memory and immediately triggers an Initial Snapshot."""
        test_store = InMemoryStateStore()
        await test_store.update_channel_activity(
            "test-ch", 1, datetime.now(timezone.utc)
        )

        token = self._get_token()
        url = f"/api/v1/ws/telemetry?token={token}&channel_id=test-ch"

        mock_hosts = [
            {
                "ip": "192.168.1.1",
                "sent_per_sec": 10.0,
                "received_per_sec": 5.0,
                "last_seen": "2026-06-17T12:00:00Z",
            }
        ]

        with patch("app.main.state_store", test_store), patch(
            "app.main.get_top_hosts", new_callable=AsyncMock, return_value=mock_hosts
        ):

            with client.websocket_connect(url) as websocket:
                # Send subscribe message
                sub_msg = {
                    "action": "subscribe",
                    "target": "lan_hosts",
                    "sort_by": "sent",
                    "limit": 5,
                }
                websocket.send_text(json.dumps(sub_msg))

                # Receive initial snapshot
                data = websocket.receive_json()
                assert data["type"] == "hosts_update"
                assert data["target"] == "lan_hosts"
                assert data["channel_id"] == "test-ch"
                assert len(data["hosts"]) == 1
                assert data["hosts"][0]["ip"] == "192.168.1.1"

                # Verify session was updated in store
                listeners = await test_store.get_listeners("test-ch")
                assert len(listeners) == 1
                session = list(listeners)[0]
                assert "lan_hosts" in session.subscriptions
                assert session.subscriptions["lan_hosts"]["sort_by"] == "sent"
                assert session.subscriptions["lan_hosts"]["limit"] == 5

    @pytest.mark.asyncio
    async def test_unsubscribe_removes_from_session(self, client):
        """Unsubscribing removes the target from the session's memory."""
        test_store = InMemoryStateStore()
        await test_store.update_channel_activity(
            "test-ch", 1, datetime.now(timezone.utc)
        )
        token = self._get_token()
        url = f"/api/v1/ws/telemetry?token={token}&channel_id=test-ch"
        with patch("app.main.state_store", test_store), patch(
            "app.main.get_top_hosts", new_callable=AsyncMock, return_value=[]
        ):
            with client.websocket_connect(url) as websocket:
                # Subscribe first
                websocket.send_text(
                    json.dumps(
                        {
                            "action": "subscribe",
                            "target": "wan_hosts",
                            "sort_by": "received",
                            "limit": 3,
                        }
                    )
                )
                websocket.receive_json()  # consume initial snapshot

                # Unsubscribe
                websocket.send_text(
                    json.dumps({"action": "unsubscribe", "target": "wan_hosts"})
                )

                # Sending a ping and waiting for a pong ensures the server has
                # fully processed the preceding 'unsubscribe' message.
                websocket.send_text("ping")
                assert websocket.receive_text() == "pong"
                # ---------------------------------------------------------

                # Verify session was updated in store
                listeners = await test_store.get_listeners("test-ch")
                session = list(listeners)[0]
                assert "wan_hosts" not in session.subscriptions

    @pytest.mark.asyncio
    async def test_invalid_control_message_does_not_crash(self, client):
        """Malformed control messages are logged but keep the connection alive."""
        test_store = InMemoryStateStore()
        await test_store.update_channel_activity(
            "test-ch", 1, datetime.now(timezone.utc)
        )

        token = self._get_token()
        url = f"/api/v1/ws/telemetry?token={token}&channel_id=test-ch"

        with patch("app.main.state_store", test_store):
            with client.websocket_connect(url) as websocket:
                # Send invalid JSON
                websocket.send_text("not a json")
                # Send valid JSON but missing required fields for Pydantic
                websocket.send_text(json.dumps({"action": "subscribe"}))

                # Connection should still be alive, test with ping/pong
                websocket.send_text("ping")
                assert websocket.receive_text() == "pong"
