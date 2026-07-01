#!/usr/bin/env python3
# ==============================================================================
# CnSS UDP Load Test Script
# Generates test UDP packets to validate the Ingestion Worker functionality.
# Tests sequence tracking, drop calculation, and keep-alive handling.
# ==============================================================================

import socket
import json
import time
import random
from typing import List, Dict, Any

# Configuration
TARGET_HOST = "127.0.0.1"
TARGET_PORT = 5140
CHANNEL_ID = "test-channel-01"


def create_packet_meta(direction: int = 0) -> Dict[str, Any]:
    """Creates a single packet metadata entry."""
    return {
        "direction": direction,
        "src_ip": f"192.168.1.{random.randint(1, 254)}",
        "dst_ip": f"10.0.0.{random.randint(1, 254)}",
        "src_port": random.randint(1024, 65535),
        "dst_port": random.choice([80, 443, 8080, 3306]),
    }


def create_telemetry_batch(
    channel_id: str,
    sequence: int,
    packets_count: int = 5,
    timestamp: Optional[int] = None
) -> Dict[str, Any]:
    """Creates a TelemetryBatch payload."""
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


def send_udp_packet(sock: socket.socket, payload: Dict[str, Any]) -> None:
    """Sends a UDP packet to the target."""
    data = json.dumps(payload).encode("utf-8")
    sock.sendto(data, (TARGET_HOST, TARGET_PORT))
    print(f"✓ Sent batch: seq={payload['sequence']}, packets={len(payload['packets'])}, size={len(data)} bytes")


def test_normal_sequence(sock: socket.socket) -> None:
    """Test 1: Normal sequential delivery (no drops)."""
    print("\n" + "="*60)
    print("TEST 1: Normal Sequential Delivery")
    print("="*60)
    
    base_seq = 1000
    for i in range(10):
        batch = create_telemetry_batch(CHANNEL_ID, base_seq + i, packets_count=5)
        send_udp_packet(sock, batch)
        time.sleep(0.1)
    
    print(f"\n✓ Sent 10 sequential batches (seq {base_seq}-{base_seq+9})")
    print("Expected: 0 drops")


def test_drops(sock: socket.socket) -> None:
    """Test 2: Sequence with gaps (should calculate drops)."""
    print("\n" + "="*60)
    print("TEST 2: Sequence with Gaps (Drop Calculation)")
    print("="*60)
    
    # First batch
    batch1 = create_telemetry_batch(CHANNEL_ID, 2000, packets_count=3)
    send_udp_packet(sock, batch1)
    time.sleep(0.2)
    
    # Skip sequences 2001-2004 (4 packets dropped)
    batch2 = create_telemetry_batch(CHANNEL_ID, 2005, packets_count=3)
    send_udp_packet(sock, batch2)
    time.sleep(0.2)
    
    # Skip sequences 2006-2009 (4 more packets dropped)
    batch3 = create_telemetry_batch(CHANNEL_ID, 2010, packets_count=3)
    send_udp_packet(sock, batch3)
    
    print(f"\n✓ Sent 3 batches with gaps")
    print("Expected: 8 total drops (4 + 4)")


def test_keepalive(sock: socket.socket) -> None:
    """Test 3: Keep-alive batches (empty packets list)."""
    print("\n" + "="*60)
    print("TEST 3: Keep-Alive Batches (Empty Packets)")
    print("="*60)
    
    for i in range(5):
        batch = create_telemetry_batch(CHANNEL_ID, 3000 + i, packets_count=0)
        send_udp_packet(sock, batch)
        time.sleep(0.2)
    
    print(f"\n✓ Sent 5 keep-alive batches (empty packets)")
    print("Expected: Activity timestamp should NOT be updated")


def test_high_volume(sock: socket.socket) -> None:
    """Test 4: High volume burst."""
    print("\n" + "="*60)
    print("TEST 4: High Volume Burst")
    print("="*60)
    
    start_time = time.time()
    for i in range(50):
        batch = create_telemetry_batch(CHANNEL_ID, 4000 + i, packets_count=10)
        send_udp_packet(sock, batch)
    
    elapsed = time.time() - start_time
    print(f"\n✓ Sent 50 batches in {elapsed:.2f} seconds")
    print(f"  Rate: {50/elapsed:.1f} batches/sec")


def test_multiple_channels(sock: socket.socket) -> None:
    """Test 5: Multiple channels simultaneously."""
    print("\n" + "="*60)
    print("TEST 5: Multiple Channels")
    print("="*60)
    
    channels = ["channel-A", "channel-B", "channel-C"]
    for channel in channels:
        for i in range(5):
            batch = create_telemetry_batch(channel, 5000 + i, packets_count=3)
            send_udp_packet(sock, batch)
            time.sleep(0.05)
    
    print(f"\n✓ Sent 15 batches across 3 channels")


def main():
    """Runs all test scenarios."""
    print("\n" + "="*60)
    print("CnSS UDP Load Test Script")
    print(f"Target: {TARGET_HOST}:{TARGET_PORT}")
    print("="*60)
    
    # Create UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    try:
        # Run test scenarios
        test_normal_sequence(sock)
        time.sleep(1)
        
        test_drops(sock)
        time.sleep(1)
        
        test_keepalive(sock)
        time.sleep(1)
        
        test_high_volume(sock)
        time.sleep(1)
        
        test_multiple_channels(sock)
        
        print("\n" + "="*60)
        print("All tests completed!")
        print("="*60)
        print("\nCheck the following in Redis:")
        print("  - GET channel:seq:test-channel-01")
        print("  - HGETALL channel:state:test-channel-01")
        print("  - LLEN udp:buffer:test-channel-01")
        print("  - SMEMBERS sub:active_hashes (if subscriptions exist)")
        
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    finally:
        sock.close()


if __name__ == "__main__":
    main()