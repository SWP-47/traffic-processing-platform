import pytest
import asyncio
import json
from datetime import datetime, timezone
from app.udp_server import start_udp_server
from app.store.memory import InMemoryStateStore
from unittest.mock import patch


@pytest.mark.asyncio
async def test_udp_socket_receives_and_updates_state():
    # Setup a temporary, isolated in-memory store for this test
    test_store = InMemoryStateStore()

    # Patch the global store used by the UDP server
    with patch("app.udp_server.state_store", test_store):
        # Start UDP server on port 0 (OS assigns a random available port)
        transport = await start_udp_server(host="127.0.0.1", port=0)
        port = transport.get_extra_info("sockname")[1]

        try:
            # Create a UDP client socket to send data
            loop = asyncio.get_running_loop()
            client_transport, _ = await loop.create_datagram_endpoint(
                asyncio.DatagramProtocol, remote_addr=("127.0.0.1", port)
            )

            # Construct and send a valid TelemetryBatch
            batch = {
                "channel_id": "integration-test-ch",
                "sequence": 100,
                "window_ms": 500,
                "direction_out": {"packets": 50},
                "direction_in": {"packets": 40},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            data = json.dumps(batch).encode("utf-8")
            client_transport.sendto(data)

            # Wait briefly for the server's event loop to process the datagram
            await asyncio.sleep(0.1)

            # Verify the state was successfully updated
            channel = await test_store.get_channel("integration-test-ch")
            assert channel is not None
            assert channel.last_sequence == 100
            assert channel.is_active is True

            client_transport.close()
        finally:
            transport.close()
