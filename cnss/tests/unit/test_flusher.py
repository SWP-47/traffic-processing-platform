# ==============================================================================
# CnSS Background Flusher Unit Tests
# Validates periodic buffer flushing, atomic Redis pops, JSON parsing,
# and batch database insertion against architectural specifications (§2.1).
# ==============================================================================

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.exceptions import DatabaseError, RedisError
from services.ingestion.flusher import BUFFER_KEY_PREFIX, BackgroundFlusher

# --- Test Fixtures ---


@pytest.fixture
def mock_lua_script():
    """Provides a mocked Lua script for atomic buffer pop."""
    return AsyncMock()


@pytest.fixture
def mock_db_pool():
    """Provides a mocked asyncpg connection pool with context manager support."""
    pool = AsyncMock()
    # Mock the async context manager returned by acquire()
    conn = AsyncMock()
    conn.executemany = AsyncMock()
    pool.acquire = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=conn), __aexit__=AsyncMock()))
    return pool


@pytest.fixture
def flusher(mock_lua_script, mock_db_pool):
    """Provides a BackgroundFlusher instance with mocked Redis and DB dependencies."""
    with (
        patch("services.ingestion.flusher.get_lua_script", return_value=mock_lua_script),
        patch("services.ingestion.flusher.get_db_pool", return_value=mock_db_pool),
    ):
        yield BackgroundFlusher()


# --- Channel Registration Tests ---


async def test_register_channel_adds_to_active_set(flusher):
    """
    Verify that register_channel adds the channel_id to the active set.
    """
    await flusher.register_channel("test-ch")
    assert "test-ch" in flusher._active_channels


async def test_register_channel_ignores_duplicates(flusher):
    """
    Verify that registering the same channel twice does not create duplicates (Set behavior).
    """
    await flusher.register_channel("test-ch")
    await flusher.register_channel("test-ch")
    assert len(flusher._active_channels) == 1


# --- Flush Channel Logic Tests ---


async def test_flush_channel_happy_path(flusher, mock_lua_script, mock_db_pool):
    """
    Architecture §2.1: Atomically pops records from Redis and executes batch INSERT.
    Verify that valid JSON records are parsed and passed to executemany.
    """
    # Prepare mock data with protocol field
    record1 = {
        "time": "2023-10-27T10:00:00+00:00",
        "channel_id": "test-ch",
        "direction": 0,
        "src_ip": "10.0.0.1",
        "dst_ip": "10.0.0.2",
        "src_port": 1234,
        "dst_port": 80,
        "protocol": "TCP",
        "size": 128,
    }
    record2 = {
        "time": "2023-10-27T10:00:01+00:00",
        "channel_id": "test-ch",
        "direction": 1,
        "src_ip": "10.0.0.2",
        "dst_ip": "10.0.0.1",
        "src_port": 80,
        "dst_port": 1234,
        "protocol": "UDP",
        "size": 64,
    }

    mock_lua_script.return_value = [json.dumps(record1), json.dumps(record2)]

    # Execute
    await flusher._flush_channel("test-ch")

    # Verify Lua script was called with correct key
    mock_lua_script.assert_awaited_once_with(keys=[f"{BUFFER_KEY_PREFIX}test-ch"])

    # Verify executemany was called
    conn = mock_db_pool.acquire.return_value.__aenter__.return_value
    conn.executemany.assert_awaited_once()

    # Verify parsed records
    call_args = conn.executemany.call_args
    query = call_args[0][0]
    records = call_args[0][1]

    # Verify SQL query includes protocol and size columns
    assert "INSERT INTO packet_flows" in query
    assert "protocol" in query
    assert "size" in query
    assert len(records) == 2

    # Verify first record tuple structure (now with 9 fields including protocol and size)
    t1, ch1, dir1, src1, dst1, sport1, dport1, proto1, size1 = records[0]
    assert isinstance(t1, datetime)
    assert ch1 == "test-ch"
    assert dir1 == 0
    assert src1 == "10.0.0.1"
    assert dst1 == "10.0.0.2"
    assert sport1 == 1234
    assert dport1 == 80
    assert proto1 == "TCP"
    assert size1 == 128

    # Verify second record protocol and size
    t2, ch2, dir2, src2, dst2, sport2, dport2, proto2, size2 = records[1]
    assert proto2 == "UDP"
    assert size2 == 64


async def test_flush_channel_empty_buffer(flusher, mock_lua_script, mock_db_pool):
    """
    Verify that if Redis buffer is empty, no database operations are performed.
    """
    mock_lua_script.return_value = []

    await flusher._flush_channel("test-ch")

    # Verify executemany was NOT called
    conn = mock_db_pool.acquire.return_value.__aenter__.return_value
    conn.executemany.assert_not_awaited()


async def test_flush_channel_skips_malformed_json(flusher, mock_lua_script, mock_db_pool):
    """
    Verify that malformed JSON entries are skipped, but valid ones are still processed.
    """
    valid_record = {
        "time": "2023-10-27T10:00:00+00:00",
        "channel_id": "test-ch",
        "direction": 0,
        "src_ip": "10.0.0.1",
        "dst_ip": "10.0.0.2",
        "src_port": 1234,
        "dst_port": 80,
    }

    # Mix of valid and invalid JSON
    mock_lua_script.return_value = [
        "not a json string",
        json.dumps(valid_record),
        "{malformed: json}",
    ]

    await flusher._flush_channel("test-ch")

    conn = mock_db_pool.acquire.return_value.__aenter__.return_value
    conn.executemany.assert_awaited_once()

    records = conn.executemany.call_args[0][1]
    # Only the valid record should be inserted
    assert len(records) == 1


async def test_flush_channel_skips_missing_keys(flusher, mock_lua_script, mock_db_pool):
    """
    Verify that JSON records missing required keys (e.g., 'time') are skipped.
    """
    valid_record = {
        "time": "2023-10-27T10:00:00+00:00",
        "channel_id": "test-ch",
        "direction": 0,
        "src_ip": "10.0.0.1",
        "dst_ip": "10.0.0.2",
        "src_port": 1234,
        "dst_port": 80,
    }

    incomplete_record = {
        "channel_id": "test-ch",
        # Missing 'time' and other fields
    }

    mock_lua_script.return_value = [json.dumps(incomplete_record), json.dumps(valid_record)]

    await flusher._flush_channel("test-ch")

    conn = mock_db_pool.acquire.return_value.__aenter__.return_value
    conn.executemany.assert_awaited_once()

    records = conn.executemany.call_args[0][1]
    # Only the valid record should be inserted
    assert len(records) == 1


async def test_flush_channel_handles_redis_error(flusher, mock_lua_script):
    """
    Verify that Redis errors during buffer pop are caught and logged,
    preventing the background task from crashing.
    """
    mock_lua_script.side_effect = RedisError("Connection lost")

    # Should not raise
    await flusher._flush_channel("test-ch")


async def test_flush_channel_handles_database_error(flusher, mock_lua_script, mock_db_pool):
    """
    Verify that Database errors during INSERT are caught and logged.
    """
    record = {
        "time": "2023-10-27T10:00:00+00:00",
        "channel_id": "test-ch",
        "direction": 0,
        "src_ip": "10.0.0.1",
        "dst_ip": "10.0.0.2",
        "src_port": 1234,
        "dst_port": 80,
    }
    mock_lua_script.return_value = [json.dumps(record)]

    # Simulate DB error
    conn = mock_db_pool.acquire.return_value.__aenter__.return_value
    conn.executemany.side_effect = DatabaseError("Insert failed")

    # Should not raise
    await flusher._flush_channel("test-ch")


# --- Flush All Channels Tests ---


async def test_flush_all_channels_processes_snapshot(flusher, mock_lua_script):
    """
    Verify that _flush_all_channels processes a snapshot of active channels.
    """
    await flusher.register_channel("ch-1")
    await flusher.register_channel("ch-2")

    mock_lua_script.return_value = []  # Empty buffers

    await flusher._flush_all_channels()

    # Verify Lua script was called for both channels
    assert mock_lua_script.await_count == 2
    mock_lua_script.assert_any_await(keys=[f"{BUFFER_KEY_PREFIX}ch-1"])
    mock_lua_script.assert_any_await(keys=[f"{BUFFER_KEY_PREFIX}ch-2"])


# --- Lifecycle Tests ---


async def test_start_creates_task(flusher):
    """
    Verify that start() creates an asyncio task for the flush loop.
    """
    await flusher.start()
    assert flusher._task is not None
    assert not flusher._task.done()

    # Cleanup
    await flusher.stop()


async def test_stop_cancels_task(flusher):
    """
    Verify that stop() cancels the background task gracefully.
    """
    await flusher.start()
    task = flusher._task

    await flusher.stop()

    assert task.cancelled() or task.done()
    assert flusher._task is None or flusher._task.done()


# --- Protocol Field Tests ---
async def test_flush_channel_extracts_protocol_from_json(flusher, mock_lua_script, mock_db_pool):
    """
    Verify that the protocol field is correctly extracted from JSON records
    and included in the database insert tuple.
    """
    record = {
        "time": "2023-10-27T10:00:00+00:00",
        "channel_id": "test-ch",
        "direction": 0,
        "src_ip": "10.0.0.1",
        "dst_ip": "10.0.0.2",
        "src_port": 1234,
        "dst_port": 80,
        "protocol": "ICMP",
    }

    mock_lua_script.return_value = [json.dumps(record)]

    await flusher._flush_channel("test-ch")

    conn = mock_db_pool.acquire.return_value.__aenter__.return_value
    conn.executemany.assert_awaited_once()

    records = conn.executemany.call_args[0][1]
    assert len(records) == 1

    # Verify protocol is in the tuple
    t, ch, dir_, src, dst, sport, dport, proto, size = records[0]
    assert proto == "ICMP"
    assert size == 0  # defaults to 0 since no size field in record


async def test_flush_channel_protocol_defaults_to_unknown(flusher, mock_lua_script, mock_db_pool):
    """
    Verify backward compatibility: when protocol field is missing from JSON
    (e.g., from older CN versions), it defaults to 'UNKNOWN'.
    """
    # Record WITHOUT protocol field (simulating old CN format)
    record = {
        "time": "2023-10-27T10:00:00+00:00",
        "channel_id": "test-ch",
        "direction": 0,
        "src_ip": "10.0.0.1",
        "dst_ip": "10.0.0.2",
        "src_port": 1234,
        "dst_port": 80,
        # No "protocol" field
    }

    mock_lua_script.return_value = [json.dumps(record)]

    await flusher._flush_channel("test-ch")

    conn = mock_db_pool.acquire.return_value.__aenter__.return_value
    conn.executemany.assert_awaited_once()

    records = conn.executemany.call_args[0][1]
    assert len(records) == 1

    # Verify protocol defaults to 'UNKNOWN'
    t, ch, dir_, src, dst, sport, dport, proto, size = records[0]
    assert proto == "UNKNOWN"
    assert size == 0  # defaults to 0 since no size field in record


async def test_flush_channel_sql_query_includes_protocol(flusher, mock_lua_script, mock_db_pool):
    """
    Verify that the SQL INSERT query includes the protocol column
    and has the correct number of placeholders ($1-$8).
    """
    record = {
        "time": "2023-10-27T10:00:00+00:00",
        "channel_id": "test-ch",
        "direction": 0,
        "src_ip": "10.0.0.1",
        "dst_ip": "10.0.0.2",
        "src_port": 1234,
        "dst_port": 80,
        "protocol": "TCP",
    }

    mock_lua_script.return_value = [json.dumps(record)]

    await flusher._flush_channel("test-ch")

    conn = mock_db_pool.acquire.return_value.__aenter__.return_value
    conn.executemany.assert_awaited_once()

    query = conn.executemany.call_args[0][0]

    # Verify query structure
    assert "INSERT INTO packet_flows" in query
    assert "protocol" in query
    assert "size" in query
    assert "$9" in query  # 9th placeholder for size
    assert "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)" in query
