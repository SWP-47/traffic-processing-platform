# send_udp.py
import socket
import json
import time

UDP_IP = "10.93.26.186"
UDP_PORT = 5140
CHANNEL_ID = "test-bridge-0"

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def send_batch(seq, i):
    payload = {
        "channel_id": CHANNEL_ID + f"{i}",
        "sequence": seq,
        "window_ms": 1000,
        "direction_out": {"packets": 150},
        "direction_in": {"packets": 140},
        "timestamp": "2026-06-20T12:00:00Z"
    }
    sock.sendto(json.dumps(payload).encode('utf-8'), (UDP_IP, UDP_PORT))
    print(f"Sent sequence {seq}")

# Отправляем 3 пакета с интервалом в 1 секунду
for i in range(1, 4):
    send_batch(i, i)
    time.sleep(1)

print("UDP sending stopped. Watch the logs and WebSocket!")