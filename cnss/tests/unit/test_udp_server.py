import pytest
import json
import logging
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone
from app.udp_server import TelemetryUDPProtocol


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
        "timestamp": int(datetime.now(timezone.utc).timestamp()),
        "packets": [
            {
                "direction": 1,
                "src_ip": "192.168.1.100",
                "dst_ip": "8.8.8.8",
                "src_port": 12345,
                "dst_port": 53,
            },
            {
                "direction": 0,
                "src_ip": "8.8.8.8",
                "dst_ip": "192.168.1.100",
                "src_port": 53,
                "dst_port": 12345,
            },
        ],
    }
    return json.dumps(batch).encode("utf-8")


# Malformed JSON / Invalid UTF-8
def test_invalid_utf8(protocol, caplog):
    invalid_data = b"\xff\xfe\xfd"
    with caplog.at_level(logging.ERROR):
        protocol.datagram_received(invalid_data, ("127.0.0.1", 12345))
    assert "Invalid UTF-8" in caplog.text


def test_malformed_json(protocol, caplog):
    bad_json = b'{"channel_id": "test", "sequence":'
    with caplog.at_level(logging.ERROR):
        protocol.datagram_received(bad_json, ("127.0.0.1", 12345))
    assert "Invalid payload" in caplog.text


def test_invalid_schema(protocol, caplog):
    incomplete_json = b'{"channel_id": "test"}'
    with caplog.at_level(logging.ERROR):
        protocol.datagram_received(incomplete_json, ("127.0.0.1", 12345))
    assert "Invalid payload" in caplog.text


# Full pipeline
@pytest.mark.asyncio
async def test_udp_to_state_integration(protocol):
    valid_data = create_valid_payload(channel_id="udp-int-test", sequence=42)

    with patch("app.udp_server.state_store") as mock_store, \
         patch("app.udp_server.insert_packet_flows", new_callable=AsyncMock) as mock_db:

        mock_store.update_channel_activity = AsyncMock(return_value=0)
        mock_store.get_listeners = AsyncMock(return_value=set())

        protocol.datagram_received(valid_data, ("127.0.0.1", 12345))
        await asyncio.sleep(0.01)

        # sequence tracked in memory
        mock_store.update_channel_activity.assert_called_once()
        kwargs = mock_store.update_channel_activity.call_args.kwargs
        assert kwargs["channel_id"] == "udp-int-test"
        assert kwargs["incoming_sequence"] == 42

        # DB insert invoked
        mock_db.assert_called_once()
        call_kwargs = mock_db.call_args.kwargs
        assert call_kwargs["channel_id"] == "udp-int-test"
        assert len(call_kwargs["packets"]) == 2


# DB failure does not crash
@pytest.mark.asyncio
async def test_db_failure_graceful(protocol, caplog):
    valid_data = create_valid_payload(channel_id="db-fail-test", sequence=7)

    async def failing_insert(*args, **kwargs):
        raise RuntimeError("connection refused")

    with patch("app.udp_server.state_store") as mock_store, \
         patch("app.udp_server.insert_packet_flows", side_effect=failing_insert):

        mock_store.update_channel_activity = AsyncMock(return_value=0)
        mock_store.get_listeners = AsyncMock(return_value=set())

        with caplog.at_level(logging.ERROR):
            protocol.datagram_received(valid_data, ("127.0.0.1", 12345))
            await asyncio.sleep(0.01)

        # Error was logged
        assert "Database insert failed" in caplog.text
        # State was still updated
        mock_store.update_channel_activity.assert_called_once()