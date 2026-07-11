# ==============================================================================
# CnSS End-to-End System Verification Script
# ==============================================================================

import os
os.environ.pop("HTTP_PROXY", None)
os.environ.pop("HTTPS_PROXY", None)
os.environ.pop("ALL_PROXY", None)
os.environ.pop("http_proxy", None)
os.environ.pop("https_proxy", None)
os.environ.pop("all_proxy", None)

import asyncio
import json
import socket
import time
import httpx
import websockets

API_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8001"
UDP_HOST = "127.0.0.1"
UDP_PORT = 5140
CHANNEL_ID = "test-channel-01"

async def test_api_login():
    print("[1] Logging in to API...")
    async with httpx.AsyncClient(trust_env=False) as client:
        response = await client.post(
            f"{API_URL}/api/v1/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        if response.status_code != 200:
            print(f"❌ Login failed: {response.status_code} - {response.text}")
            return None
        data = response.json()
        print("✓ Login successful!")
        return data["access_token"]

async def test_websocket_and_udp(token: str):
    print("\n[2] Establishing WebSocket connection...")
    ws_uri = f"{WS_URL}/ws?token={token}&channel_id={CHANNEL_ID}"
    
    # Establish WebSocket connection
    async with websockets.connect(ws_uri) as ws:
        print("✓ WebSocket connected!")
        
        # Subscribe to telemetry target
        print("[3] Subscribing to telemetry target...")
        sub_msg = {
            "action": "subscribe",
            "id": "verify-sub-01",
            "channel_id": CHANNEL_ID,
            "target": "telemetry",
            "params": {}
        }
        await ws.send(json.dumps(sub_msg))
        
        # Wait for the initial snapshot response
        snapshot_resp = await ws.recv()
        print(f"✓ Initial Snapshot Received: {snapshot_resp}")
        
        # Send simulated UDP traffic
        print("\n[4] Simulating UDP traffic on port 5140...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Construct and send 3 UDP telemetry packets
        for seq in range(1001, 1004):
            batch = {
                "channel_id": CHANNEL_ID,
                "timestamp": int(time.time()),
                "sequence": seq,
                "window_ms": 1000,
                "packets": [
                    {
                        "direction": 0,
                        "src_ip": "8.8.8.8",
                        "dst_ip": "192.168.1.10",
                        "src_port": 12345,
                        "dst_port": 80,
                        "protocol": "TCP"
                    }
                ]
            }
            data = json.dumps(batch).encode("utf-8")
            sock.sendto(data, (UDP_HOST, UDP_PORT))
            print(f"  Sent UDP batch #{seq}")
            await asyncio.sleep(0.1)
        sock.close()
        
        # Wait and read real-time subscription update messages
        print("\n[5] Waiting for WebSocket real-time subscription updates...")
        for _ in range(3):
            try:
                # Use wait_for to prevent blocking indefinitely if update fails
                msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                print(f"✓ WebSocket Update Received: {msg}")
            except asyncio.TimeoutError:
                print("❌ Timeout waiting for WebSocket updates.")
                break

async def main():
    token = await test_api_login()
    if token:
        await test_websocket_and_udp(token)

if __name__ == "__main__":
    asyncio.run(main())
