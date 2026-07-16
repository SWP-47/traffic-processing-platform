#!/usr/bin/env python3
# ==============================================================================
# CnSS UDP Traffic Simulator with Sinusoidal Load
# Generates realistic UDP telemetry batches with varying packet counts
# following a sinusoidal pattern (period: 10s, interval: 50ms).
# Simulates network traffic fluctuations for testing the full pipeline.
# ==============================================================================

import json
import math
import random
import socket
import time
from typing import Any, Dict

# --- Configuration ---
TARGET_HOST = "127.0.0.1"
TARGET_PORT = 5140
CHANNEL_ID = "test-channel-01"

# Sinusoidal load parameters
BASE_PACKETS = 10  # Baseline packet count
AMPLITUDE = 10  # Amplitude of sine wave (±10 packets)
PERIOD_SEC = 10.0  # Full sine wave period (10 seconds)
SEND_INTERVAL_SEC = 0.05  # Send interval (50ms = 20 batches/sec)

# IP pool for random generation
LAN_IP_POOL = ["192.168.1.10", "192.168.1.20", "192.168.1.30", "10.0.0.1", "10.0.0.2"]
WAN_IP_POOL = ["8.8.8.8", "1.1.1.1", "172.217.0.1", "151.101.1.140", "93.184.216.34"]

# Protocol pool with weights for realistic distribution
# TCP and UDP dominate real traffic, ICMP is rare
PROTOCOL_POOL = ["TCP", "TCP", "TCP", "TCP", "TCP", "UDP", "UDP", "UDP", "ICMP"]


def create_packet_meta(direction: int = 0) -> Dict[str, Any]:
    # Гарантируем, что IP LAN и WAN не будут пересекаться
    if direction == 0:  # IN: WAN -> LAN
        src_ip = random.choice(WAN_IP_POOL)
        dst_ip = random.choice(LAN_IP_POOL)
    else:  # OUT: LAN -> WAN
        src_ip = random.choice(LAN_IP_POOL)
        dst_ip = random.choice(WAN_IP_POOL)

    src_port = random.randint(1024, 65535)
    dst_port = random.choice([53, 80, 443, 123, 514, 8080, 3306])

    # Randomly select protocol with weighted distribution
    protocol = random.choice(PROTOCOL_POOL)

    return {
        "direction": direction,
        "src_ip": src_ip,
        "dst_ip": dst_ip,
        "src_port": src_port,
        "dst_port": dst_port,
        "protocol": protocol,
        "size": random.randint(60, 1200)
    }


def calculate_sinusoidal_packets(elapsed_time: float) -> int:
    """
    Calculates packet count using a sinusoidal function.
    Formula: BASE + AMPLITUDE * sin(2π * t / PERIOD)
    Result is clamped to [0, BASE + AMPLITUDE] to prevent negative values.
    """
    sine_value = math.sin(2 * math.pi * elapsed_time / PERIOD_SEC)
    packets = int(BASE_PACKETS + AMPLITUDE * sine_value)
    # Clamp to non-negative range
    return max(0, packets)


def create_telemetry_batch(
    channel_id: str,
    sequence: int,
    packets_count: int,
    timestamp: int | None = None,
) -> Dict[str, Any]:
    """
    Constructs a TelemetryBatch payload matching the UDP contract.
    """
    if timestamp is None:
        timestamp = int(time.time())

    packets = [create_packet_meta(i % 2) for i in range(packets_count)]

    return {
        "channel_id": channel_id,
        "timestamp": timestamp,
        "sequence": sequence,
        "window_ms": 1000,
        "packets": packets,
    }


def send_udp_packet(sock: socket.socket, payload: Dict[str, Any]) -> int:
    """
    Serializes and sends a UDP packet. Returns the packet size in bytes.
    """
    data = json.dumps(payload).encode("utf-8")
    sock.sendto(data, (TARGET_HOST, TARGET_PORT))
    return len(data)


def main() -> None:
    """
    Main simulation loop. Sends UDP batches every 50ms with sinusoidal load.
    Prints real-time statistics to the console.
    """
    print("=" * 70)
    print("CnSS UDP Traffic Simulator (Sinusoidal Load)")
    print(f"Target: {TARGET_HOST}:{TARGET_PORT}")
    print(f"Channel: {CHANNEL_ID}")
    print(f"Load Pattern: sin(2π * t / {PERIOD_SEC}s), base={BASE_PACKETS}, amp={AMPLITUDE}")
    print(f"Send Interval: {SEND_INTERVAL_SEC * 1000:.0f}ms")
    print("=" * 70)
    print("Press Ctrl+C to stop.\n")

    # Create UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sequence = 1000
    start_time = time.time()
    batch_count = 0
    total_packets = 0

    try:
        while True:
            # Calculate elapsed time for sinusoidal function
            elapsed = time.time() - start_time

            # Calculate packet count using sine wave
            packets_count = calculate_sinusoidal_packets(elapsed)

            # Create and send batch
            batch = create_telemetry_batch(CHANNEL_ID, sequence, packets_count)
            packet_size = send_udp_packet(sock, batch)

            # Update counters
            batch_count += 1
            total_packets += packets_count
            sequence += 1

            # Print progress every second (20 batches)
            if batch_count % 20 == 0:
                sine_phase = (elapsed % PERIOD_SEC) / PERIOD_SEC
                print(
                    f"[{elapsed:6.1f}s] Phase: {sine_phase:.2f} | "
                    f"Packets: {packets_count:2d} | "
                    f"Batch #{batch_count:4d} | "
                    f"Total: {total_packets:6d} pkts | "
                    f"Size: {packet_size:4d}B"
                )

            # Wait for next interval
            time.sleep(SEND_INTERVAL_SEC)

    except KeyboardInterrupt:
        print("\n\n" + "=" * 70)
        print("Simulation stopped by user.")
        print(f"Total batches sent: {batch_count}")
        print(f"Total packets simulated: {total_packets}")
        print(f"Duration: {time.time() - start_time:.1f}s")
        print("=" * 70)

    finally:
        sock.close()


if __name__ == "__main__":
    main()
