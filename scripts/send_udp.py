import socket
import json
import time

# 1. Define the TelemetryBatch payload (MVP v2 schema)
payload = {
    "channel_id": "bridge-berlin-01",
    "sequence": 1,
    "window_ms": 500,
    "timestamp": int(time.time()),  # Unix epoch seconds (integer)
    "packets": [
        {
            "direction": 1,  # 1 = OUT
            "src_ip": "192.168.1.100",
            "dst_ip": "8.8.8.8",
            "src_port": 12345,
            "dst_port": 53
        },
        {
            "direction": 0,  # 0 = IN
            "src_ip": "8.8.8.8",
            "dst_ip": "192.168.1.100",
            "src_port": 53,
            "dst_port": 12345
        },
        {
            "direction": 1,  # 1 = OUT
            "src_ip": "192.168.1.100",
            "dst_ip": "1.1.1.1",
            "src_port": 54321,
            "dst_port": 443
        }
    ]
}

# Example: Generate 50 random packets for a heavier load test
import random

packets = []
for _ in range(random.randint(10, 50)):
    packets.append({
        "direction": random.choice([0, 1]),
        "src_ip": f"192.168.1.{random.randint(1, 254)}",
        "dst_ip": f"8.8.{random.randint(0, 255)}.{random.randint(1, 254)}",
        "src_port": random.randint(1024, 65535),
        "dst_port": random.choice([53, 80, 443])
    })

payload["packets"] = packets

# 2. Configure UDP socket
UDP_IP = "10.93.26.186"
UDP_PORT = 5140

# 3. Send the datagram
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # SOCK_DGRAM = UDP
message = json.dumps(payload).encode('utf-8')
sock.sendto(message, (UDP_IP, UDP_PORT))

print(f"Successfully sent {len(message)} bytes to {UDP_IP}:{UDP_PORT}")
sock.close()