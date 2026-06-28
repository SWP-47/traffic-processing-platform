import pytest
import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock

from app.udp_server import start_udp_server
from app.store import StateStore as InMemoryStateStore


@pytest.mark.asyncio
async def test_udp_socket_receives_and_updates_state():
    test_store = InMemoryStateStore()

    with patch("app.udp_server.state_store", test_store), patch(
        "app.udp_server.insert_packet_flows", new_callable=AsyncMock
    ) as mock_db:

        transport = await start_udp_server(host="127.0.0.1", port=0)
        port = transport.get_extra_info("sockname")[1]
        try:
            loop = asyncio.get_running_loop()
            client_transport, _ = await loop.create_datagram_endpoint(
                asyncio.DatagramProtocol, remote_addr=("127.0.0.1", port)
            )

            batch = {
                "channel_id": "integration-test-ch",
                "sequence": 100,
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
            client_transport.sendto(json.dumps(batch).encode("utf-8"))
            await asyncio.sleep(0.1)

            channel = await test_store.get_channel("integration-test-ch")
            assert channel is not None
            assert channel.last_sequence == 100

            # Verify DB insert was attempted with correct data
            mock_db.assert_called_once()
            assert mock_db.call_args.kwargs["channel_id"] == "integration-test-ch"
            assert len(mock_db.call_args.kwargs["packets"]) == 2

            client_transport.close()
        finally:
            transport.close()
