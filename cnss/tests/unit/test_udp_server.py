import pytest
import json
import logging
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from app.udp_server import TelemetryUDPProtocol
from datetime import datetime, timezone


@pytest.fixture
def protocol():
    proto = TelemetryUDPProtocol()
    proto.transport = MagicMock()
    return proto


def create_valid_payload(channel_id="test-ch", sequence=1):
    batch = {
        "channel_id": channel_id,
        "sequence": sequence,
        "window_ms": 500,
        "direction_out": {"packets": 10},
        "direction_in": {"packets": 10},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return json.dumps(batch).encode("utf-8")


# --- AC 5: Malformed JSON / Invalid UTF-8 ---
def test_ac5_invalid_utf8(protocol, caplog):
    invalid_data = b"\xff\xfe\xfd"
    with caplog.at_level(logging.ERROR):
        protocol.datagram_received(invalid_data, ("127.0.0.1", 12345))
    assert "invalid UTF-8" in caplog.text


def test_ac5_malformed_json(protocol, caplog):
    bad_json = b'{"channel_id": "test", "sequence":'
    with caplog.at_level(logging.ERROR):
        protocol.datagram_received(bad_json, ("127.0.0.1", 12345))
    assert "Invalid payload" in caplog.text


def test_ac5_invalid_schema(protocol, caplog):
    # Valid JSON, but missing required Pydantic fields
    incomplete_json = b'{"channel_id": "test"}'
    with caplog.at_level(logging.ERROR):
        protocol.datagram_received(incomplete_json, ("127.0.0.1", 12345))
    assert "Invalid payload" in caplog.text


# --- AC 1: UDP Parsing & State Delegation ---
@pytest.mark.asyncio
async def test_ac1_udp_to_state_integration(protocol):
    valid_data = create_valid_payload(channel_id="udp-int-test", sequence=42)

    # Mock the global state_store to verify it gets called correctly
    with patch("app.udp_server.state_store") as mock_store:
        mock_store.update_channel_activity = AsyncMock(return_value=0)
        mock_store.get_listeners = AsyncMock(return_value=set())

        protocol.datagram_received(valid_data, ("127.0.0.1", 12345))

        # Allow asyncio.create_task to execute
        await asyncio.sleep(0.01)

        mock_store.update_channel_activity.assert_called_once()
        args, kwargs = mock_store.update_channel_activity.call_args
        assert kwargs["channel_id"] == "udp-int-test"
        assert kwargs["incoming_sequence"] == 42
