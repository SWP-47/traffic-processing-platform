# ==============================================================================
# CnSS Buffer Manager Unit Tests
# Validates Redis Capped List buffering, data serialization, and OOM protection
# against the architectural specifications defined in architecture.md §2.1.
# ==============================================================================

import json
import pytest
from unittest.mock import AsyncMock, patch

from core.contracts.udp_contracts import PacketMeta, TelemetryBatch
from core.exceptions import RedisError
from services.ingestion.buffer_manager import BUFFER_KEY_PREFIX, BufferManager

# --- Test Fixtures ---

@pytest.fixture
def mock_redis():
    """Provides a mocked Redis client instance."""
    return AsyncMock()


@pytest.fixture
def buffer_manager(mock_redis):
    """Provides a BufferManager instance with a mocked Redis client."""
    # Patch the global Redis client getter to inject our mock
    with patch("services.ingestion.buffer_manager.get_redis_client", return_value=mock_redis):
        yield BufferManager()


@pytest.fixture
def sample_batch():
    """Creates a sample TelemetryBatch with packets for testing."""
    return TelemetryBatch(
        channel_id="test-ch",
        timestamp=1700000000,
        sequence=100,
        window_ms=1000,
        packets=[
            PacketMeta(direction=0, src_ip="10.0.0.1", dst_ip="10.0.0.2", src_port=1234, dst_port=80),
            PacketMeta(direction=1, src_ip="10.0.0.2", dst_ip="10.0.0.1", src_port=80, dst_port=1234),
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


# --- Empty Batch Handling Tests ---

async def test_empty_batch_skipped(buffer_manager, mock_redis, keepalive_batch):
    """
    Architecture §2.1: Empty keep-alive batches must not be buffered.
    Verify that no Redis operations are performed for batches with empty packets.
    """
    await buffer_manager.push_packets(keepalive_batch)
    
    # Verify no Redis operations were called
    mock_redis.llen.assert_not_awaited()
    mock_redis.lpush.assert_not_awaited()
    mock_redis.ltrim.assert_not_awaited()


# --- Normal Buffer Push Tests ---

async def test_normal_push_without_cap(buffer_manager, mock_redis, sample_batch):
    """
    Architecture §2.1: Push raw packet metadata into Redis List when buffer has space.
    Verify LPUSH is called with correct serialized data.
    """
    # Buffer is not full (current length < max)
    mock_redis.llen.return_value = 50
    
    await buffer_manager.push_packets(sample_batch)
    
    # Verify LLEN was checked
    mock_redis.llen.assert_awaited_once_with(f"{BUFFER_KEY_PREFIX}test-ch")
    
    # Verify LPUSH was called with serialized records
    mock_redis.lpush.assert_awaited_once()
    call_args = mock_redis.lpush.call_args
    assert call_args[0][0] == f"{BUFFER_KEY_PREFIX}test-ch"
    
    # Verify correct number of records were pushed
    serialized_records = call_args[0][1:]
    assert len(serialized_records) == 2, f"Expected 2 records, got {len(serialized_records)}"
    
    # Verify LTRIM was NOT called (buffer not full)
    mock_redis.ltrim.assert_not_awaited()


async def test_serialization_format(buffer_manager, mock_redis, sample_batch):
    """
    Architecture §2.1: Flattens TelemetryBatch into individual packet records
    matching the 'packet_flows' TimescaleDB schema.
    Verify correct JSON structure with ISO 8601 timestamp.
    """
    mock_redis.llen.return_value = 0
    
    await buffer_manager.push_packets(sample_batch)
    
    # Extract serialized records from LPUSH call
    call_args = mock_redis.lpush.call_args
    serialized_records = call_args[0][1:]
    
    # Parse and validate first record
    record = json.loads(serialized_records[0])
    
    # Verify all required fields are present
    assert record["channel_id"] == "test-ch"
    assert record["direction"] == 0
    assert record["src_ip"] == "10.0.0.1"
    assert record["dst_ip"] == "10.0.0.2"
    assert record["src_port"] == 1234
    assert record["dst_port"] == 80
    
    # Verify timestamp is ISO 8601 format (contains 'T' and timezone)
    assert "time" in record
    assert "T" in record["time"], "Timestamp must be ISO 8601 format"
    assert "+" in record["time"] or "Z" in record["time"], "Timestamp must include timezone"


# --- Capped List Enforcement Tests ---

async def test_push_with_cap_enforcement(buffer_manager, mock_redis, sample_batch):
    """
    Architecture §2.1: If LLEN exceeds threshold, use LTRIM to discard oldest entries.
    Verify LTRIM is called before LPUSH when buffer is full.
    """
    from core.config import settings
    
    # Buffer is at capacity
    mock_redis.llen.return_value = settings.redis_udp_buffer_max_len
    
    await buffer_manager.push_packets(sample_batch)
    
    # Verify LLEN was checked
    mock_redis.llen.assert_awaited_once()
    
    # Verify LTRIM was called to make room
    mock_redis.ltrim.assert_awaited_once()
    trim_call_args = mock_redis.ltrim.call_args[0]
    assert trim_call_args[0] == f"{BUFFER_KEY_PREFIX}test-ch"
    assert trim_call_args[1] == 0  # Start from beginning
    
    # Calculate expected keep_count
    expected_keep = settings.redis_udp_buffer_max_len - len(sample_batch.packets)
    assert trim_call_args[2] == expected_keep - 1, "LTRIM end index must be keep_count - 1"
    
    # Verify LPUSH was called after LTRIM
    mock_redis.lpush.assert_awaited_once()


async def test_push_drops_batch_when_too_large(buffer_manager, mock_redis):
    """
    Architecture §2.1: If incoming batch exceeds max buffer capacity, drop entire batch.
    Verify no push operations occur when batch is too large.
    """
    from core.config import settings
    
    # Create a batch larger than max capacity.
    # Use a fixed src_port to avoid exceeding the 65535 limit enforced by PacketMeta validation.
    large_batch = TelemetryBatch(
        channel_id="test-ch",
        timestamp=1700000000,
        sequence=100,
        window_ms=1000,
        packets=[
            PacketMeta(direction=i % 2, src_ip="10.0.0.1", dst_ip="10.0.0.2", src_port=8080, dst_port=80)
            for i in range(settings.redis_udp_buffer_max_len + 100)
        ],
    )
    
    # Buffer is at capacity
    mock_redis.llen.return_value = settings.redis_udp_buffer_max_len
    
    await buffer_manager.push_packets(large_batch)
    
    # Verify LLEN was checked
    mock_redis.llen.assert_awaited_once()
    
    # Verify LTRIM and LPUSH were NOT called (batch dropped)
    mock_redis.ltrim.assert_not_awaited()
    mock_redis.lpush.assert_not_awaited()


# --- Buffer Key Construction Tests ---

async def test_buffer_key_construction(buffer_manager, mock_redis, sample_batch):
    """
    Verify that the buffer key follows the correct prefix pattern:
    udp:buffer:{channel_id}
    """
    mock_redis.llen.return_value = 0
    
    await buffer_manager.push_packets(sample_batch)
    
    # Verify correct key format in LLEN call
    llen_call_args = mock_redis.llen.call_args[0]
    assert llen_call_args[0] == "udp:buffer:test-ch"
    assert llen_call_args[0].startswith(BUFFER_KEY_PREFIX)
    
    # Verify correct key format in LPUSH call
    lpush_call_args = mock_redis.lpush.call_args[0]
    assert lpush_call_args[0] == "udp:buffer:test-ch"


# --- Error Handling Tests ---

async def test_redis_error_wrapped(buffer_manager, mock_redis, sample_batch):
    """
    Verify that Redis errors are wrapped in RedisError to maintain
    consistent error handling across the ingestion pipeline.
    """
    # Simulate Redis failure
    mock_redis.llen.side_effect = Exception("Connection lost")
    
    with pytest.raises(RedisError) as exc_info:
        await buffer_manager.push_packets(sample_batch)
    
    assert "Buffer push failed" in str(exc_info.value)
    assert "test-ch" in str(exc_info.value)


async def test_lpush_error_wrapped(buffer_manager, mock_redis, sample_batch):
    """
    Verify that LPUSH errors are also wrapped in RedisError.
    """
    mock_redis.llen.return_value = 0
    mock_redis.lpush.side_effect = Exception("Push failed")
    
    with pytest.raises(RedisError) as exc_info:
        await buffer_manager.push_packets(sample_batch)
    
    assert "Buffer push failed" in str(exc_info.value)


# --- Timestamp Conversion Tests ---

async def test_timestamp_iso8601_conversion(buffer_manager, mock_redis, sample_batch):
    """
    Architecture §2.1: Convert batch timestamp to ISO 8601 UTC string.
    Verify correct timezone-aware datetime conversion.
    """
    mock_redis.llen.return_value = 0
    
    await buffer_manager.push_packets(sample_batch)
    
    # Extract serialized records
    call_args = mock_redis.lpush.call_args
    serialized_records = call_args[0][1:]
    record = json.loads(serialized_records[0])
    
    # Verify timestamp format
    time_str = record["time"]
    assert time_str.endswith("+00:00") or time_str.endswith("Z"), "Must be UTC timezone"
    
    # Verify it's a valid ISO 8601 datetime
    from datetime import datetime
    parsed_time = datetime.fromisoformat(time_str)
    assert parsed_time.year == 2023, "Year should match batch timestamp"


# --- Multiple Packets Serialization Tests ---

async def test_multiple_packets_serialized_correctly(buffer_manager, mock_redis):
    """
    Verify that all packets in a batch are individually serialized and pushed.
    """
    batch = TelemetryBatch(
        channel_id="test-ch",
        timestamp=1700000000,
        sequence=100,
        window_ms=1000,
        packets=[
            PacketMeta(direction=0, src_ip="192.168.1.1", dst_ip="8.8.8.8", src_port=5000, dst_port=53),
            PacketMeta(direction=1, src_ip="10.0.0.5", dst_ip="172.16.0.1", src_port=8080, dst_port=443),
            PacketMeta(direction=0, src_ip="192.168.1.100", dst_ip="1.1.1.1", src_port=6000, dst_port=123),
        ],
    )
    
    mock_redis.llen.return_value = 0
    
    await buffer_manager.push_packets(batch)
    
    # Verify all 3 packets were pushed
    call_args = mock_redis.lpush.call_args
    serialized_records = call_args[0][1:]
    assert len(serialized_records) == 3, f"Expected 3 records, got {len(serialized_records)}"
    
    # Verify each record has correct data
    for i, record_str in enumerate(serialized_records):
        record = json.loads(record_str)
        assert record["channel_id"] == "test-ch"
        assert record["direction"] == batch.packets[i].direction
        assert record["src_ip"] == str(batch.packets[i].src_ip)
        assert record["dst_ip"] == str(batch.packets[i].dst_ip)
        assert record["src_port"] == batch.packets[i].src_port
        assert record["dst_port"] == batch.packets[i].dst_port