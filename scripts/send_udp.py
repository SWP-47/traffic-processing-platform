import socket
import json

# 1. Define the TelemetryBatch payload
payload = {
    "channel_id": "bridge-berlin-01",
    "sequence": 1,
    "window_ms": 500,
    "direction_out": {"packets": 150},
    "direction_in": {"packets": 140},
    "timestamp": "2026-06-17T12:00:00Z"
}

# 2. Configure UDP socket
UDP_IP = "127.0.0.1"
UDP_PORT = 5140

# 3. Send the datagram
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # SOCK_DGRAM = UDP
message = json.dumps(payload).encode('utf-8')
sock.sendto(message, (UDP_IP, UDP_PORT))

print(f"Successfully sent {len(message)} bytes to {UDP_IP}:{UDP_PORT}")
sock.close()