# ==============================================================================
# CnSS State Manager Unit Tests
# Validates Fast Path Redis state updates, activity tracking, drop accumulation,
# and TTL enforcement against architectural specifications (architecture.md §2.1).
# ==============================================================================

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.contracts.udp_contracts import PacketMeta, TelemetryBatch
from core.exceptions import RedisError
from services.ingestion.state_manager import STATE_KEY_TTL_SEC, StateManager

# --- Test Fixtures ---


@pytest.fixture
def mock_redis():
    """Provides a mocked Redis client instance with pipeline support."""
    redis = AsyncMock()
    # Create a mock pipeline that returns itself for method chaining.
    # IMPORTANT: In redis.asyncio, pipeline commands (hset, hincrby, expire)
    # are SYNCHRONOUS and return the pipeline object for chaining.
    # Only pipeline.execute() is an async method that must be awaited.
    pipeline = MagicMock()
    pipeline.hincrby = MagicMock(return_value=pipeline)
    pipeline.hset = MagicMock(return_value=pipeline)
    pipeline.expire = MagicMock(return_value=pipeline)
    pipeline.execute = AsyncMock(return_value=[])
    redis.pipeline = MagicMock(return_value=pipeline)
    return redis


@pytest.fixture
def mock_tracker():
    """Provides a mocked SequenceTracker instance."""
    tracker = AsyncMock()
    # Default: no drops, no reset
    tracker.process_sequence = AsyncMock(return_value=(0, False))
    return tracker


@pytest.fixture
def state_manager(mock_redis, mock_tracker):
    """Provides a StateManager instance with mocked dependencies."""
    # Patch the global Redis client getter to inject our mock
    with patch("services.ingestion.state_manager.get_redis_client", return_value=mock_redis):
        yield StateManager(sequence_tracker=mock_tracker)


@pytest.fixture
def sample_batch():
    """Creates a sample TelemetryBatch with packets for testing."""
    return TelemetryBatch(
        channel_id="test-ch",
        timestamp=1700000000,
        sequence=100,
        window_ms=1000,
        packets=[
            PacketMeta(direction=0, src_ip="10.0.0.1", dst_ip="10.0.0.2", src_port=1234, dst_port=80, size=64),
            PacketMeta(direction=1, src_ip="10.0.0.2", dst_ip="10.0.0.1", src_port=80, dst_port=1234, size=128),
        ],
    )


@pytest.fixture
def keepalive_batch():
    """Creates a keep-alive TelemetryBatch (empty packets list) for testing."""
    return TelemetryBatch(
        channel_id="test-ch",
        timestamp=1700000000,
        sequence=101,
        window_ms=1000,
        packets=[],  # Empty: keep-alive batch
    )


# --- Normal Batch Processing Tests ---


async def test_batch_with_packets_updates_activity(state_manager, mock_redis, mock_tracker, sample_batch):
    """
    Architecture §2.1: Activity Tracking
    Uses HSET channel:state:{channel_id} last_activity_at <current_timestamp>
    ONLY IF len(TelemetryBatch.packets) > 0.
    """
    mock_tracker.process_sequence.return_value = (0, False)

    await state_manager.process_batch(sample_batch)

    # Verify sequence tracker was called
    mock_tracker.process_sequence.assert_awaited_once_with("test-ch", 100)

    # Verify pipeline was created
    mock_redis.pipeline.assert_called_once_with(transaction=False)
    pipeline = mock_redis.pipeline.return_value

    # Verify HSET was called with last_activity_at and is_active
    pipeline.hset.assert_called_once()
    call_args = pipeline.hset.call_args
    assert call_args[0][0] == "channel:state:test-ch"
    mapping = call_args[1]["mapping"]
    assert "last_activity_at" in mapping
    assert mapping["is_active"] == 1  # Must be integer 1, not boolean True

    # Verify TTL was set
    pipeline.expire.assert_called_once_with("channel:state:test-ch", STATE_KEY_TTL_SEC)

    # Verify pipeline was executed
    pipeline.execute.assert_awaited_once()


async def test_keepalive_batch_does_not_update_activity(state_manager, mock_redis, mock_tracker, keepalive_batch):
    """
    Architecture §2.1: Empty keep-alive batches do not reset the timeout.
    HSET must NOT be called for batches with empty packets list.
    """
    mock_tracker.process_sequence.return_value = (0, False)

    await state_manager.process_batch(keepalive_batch)

    # Verify sequence tracker was still called (for sequence validation)
    mock_tracker.process_sequence.assert_awaited_once_with("test-ch", 101)

    pipeline = mock_redis.pipeline.return_value

    # Verify HSET was NOT called (no activity update for keep-alive)
    pipeline.hset.assert_not_called()

    # Verify TTL was still refreshed (key expiration is updated on every batch)
    pipeline.expire.assert_called_once_with("channel:state:test-ch", STATE_KEY_TTL_SEC)

    # Verify pipeline was executed
    pipeline.execute.assert_awaited_once()


# --- Drop Accumulation Tests ---


async def test_batch_with_drops_accumulates_delta(state_manager, mock_redis, mock_tracker, sample_batch):
    """
    Architecture §2.1: Uses HINCRBY channel:state:{channel_id} dropped_delta <calculated_drops>
    to accumulate dropped packets.
    """
    # Simulate 5 dropped packets
    mock_tracker.process_sequence.return_value = (5, False)

    await state_manager.process_batch(sample_batch)

    pipeline = mock_redis.pipeline.return_value

    # Verify HINCRBY was called with correct drop count
    pipeline.hincrby.assert_called_once_with("channel:state:test-ch", "dropped_delta", 5)

    # Verify activity was still updated (batch has packets)
    pipeline.hset.assert_called_once()

    # Verify TTL was set
    pipeline.expire.assert_called_once_with("channel:state:test-ch", STATE_KEY_TTL_SEC)


async def test_batch_without_drops_skips_hincrby(state_manager, mock_redis, mock_tracker, sample_batch):
    """
    Verify that HINCRBY is NOT called when no drops are detected.
    """
    mock_tracker.process_sequence.return_value = (0, False)

    await state_manager.process_batch(sample_batch)

    pipeline = mock_redis.pipeline.return_value

    # Verify HINCRBY was NOT called
    pipeline.hincrby.assert_not_called()

    # Verify activity was updated
    pipeline.hset.assert_called_once()


async def test_keepalive_with_drops_still_accumulates(state_manager, mock_redis, mock_tracker, keepalive_batch):
    """
    Verify that drops are accumulated even for keep-alive batches.
    Sequence tracking happens regardless of packet presence.
    """
    mock_tracker.process_sequence.return_value = (3, False)

    await state_manager.process_batch(keepalive_batch)

    pipeline = mock_redis.pipeline.return_value

    # Verify HINCRBY was called (drops are accumulated)
    pipeline.hincrby.assert_called_once_with("channel:state:test-ch", "dropped_delta", 3)

    # Verify HSET was NOT called (keep-alive, no activity update)
    pipeline.hset.assert_not_called()

    # Verify TTL was still refreshed
    pipeline.expire.assert_called_once_with("channel:state:test-ch", STATE_KEY_TTL_SEC)


# --- Sequence Reset Tests ---


async def test_sequence_reset_does_not_accumulate_drops(state_manager, mock_redis, mock_tracker, sample_batch):
    """
    Architecture §2.1: Sequence Reset Detection
    If reset detected, drop counter for this batch is reset (return 0 drops).
    """
    # Simulate sequence reset (0 drops, is_reset=True)
    mock_tracker.process_sequence.return_value = (0, True)

    await state_manager.process_batch(sample_batch)

    pipeline = mock_redis.pipeline.return_value

    # Verify HINCRBY was NOT called (reset means 0 drops)
    pipeline.hincrby.assert_not_called()

    # Verify activity was updated (batch has packets)
    pipeline.hset.assert_called_once()


# --- TTL Enforcement Tests ---


async def test_ttl_is_set_to_six_seconds(state_manager, mock_redis, mock_tracker, sample_batch):
    """
    Architecture §2.1: Sets a TTL of 6 seconds on the key.
    If the CN dies, the key expires, naturally indicating inactivity.
    """
    mock_tracker.process_sequence.return_value = (0, False)

    await state_manager.process_batch(sample_batch)

    pipeline = mock_redis.pipeline.return_value

    # Verify TTL is exactly 6 seconds (STATE_KEY_TTL_SEC constant)
    pipeline.expire.assert_called_once_with("channel:state:test-ch", 6)
    assert STATE_KEY_TTL_SEC == 6


async def test_ttl_refreshed_on_keepalive(state_manager, mock_redis, mock_tracker, keepalive_batch):
    """
    Verify that TTL is refreshed even for keep-alive batches.
    This prevents premature expiration during periods of no traffic.
    """
    mock_tracker.process_sequence.return_value = (0, False)

    await state_manager.process_batch(keepalive_batch)

    pipeline = mock_redis.pipeline.return_value

    # Verify TTL was refreshed
    pipeline.expire.assert_called_once_with("channel:state:test-ch", STATE_KEY_TTL_SEC)


# --- Error Handling Tests ---


async def test_redis_pipeline_error_wrapped(state_manager, mock_redis, mock_tracker, sample_batch):
    """
    Verify that Redis pipeline execution errors are wrapped in RedisError
    to maintain consistent error handling across the ingestion pipeline.
    """
    mock_tracker.process_sequence.return_value = (0, False)

    # Simulate pipeline execution failure
    pipeline = mock_redis.pipeline.return_value
    pipeline.execute.side_effect = Exception("Connection lost")

    with pytest.raises(RedisError) as exc_info:
        await state_manager.process_batch(sample_batch)

    assert "State update failed" in str(exc_info.value)
    assert "test-ch" in str(exc_info.value)


# --- Pipeline Optimization Tests ---


async def test_pipeline_used_for_batch_operations(state_manager, mock_redis, mock_tracker, sample_batch):
    """
    Architecture §2.1: Use a pipeline to batch Redis commands, minimizing network roundtrips.
    Verify that pipeline(transaction=False) is used for high-throughput processing.
    """
    mock_tracker.process_sequence.return_value = (2, False)

    await state_manager.process_batch(sample_batch)

    # Verify pipeline was created with transaction=False
    # (avoiding MULTI/EXEC overhead improves IOPS)
    mock_redis.pipeline.assert_called_once_with(transaction=False)

    # Verify all operations were queued in the pipeline
    pipeline = mock_redis.pipeline.return_value
    assert pipeline.hincrby.called
    assert pipeline.hset.called
    assert pipeline.expire.called

    # Verify single execute call (batched operations)
    pipeline.execute.assert_awaited_once()


# --- State Key Construction Tests ---


async def test_state_key_prefix_correct(state_manager, mock_redis, mock_tracker, sample_batch):
    """
    Verify that the state key follows the correct prefix pattern:
    channel:state:{channel_id}
    """
    mock_tracker.process_sequence.return_value = (0, False)

    await state_manager.process_batch(sample_batch)

    pipeline = mock_redis.pipeline.return_value

    # Verify correct key format
    pipeline.expire.assert_called_once()
    call_args = pipeline.expire.call_args[0]
    assert call_args[0] == "channel:state:test-ch"
    assert call_args[0].startswith("channel:state:")


# --- Activity Timestamp Tests ---


async def test_activity_timestamp_is_current_time(state_manager, mock_redis, mock_tracker, sample_batch):
    """
    Verify that last_activity_at is set to the current Unix timestamp.
    """
    mock_tracker.process_sequence.return_value = (0, False)

    await state_manager.process_batch(sample_batch)

    pipeline = mock_redis.pipeline.return_value

    # Extract the timestamp from HSET call
    call_args = pipeline.hset.call_args
    mapping = call_args[1]["mapping"]
    timestamp = mapping["last_activity_at"]

    # Verify timestamp is a float (Unix timestamp from time.time())
    assert isinstance(timestamp, float)
    # Verify timestamp is recent (within last second)
    import time

    assert abs(time.time() - timestamp) < 1.0


async def test_is_active_flag_set_to_one(state_manager, mock_redis, mock_tracker, sample_batch):
    """
    Architecture §2.1: is_active flag (1/0) indicating if the channel is currently receiving traffic.
    Verify that is_active is set to integer 1 (not boolean True or string "1").
    """
    mock_tracker.process_sequence.return_value = (0, False)

    await state_manager.process_batch(sample_batch)

    pipeline = mock_redis.pipeline.return_value

    # Extract is_active from HSET call
    call_args = pipeline.hset.call_args
    mapping = call_args[1]["mapping"]

    # Verify is_active is integer 1
    assert mapping["is_active"] == 1
    assert isinstance(mapping["is_active"], int)
