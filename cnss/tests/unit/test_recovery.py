import pytest
import asyncio
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch
from app.store.memory import InMemoryStateStore
from app.udp_server import TelemetryUDPProtocol


@pytest.fixture
def store():
    return InMemoryStateStore()


@pytest.mark.asyncio
async def test_recovery_on_new_udp_state(store):
    """
    Given a channel receives UDP telemetry after being marked inactive,
        When the batch is processed, Then is_active is set back to true.
    """
    now = datetime.now(timezone.utc)

    # 1. Setup inactive channel
    await store.update_channel_activity("ch-recover", 1, now - timedelta(seconds=10))
    await store.set_channel_inactive("ch-recover")

    ch = await store.get_channel("ch-recover")
    assert ch.is_active is False

    # 2. Simulate new UDP batch processing
    await store.update_channel_activity("ch-recover", 2, now)

    ch = await store.get_channel("ch-recover")
    assert ch.is_active is True, "Channel should be active after new UDP"
    assert ch.last_sequence == 2


@pytest.mark.asyncio
async def test_recovery_broadcasts_to_listeners():
    protocol = TelemetryUDPProtocol()
    protocol.transport = AsyncMock()

    valid_batch = {
        "channel_id": "ch-recover-broadcast",
        "sequence": 2,
        "window_ms": 500,
        "timestamp": int(datetime.now(timezone.utc).timestamp()),
        "packets": [
            {
                "direction": 1,
                "src_ip": "192.168.1.100",
                "dst_ip": "8.8.8.8",
                "src_port": 12345,
                "dst_port": 53,
            }
        ],
    }
    data = json.dumps(valid_batch).encode("utf-8")

    with patch("app.udp_server.state_store") as mock_store, \
         patch("app.udp_server.insert_packet_flows", new_callable=AsyncMock), \
         patch("app.udp_server.broadcast_telemetry_update", new_callable=AsyncMock) as mock_broadcast:

        mock_store.update_channel_activity = AsyncMock(return_value=0)
        mock_store.get_listeners = AsyncMock(return_value={AsyncMock()})

        protocol.datagram_received(data, ("127.0.0.1", 12345))
        await asyncio.sleep(0.01)

        mock_broadcast.assert_called_once()
        args, kwargs = mock_broadcast.call_args
        channel_id = args[0] if args else kwargs.get("channel_id")
        assert channel_id == "ch-recover-broadcast"
        assert kwargs.get("is_active") is True