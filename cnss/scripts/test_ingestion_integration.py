# ==============================================================================
# Integration Test for Ingestion Worker
# Requires Redis running (make dev). Tests the full pipeline with real Redis.
# ==============================================================================
import asyncio

from core.contracts.udp_contracts import PacketMeta, TelemetryBatch
from core.redis.client import get_redis_client, init_redis_client
from services.ingestion.buffer_manager import BufferManager
from services.ingestion.sequence_tracker import SequenceTracker
from services.ingestion.state_manager import StateManager


async def main() -> None:
    # --- Setup ---
    await init_redis_client()
    redis = get_redis_client()

    # Clean up any previous test data
    await redis.delete("channel:seq:test-ch", "channel:state:test-ch", "udp:buffer:test-ch")

    tracker = SequenceTracker()
    state_manager = StateManager(sequence_tracker=tracker)
    buffer_manager = BufferManager()

    # --- Test 1: Initial State ---
    print("[Test 1] Initial state baseline...")
    batch1 = TelemetryBatch(
        channel_id="test-ch",
        timestamp=1700000000,
        sequence=100,
        window_ms=1000,
        packets=[PacketMeta(direction=0, src_ip="10.0.0.1", dst_ip="10.0.0.2", src_port=1234, dst_port=80, size=0)],
    )
    await state_manager.process_batch(batch1)
    await buffer_manager.push_packets(batch1)

    seq_value = await redis.get("channel:seq:test-ch")
    assert isinstance(seq_value, str), f"Expected str, got {type(seq_value)}"
    assert seq_value == "100", f"Expected seq=100, got {seq_value}"
    print(f"  ✓ Sequence baseline set: {seq_value}")

    state = await redis.hgetall("channel:state:test-ch")
    assert "last_activity_at" in state, "Activity timestamp missing"
    assert state["is_active"] == "1", "Channel should be active"
    print(f"  ✓ Activity tracked: {state}")

    buffer_len = await redis.llen("udp:buffer:test-ch")
    assert buffer_len == 1, f"Expected 1 packet in buffer, got {buffer_len}"
    print(f"  ✓ Buffer contains {buffer_len} packet(s)")

    # --- Test 2: Gap with Drops ---
    print("\n[Test 2] Sequence gap with drops...")
    batch2 = TelemetryBatch(
        channel_id="test-ch",
        timestamp=1700000001,
        sequence=105,  # Gap: 101, 102, 103, 104 are missing
        window_ms=1000,
        packets=[],  # Keep-alive (no packets)
    )
    await state_manager.process_batch(batch2)

    state = await redis.hgetall("channel:state:test-ch")
    dropped_delta = int(state.get("dropped_delta", 0))
    assert dropped_delta == 4, f"Expected 4 drops, got {dropped_delta}"
    print(f"  ✓ Dropped delta accumulated: {dropped_delta}")

    # Activity should NOT be updated for empty batch
    old_activity = state["last_activity_at"]
    batch3 = TelemetryBatch(
        channel_id="test-ch",
        timestamp=1700000002,
        sequence=106,
        window_ms=1000,
        packets=[],
    )
    await state_manager.process_batch(batch3)
    state = await redis.hgetall("channel:state:test-ch")
    assert state["last_activity_at"] == old_activity, "Activity should not change for empty batch"
    print("  ✓ Empty batch did not reset activity timeout")

    # --- Test 3: Buffer Capped List ---
    print("\n[Test 3] Buffer capped list...")
    # Push 10 packets
    packets = [
        PacketMeta(direction=i % 2, src_ip="10.0.0.1", dst_ip="10.0.0.2", src_port=1000 + i, dst_port=80, size=0)
        for i in range(10)
    ]
    batch4 = TelemetryBatch(
        channel_id="test-ch",
        timestamp=1700000003,
        sequence=107,
        window_ms=1000,
        packets=packets,
    )
    await buffer_manager.push_packets(batch4)

    buffer_len = await redis.llen("udp:buffer:test-ch")
    assert buffer_len == 11, f"Expected 11 packets (1 + 10), got {buffer_len}"
    print(f"  ✓ Buffer length: {buffer_len}")

    # --- Cleanup ---
    await redis.delete("channel:seq:test-ch", "channel:state:test-ch", "udp:buffer:test-ch")
    print("\n✅ All integration tests passed!")


if __name__ == "__main__":
    asyncio.run(main())
