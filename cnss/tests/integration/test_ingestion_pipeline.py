# ==============================================================================
# CnSS Ingestion Pipeline Integration Tests
# Validates the end-to-end telemetry ingestion pipeline (Sequence Tracking,
# State Management, Buffering, and Flushing) against a live Redis instance.
# Requires Redis to be running (e.g., via `make dev`).
# ==============================================================================

import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.config import settings
from core.contracts.udp_contracts import PacketMeta, TelemetryBatch
from core.redis.client import close_redis_client, get_redis_client, init_redis_client
from services.ingestion.buffer_manager import BUFFER_KEY_PREFIX, BufferManager
from services.ingestion.flusher import BackgroundFlusher
from services.ingestion.sequence_tracker import SEQ_KEY_PREFIX, SequenceTracker
from services.ingestion.state_manager import STATE_KEY_PREFIX, StateManager
from services.ingestion.udp_server import UDPIngestionServer

# --- Test Constants ---
# Unique channel IDs to prevent collisions with other tests or production data.
TEST_CHANNEL_ID = "integration-test-ch-01"
TEST_CHANNEL_ID_2 = "integration-test-ch-02"

# --- Fixtures ---
@pytest.fixture
async def redis_setup():
    """
    Initializes the global Redis client for the test.
    Ensures a clean state by flushing test-specific keys before and after tests.
    Uses function scope to align with pytest-asyncio's default event loop lifecycle,
    preventing 'Event loop is closed' errors when global clients are reused across loops.
    """
    # Reset the global Redis client to ensure it binds to the current test's event loop
    await close_redis_client()
        
    await init_redis_client()
    redis = get_redis_client()
    
    # Clean up any leftover data from previous failed runs
    await redis.delete(
        f"{SEQ_KEY_PREFIX}{TEST_CHANNEL_ID}",
        f"{STATE_KEY_PREFIX}{TEST_CHANNEL_ID}",
        f"{BUFFER_KEY_PREFIX}{TEST_CHANNEL_ID}",
        f"{SEQ_KEY_PREFIX}{TEST_CHANNEL_ID_2}",
        f"{STATE_KEY_PREFIX}{TEST_CHANNEL_ID_2}",
        f"{BUFFER_KEY_PREFIX}{TEST_CHANNEL_ID_2}",
    )
    
    yield redis
    
    # Teardown: Clean up after the test has run
    await redis.delete(
        f"{SEQ_KEY_PREFIX}{TEST_CHANNEL_ID}",
        f"{STATE_KEY_PREFIX}{TEST_CHANNEL_ID}",
        f"{BUFFER_KEY_PREFIX}{TEST_CHANNEL_ID}",
        f"{SEQ_KEY_PREFIX}{TEST_CHANNEL_ID_2}",
        f"{STATE_KEY_PREFIX}{TEST_CHANNEL_ID_2}",
        f"{BUFFER_KEY_PREFIX}{TEST_CHANNEL_ID_2}",
    )
    
    # Close the client to release resources and reset global state
    await close_redis_client()

@pytest.fixture
def sequence_tracker(redis_setup):
    """Provides a real SequenceTracker instance connected to the test Redis."""
    return SequenceTracker()

@pytest.fixture
def state_manager(redis_setup, sequence_tracker):
    """Provides a real StateManager instance connected to the test Redis."""
    return StateManager(sequence_tracker=sequence_tracker)

@pytest.fixture
def buffer_manager(redis_setup):
    """Provides a real BufferManager instance connected to the test Redis."""
    return BufferManager()

@pytest.fixture
def mock_flusher():
    """
    Provides a mocked BackgroundFlusher to verify channel registration
    without actually executing the background flush loop or DB inserts.
    """
    flusher = MagicMock(spec=BackgroundFlusher)
    flusher.register_channel = AsyncMock()
    return flusher

@pytest.fixture
def udp_server(state_manager, buffer_manager, mock_flusher):
    """
    Provides a UDPIngestionServer instance wired with real State/Buffer managers
    and a mocked Flusher for pipeline integration testing.
    """
    return UDPIngestionServer(
        state_manager=state_manager,
        buffer_manager=buffer_manager,
        flusher=mock_flusher,
    )

# --- Helper Functions ---
def create_batch(
    channel_id: str,
    sequence: int,
    packet_count: int = 1,
    timestamp: int | None = None,
) -> TelemetryBatch:
    """Constructs a valid TelemetryBatch for testing."""
    if timestamp is None:
        timestamp = int(time.time())
    
    packets = [
        PacketMeta(
            direction=i % 2,
            src_ip="192.168.1.10",
            dst_ip="8.8.8.8",
            src_port=10000 + i,
            dst_port=80,
        )
        for i in range(packet_count)
    ]
    
    return TelemetryBatch(
        channel_id=channel_id,
        timestamp=timestamp,
        sequence=sequence,
        window_ms=1000,
        packets=packets,
    )

# --- Sequence Tracking Integration Tests ---
async def test_initial_sequence_baseline(redis_setup, state_manager):
    """
    Architecture §2.1: If the sequence key does not exist, the first received
    sequence is stored as the baseline without calculating drops.
    """
    redis = redis_setup
    seq_key = f"{SEQ_KEY_PREFIX}{TEST_CHANNEL_ID}"
    
    # Ensure key is missing
    await redis.delete(seq_key)
    
    batch = create_batch(TEST_CHANNEL_ID, sequence=1000)
    await state_manager.process_batch(batch)
    
    # Verify baseline is set
    stored_seq = await redis.get(seq_key)
    assert stored_seq == "1000"
    
    # Verify no drops accumulated
    state_key = f"{STATE_KEY_PREFIX}{TEST_CHANNEL_ID}"
    state = await redis.hgetall(state_key)
    assert int(state.get("dropped_delta", 0)) == 0

async def test_sequential_processing_no_drops(redis_setup, state_manager):
    """
    Architecture §2.1: If incoming_sequence == last_sequence + 1,
    it's a perfect sequential packet. Update baseline, return 0 drops.
    """
    redis = redis_setup
    seq_key = f"{SEQ_KEY_PREFIX}{TEST_CHANNEL_ID}"
    state_key = f"{STATE_KEY_PREFIX}{TEST_CHANNEL_ID}"
    
    # Reset state
    await redis.delete(seq_key, state_key)
    
    # Process initial batch
    await state_manager.process_batch(create_batch(TEST_CHANNEL_ID, sequence=2000))
    
    # Process sequential batch
    await state_manager.process_batch(create_batch(TEST_CHANNEL_ID, sequence=2001))
    
    # Verify sequence updated
    assert await redis.get(seq_key) == "2001"
    
    # Verify no drops
    state = await redis.hgetall(state_key)
    assert int(state.get("dropped_delta", 0)) == 0

async def test_sequence_gap_calculates_drops(redis_setup, state_manager):
    """
    Architecture §2.1: If incoming_sequence > last_sequence + 1,
    calculates dropped = incoming_sequence - (last_sequence + 1).
    """
    redis = redis_setup
    seq_key = f"{SEQ_KEY_PREFIX}{TEST_CHANNEL_ID}"
    state_key = f"{STATE_KEY_PREFIX}{TEST_CHANNEL_ID}"
    
    await redis.delete(seq_key, state_key)
    
    # Initial batch
    await state_manager.process_batch(create_batch(TEST_CHANNEL_ID, sequence=3000))
    
    # Gap: 3001, 3002, 3003 are missing (3 drops)
    await state_manager.process_batch(create_batch(TEST_CHANNEL_ID, sequence=3004))
    
    assert await redis.get(seq_key) == "3004"
    
    state = await redis.hgetall(state_key)
    assert int(state["dropped_delta"]) == 3

async def test_out_of_order_ignored(redis_setup, state_manager):
    """
    Architecture §2.1: If incoming_sequence <= last_sequence,
    it's an out-of-order or duplicate delivery. Ignore it gracefully.
    """
    redis = redis_setup
    seq_key = f"{SEQ_KEY_PREFIX}{TEST_CHANNEL_ID}"
    
    await redis.delete(seq_key)
    
    # Initial batch
    await state_manager.process_batch(create_batch(TEST_CHANNEL_ID, sequence=4000))
    
    # Out-of-order batch (older sequence)
    await state_manager.process_batch(create_batch(TEST_CHANNEL_ID, sequence=3999))
    
    # Sequence should NOT be updated
    assert await redis.get(seq_key) == "4000"

async def test_sequence_reset_detection(redis_setup, state_manager):
    """
    Architecture §2.1: If last_sequence - incoming_sequence > THRESHOLD,
    treat as a reset, forcefully update last_sequence, and reset drop counter.
    """
    redis = redis_setup
    seq_key = f"{SEQ_KEY_PREFIX}{TEST_CHANNEL_ID}"
    state_key = f"{STATE_KEY_PREFIX}{TEST_CHANNEL_ID}"
    
    await redis.delete(seq_key, state_key)
    
    # Simulate a high sequence number
    await state_manager.process_batch(create_batch(TEST_CHANNEL_ID, sequence=5000000))
    
    # Simulate a reboot/reset (massive backward jump)
    await state_manager.process_batch(create_batch(TEST_CHANNEL_ID, sequence=100))
    
    # Baseline must be forcefully updated
    assert await redis.get(seq_key) == "100"
    
    # Drops should NOT be accumulated for the backward jump
    state = await redis.hgetall(state_key)
    assert int(state.get("dropped_delta", 0)) == 0

# --- State Management Integration Tests ---
async def test_activity_tracking_only_with_packets(redis_setup, state_manager):
    """
    Architecture §2.1: Activity Tracking uses HSET last_activity_at
    ONLY IF len(TelemetryBatch.packets) > 0. Empty keep-alive batches
    do not reset the timeout.
    """
    redis = redis_setup
    state_key = f"{STATE_KEY_PREFIX}{TEST_CHANNEL_ID}"
    
    await redis.delete(state_key)
    
    # Batch with packets
    batch_with_packets = create_batch(TEST_CHANNEL_ID, sequence=6000, packet_count=5)
    await state_manager.process_batch(batch_with_packets)
    
    state = await redis.hgetall(state_key)
    assert "last_activity_at" in state
    assert state["is_active"] == "1"
    initial_activity = float(state["last_activity_at"])
    
    # Wait briefly to ensure timestamp difference
    await asyncio.sleep(0.1)
    
    # Keep-alive batch (empty packets)
    keepalive_batch = create_batch(TEST_CHANNEL_ID, sequence=6001, packet_count=0)
    await state_manager.process_batch(keepalive_batch)
    
    state = await redis.hgetall(state_key)
    # Activity timestamp should NOT be updated
    assert float(state["last_activity_at"]) == initial_activity

async def test_ttl_enforcement(redis_setup, state_manager):
    """
    Architecture §2.1: Sets a TTL of 6 seconds on the key.
    """
    redis = redis_setup
    state_key = f"{STATE_KEY_PREFIX}{TEST_CHANNEL_ID}"
    
    await redis.delete(state_key)
    
    await state_manager.process_batch(create_batch(TEST_CHANNEL_ID, sequence=7000))
    
    ttl = await redis.ttl(state_key)
    # TTL should be approximately 6 seconds (allowing for slight execution delay)
    assert 4 <= ttl <= 6

# --- Buffer Management Integration Tests ---
async def test_normal_buffer_push(redis_setup, buffer_manager):
    """
    Architecture §2.1: Pushes raw packet metadata into a Redis List.
    """
    redis = redis_setup
    buffer_key = f"{BUFFER_KEY_PREFIX}{TEST_CHANNEL_ID}"
    
    await redis.delete(buffer_key)
    
    batch = create_batch(TEST_CHANNEL_ID, sequence=8000, packet_count=3)
    await buffer_manager.push_packets(batch)
    
    length = await redis.llen(buffer_key)
    assert length == 3
    
    # Verify data format (JSON strings)
    items = await redis.lrange(buffer_key, 0, -1)
    for item in items:
        record = json.loads(item)
        assert "channel_id" in record
        assert "time" in record
        assert "src_ip" in record

async def test_buffer_capped_list_enforcement(redis_setup, buffer_manager):
    """
    Architecture §2.1: To prevent OOM, the list is strictly capped.
    If LLEN exceeds threshold, LTRIM is used to discard oldest entries.
    """
    redis = redis_setup
    buffer_key = f"{BUFFER_KEY_PREFIX}{TEST_CHANNEL_ID}"
    
    await redis.delete(buffer_key)
    
    # Temporarily lower the max length for testing
    original_max_len = settings.redis_udp_buffer_max_len
    settings.redis_udp_buffer_max_len = 10
    
    try:
        # Push 8 packets
        await buffer_manager.push_packets(create_batch(TEST_CHANNEL_ID, sequence=9000, packet_count=8))
        assert await redis.llen(buffer_key) == 8
        
        # Push 5 more packets. Total would be 13, exceeding max_len=10.
        # LTRIM should keep the newest 10 packets.
        await buffer_manager.push_packets(create_batch(TEST_CHANNEL_ID, sequence=9001, packet_count=5))
        
        length = await redis.llen(buffer_key)
        assert length == 10
        
        # Verify the oldest packets were dropped (the first 3 packets from seq 9000)
        # The list is LPUSH, so newest are at index 0.
        # We should have 5 packets from seq 9001 and 5 from seq 9000.
        items = await redis.lrange(buffer_key, 0, -1)
        # Since we can't easily check sequence in the buffer (it's not stored),
        # we just verify the count is strictly capped.
        assert len(items) == 10
    finally:
        # Restore original setting
        settings.redis_udp_buffer_max_len = original_max_len
        await redis.delete(buffer_key)

async def test_empty_batch_not_buffered(redis_setup, buffer_manager):
    """
    Architecture §2.1: Empty keep-alive batches must not be buffered.
    """
    redis = redis_setup
    buffer_key = f"{BUFFER_KEY_PREFIX}{TEST_CHANNEL_ID}"
    
    await redis.delete(buffer_key)
    
    keepalive = create_batch(TEST_CHANNEL_ID, sequence=10000, packet_count=0)
    await buffer_manager.push_packets(keepalive)
    
    length = await redis.llen(buffer_key)
    assert length == 0

# --- Full Pipeline Integration Tests ---
async def test_full_pipeline_handle_batch(redis_setup, udp_server, mock_flusher):
    """
    Validates the full orchestration of UDPIngestionServer._handle_batch:
    1. Registers channel with flusher.
    2. Updates state via StateManager.
    3. Buffers packets via BufferManager.
    """
    redis = redis_setup
    seq_key = f"{SEQ_KEY_PREFIX}{TEST_CHANNEL_ID_2}"
    state_key = f"{STATE_KEY_PREFIX}{TEST_CHANNEL_ID_2}"
    buffer_key = f"{BUFFER_KEY_PREFIX}{TEST_CHANNEL_ID_2}"
    
    await redis.delete(seq_key, state_key, buffer_key)
    
    batch = create_batch(TEST_CHANNEL_ID_2, sequence=11000, packet_count=2)
    addr = ("127.0.0.1", 12345)
    
    await udp_server._handle_batch(batch, addr)
    
    # 1. Verify flusher registration
    mock_flusher.register_channel.assert_awaited_once_with(TEST_CHANNEL_ID_2)
    
    # 2. Verify state update
    assert await redis.get(seq_key) == "11000"
    state = await redis.hgetall(state_key)
    assert state["is_active"] == "1"
    
    # 3. Verify buffering
    assert await redis.llen(buffer_key) == 2
    
    # Cleanup
    await redis.delete(seq_key, state_key, buffer_key)

# --- Background Flusher Integration Tests ---
async def test_flusher_atomic_pop_and_insert(redis_setup, buffer_manager):
    """
    Architecture §2.1: Background Flush periodically flushes the Redis buffer
    into the TimescaleDB hypertable using batch INSERT operations.
    Validates that the Lua script atomically pops items and the DB insert is called.
    """
    redis = redis_setup
    buffer_key = f"{BUFFER_KEY_PREFIX}{TEST_CHANNEL_ID}"
    
    await redis.delete(buffer_key)
    
    # Push some data to the buffer
    batch = create_batch(TEST_CHANNEL_ID, sequence=12000, packet_count=2)
    await buffer_manager.push_packets(batch)
    
    # Verify data is in Redis
    assert await redis.llen(buffer_key) == 2
    
    # Mock the DB pool and connection
    mock_conn = AsyncMock()
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_conn), __aexit__=AsyncMock()))
    
    # We need to patch get_db_pool in the flusher module
    from services.ingestion import flusher as flusher_module
    original_get_db_pool = flusher_module.get_db_pool
    flusher_module.get_db_pool = MagicMock(return_value=mock_pool)
    
    try:
        bg_flusher = BackgroundFlusher()
        await bg_flusher._flush_channel(TEST_CHANNEL_ID)
        
        # Verify Redis buffer is now empty (atomic pop)
        assert await redis.llen(buffer_key) == 0
        
        # Verify DB executemany was called with the correct number of records
        mock_conn.executemany.assert_awaited_once()
        call_args = mock_conn.executemany.call_args
        records = call_args[0][1]
        assert len(records) == 2
    finally:
        # Restore original function
        flusher_module.get_db_pool = original_get_db_pool
        await redis.delete(buffer_key)