# ==============================================================================
# CnSS Sequence Tracker Unit Tests
# Validates sequence tracking logic, drop calculation, and reset detection
# against the architectural specifications defined in architecture.md §2.1.
# ==============================================================================

from unittest.mock import AsyncMock, patch

import pytest

from core.exceptions import RedisError
from services.ingestion.sequence_tracker import SEQ_KEY_PREFIX, SequenceTracker

# --- Test Fixtures ---


@pytest.fixture
def mock_redis():
    """Provides a mocked Redis client instance."""
    return AsyncMock()


@pytest.fixture
def tracker(mock_redis):
    """Provides a SequenceTracker instance with a mocked Redis client."""
    # Patch the global Redis client getter to inject our mock
    with patch("services.ingestion.sequence_tracker.get_redis_client", return_value=mock_redis):
        yield SequenceTracker()


# --- Initial State Handling Tests ---


async def test_initial_state_baseline_set(tracker, mock_redis):
    """
    Architecture §2.1: If the key does not exist (new channel or post-crash),
    the first received sequence is stored as the baseline without calculating drops.
    """
    # Redis returns None for a non-existent key
    mock_redis.get.return_value = None

    channel_id = "test-ch"
    incoming_seq = 100

    dropped, is_reset = await tracker.process_sequence(channel_id, incoming_seq)

    assert dropped == 0, "Initial state should not calculate drops"
    assert is_reset is False, "Initial state is not a reset"
    mock_redis.get.assert_awaited_once_with(f"{SEQ_KEY_PREFIX}{channel_id}")
    mock_redis.set.assert_awaited_once_with(f"{SEQ_KEY_PREFIX}{channel_id}", incoming_seq)


# --- Normal Sequence Processing Tests ---


async def test_sequential_packet_no_drops(tracker, mock_redis):
    """
    Architecture §2.1: If incoming_sequence == last_sequence + 1,
    it's a perfect sequential packet. Update baseline, return 0 drops.
    """
    mock_redis.get.return_value = "100"

    channel_id = "test-ch"
    incoming_seq = 101

    dropped, is_reset = await tracker.process_sequence(channel_id, incoming_seq)

    assert dropped == 0
    assert is_reset is False
    mock_redis.set.assert_awaited_once_with(f"{SEQ_KEY_PREFIX}{channel_id}", incoming_seq)


async def test_gap_calculates_drops(tracker, mock_redis):
    """
    Architecture §2.1: If incoming_sequence > last_sequence + 1,
    calculates dropped = incoming_sequence - (last_sequence + 1).
    """
    mock_redis.get.return_value = "100"

    channel_id = "test-ch"
    incoming_seq = 105  # Gap: 101, 102, 103, 104 (4 drops)

    dropped, is_reset = await tracker.process_sequence(channel_id, incoming_seq)

    assert dropped == 4, "Should calculate exactly 4 dropped packets"
    assert is_reset is False
    mock_redis.set.assert_awaited_once_with(f"{SEQ_KEY_PREFIX}{channel_id}", incoming_seq)


async def test_out_of_order_ignored(tracker, mock_redis):
    """
    Architecture §2.1: If incoming_sequence <= last_sequence,
    it's an out-of-order or duplicate delivery. Ignore it gracefully.
    """
    mock_redis.get.return_value = "100"

    channel_id = "test-ch"
    incoming_seq = 99  # Out of order

    dropped, is_reset = await tracker.process_sequence(channel_id, incoming_seq)

    assert dropped == 0
    assert is_reset is False
    # Key should NOT be updated for out-of-order packets
    mock_redis.set.assert_not_awaited()


async def test_duplicate_ignored(tracker, mock_redis):
    """
    Architecture §2.1: Duplicate packets (incoming == last) must be ignored.
    """
    mock_redis.get.return_value = "100"

    channel_id = "test-ch"
    incoming_seq = 100  # Exact duplicate

    dropped, is_reset = await tracker.process_sequence(channel_id, incoming_seq)

    assert dropped == 0
    assert is_reset is False
    mock_redis.set.assert_not_awaited()


# --- Sequence Reset Detection Tests ---


async def test_sequence_reset_detected(tracker, mock_redis):
    """
    Architecture §2.1: If last_sequence - incoming_sequence > THRESHOLD,
    treat as a reset, forcefully update last_sequence, and reset drop counter.
    """
    # Simulate a high sequence number that wrapped around or rebooted
    mock_redis.get.return_value = "2000000"

    channel_id = "test-ch"
    incoming_seq = 100  # Massive backward jump (> 1,000,000 threshold)

    dropped, is_reset = await tracker.process_sequence(channel_id, incoming_seq)

    assert dropped == 0, "Reset should not calculate drops for the backward jump"
    assert is_reset is True, "Must flag this event as a sequence reset"
    # Baseline must be forcefully updated to the new incoming sequence
    mock_redis.set.assert_awaited_once_with(f"{SEQ_KEY_PREFIX}{channel_id}", incoming_seq)


async def test_normal_backward_jump_not_reset(tracker, mock_redis):
    """
    Ensure that a backward jump smaller than the threshold is treated as
    out-of-order/duplicate, NOT as a reset.
    """
    mock_redis.get.return_value = "100"

    channel_id = "test-ch"
    incoming_seq = 90  # Backward jump, but < THRESHOLD (1,000,000)

    dropped, is_reset = await tracker.process_sequence(channel_id, incoming_seq)

    assert dropped == 0
    assert is_reset is False
    mock_redis.set.assert_not_awaited()


# --- Error Handling Tests ---


async def test_redis_error_wrapped(tracker, mock_redis):
    """
    Verify that unexpected Redis errors are wrapped in the custom RedisError
    to maintain a consistent error handling strategy across the ingestion pipeline.
    """
    mock_redis.get.side_effect = Exception("Connection lost")

    channel_id = "test-ch"
    incoming_seq = 100

    with pytest.raises(RedisError) as exc_info:
        await tracker.process_sequence(channel_id, incoming_seq)

    assert "Sequence tracking failed" in str(exc_info.value)
