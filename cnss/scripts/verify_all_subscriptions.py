# ==============================================================================
# CnSS All Subscriptions Verification Script
# ==============================================================================

import asyncio
import json
import os
from typing import Any

import httpx
import websockets

os.environ.pop("HTTP_PROXY", None)
os.environ.pop("HTTPS_PROXY", None)
os.environ.pop("ALL_PROXY", None)
os.environ.pop("http_proxy", None)
os.environ.pop("https_proxy", None)
os.environ.pop("all_proxy", None)

API_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8001"
CHANNEL_ID = "test-channel-01"
HOST_IP = "192.168.1.10"


async def login() -> str:
    async with httpx.AsyncClient(trust_env=False) as client:
        response = await client.post(
            f"{API_URL}/api/v1/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        return str(response.json()["access_token"])


async def run_subscriber(target: str, params: dict[str, Any], token: str, duration: float = 12.0) -> None:
    ws_uri = f"{WS_URL}/ws?token={token}&channel_id={CHANNEL_ID}"
    print(f"[Subscriber: {target}] Connecting to WebSocket...")

    async with websockets.connect(ws_uri) as ws:
        print(f"[Subscriber: {target}] ✓ Connected!")

        sub_msg = {
            "action": "subscribe",
            "id": f"sub-{target}-01",
            "channel_id": CHANNEL_ID,
            "target": target,
            "params": params,
        }
        await ws.send(json.dumps(sub_msg))

        # Read initial snapshot
        snapshot = await ws.recv()
        snapshot_str = snapshot.decode("utf-8") if isinstance(snapshot, bytes) else snapshot
        print(f"[Subscriber: {target}] ✓ Initial Snapshot: {snapshot_str[:160]}...")

        # Read real-time updates for `duration` seconds
        start_time = asyncio.get_event_loop().time()
        update_count = 0
        while asyncio.get_event_loop().time() - start_time < duration:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
                update_count += 1
                msg_str = msg.decode("utf-8") if isinstance(msg, bytes) else msg
                print(f"[Subscriber: {target}] ✓ Update #{update_count} received: {msg_str[:160]}...")
            except asyncio.TimeoutError:
                print(f"[Subscriber: {target}] ⌛ Timeout waiting for update...")

        # Unsubscribe
        unsub_msg = {
            "action": "unsubscribe",
            "id": f"sub-{target}-01",
            "channel_id": CHANNEL_ID,
            "target": target,
            "params": params,
        }
        await ws.send(json.dumps(unsub_msg))
        print(f"[Subscriber: {target}] ✓ Unsubscribed cleanly.")


async def main() -> None:
    token = await login()
    print("✓ Logged in. Token retrieved.")

    # 5 targets
    subscriptions: dict[str, dict[str, Any]] = {
        "telemetry": {"window_sec": 5.0},
        "hosts_table": {
            "period_sec": 300,
            "location": None,
            "ip": None,
            "sort_by": "rx",
            "sort_order": "desc",
            "limit": 10,
            "offset": 0,
        },
        "host_details": {"host_ip": HOST_IP, "period_sec": 300},
        "host_top_destinations": {
            "host_ip": HOST_IP,
            "period_sec": 300,
            "sort_by": "received",
            "sort_order": "desc",
            "limit": 5,
            "offset": 0,
        },
        "host_top_ports": {
            "host_ip": HOST_IP,
            "period_sec": 300,
            "sort_by": "pps",
            "sort_order": "desc",
            "limit": 5,
            "offset": 0,
        },
    }

    # Run all subscribers concurrently
    tasks = [run_subscriber(target, params, token) for target, params in subscriptions.items()]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
