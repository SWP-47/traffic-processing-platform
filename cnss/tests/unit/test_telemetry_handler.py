# ==============================================================================
# CnSS Telemetry Handler Unit Tests
# Validates SQL execution, metric calculation, and edge case handling for the
# 'telemetry' subscription target against a mocked asyncpg database pool.
# ==============================================================================

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone
import asyncpg

from core.contracts.subscriptions import SubscribeRequest, SubscriptionParams
from core.exceptions import DatabaseError
from services.reporting.handlers.telemetry_handler import TelemetryHandler

# --- Test Fixtures ---

@pytest.fixture
def mock_conn():
    """Provides a mocked asyncpg connection with context manager support."""
    conn = AsyncMock()
    # Mock the async context manager behavior for acquire()
    conn.__aenter__ = AsyncMock(return_value=conn)
    conn.__aexit__ = AsyncMock(return_value=None)
    return conn

@pytest.fixture
def mock_db_pool(mock_conn):
    """Provides a mocked asyncpg connection pool."""
    pool = MagicMock()
    # Inject the mocked connection into the pool's acquire method
    pool.acquire = MagicMock(return_value=mock_conn)
    return pool

@pytest.fixture
def handler():
    """Provides a TelemetryHandler instance."""
    return TelemetryHandler()

@pytest.fixture
def valid_request():
    """Provides a valid SubscribeRequest for telemetry."""
    return SubscribeRequest(
        action="subscribe",
        id="sub-123",
        channel_id="bridge-01",
        target="telemetry",
        params=SubscriptionParams(window_sec=5.0),
    )

# --- Successful Execution Tests ---

async def test_execute_success_with_data(handler, mock_db_pool, mock_conn, valid_request):
    """
    Verify that valid telemetry data is correctly aggregated and formatted.
    Tests rate calculation using actual bucket count instead of requested window.
    """
    # Simulate database returning 5 buckets with traffic
    mock_conn.fetchrow = AsyncMock(return_value={
        "is_active": True,
        "dropped": 10,
        "total_in": 500,
        "total_out": 300,
        "bucket_count": 5,
        "latest_bucket": datetime(2026, 7, 9, 12, 0, 5, tzinfo=timezone.utc),
    })
    
    result = await handler.execute(mock_db_pool, valid_request)
    
    # Verify SQL query was executed with correct parameters
    mock_conn.fetchrow.assert_awaited_once()
    query_args = mock_conn.fetchrow.call_args[0]
    assert query_args[1] == 5.0  # window_sec
    assert query_args[2] == "bridge-01"  # channel_id
    
    # Verify payload structure and accurate rate calculation (500 / 5 = 100 pps)
    assert result["type"] == "telemetry_update"
    assert result["channel_id"] == "bridge-01"
    assert result["is_active"] is True
    assert result["dropped_batches"] == 10
    assert result["metrics"]["direction_in"]["packets"] == 500
    assert result["metrics"]["direction_in"]["packets_per_sec"] == 100
    assert result["metrics"]["direction_out"]["packets"] == 300
    assert result["metrics"]["direction_out"]["packets_per_sec"] == 60
    assert result["window_ms"] == 5000

# --- Edge Case & Empty Data Tests ---

async def test_execute_channel_not_found(handler, mock_db_pool, mock_conn, valid_request):
    """
    Verify that None is returned when the channel does not exist in the registry.
    """
    # Simulate missing channel in the database
    mock_conn.fetchrow = AsyncMock(return_value=None)
    
    result = await handler.execute(mock_db_pool, valid_request)
    
    assert result is None

async def test_execute_no_buckets_found(handler, mock_db_pool, mock_conn, valid_request):
    """
    Verify that zero rates are returned when no time buckets match the window.
    """
    # Simulate empty aggregation result (channel exists but no traffic in window)
    mock_conn.fetchrow = AsyncMock(return_value={
        "is_active": False,
        "dropped": 0,
        "total_in": 0,
        "total_out": 0,
        "bucket_count": 0,
        "latest_bucket": None,
    })
    
    result = await handler.execute(mock_db_pool, valid_request)
    
    # Verify zero rates and fallback timestamp generation
    assert result["metrics"]["direction_in"]["packets_per_sec"] == 0
    assert result["metrics"]["direction_out"]["packets_per_sec"] == 0
    assert result["window_ms"] == 0
    assert "received_at" in result

async def test_execute_window_sec_below_minimum(handler, mock_db_pool, mock_conn):
    """
    Verify that window_sec below the minimum threshold defaults to 1.0 second.
    Prevents division by zero or invalid interval queries.
    """
    # Request with invalid window size
    invalid_request = SubscribeRequest(
        action="subscribe",
        id="sub-123",
        channel_id="bridge-01",
        target="telemetry",
        params=SubscriptionParams(window_sec=0.05),
    )
    
    mock_conn.fetchrow = AsyncMock(return_value={
        "is_active": True,
        "dropped": 0,
        "total_in": 10,
        "total_out": 10,
        "bucket_count": 1,
        "latest_bucket": datetime.now(timezone.utc),
    })
    
    await handler.execute(mock_db_pool, invalid_request)
    
    # Verify the query was executed with the default 1.0s window instead of 0.05
    query_args = mock_conn.fetchrow.call_args[0]
    assert query_args[1] == 1.0

# --- Error Handling Tests ---

async def test_execute_database_error(handler, mock_db_pool, mock_conn, valid_request):
    """
    Verify that asyncpg PostgresError is caught and wrapped in DatabaseError.
    """
    # Simulate a database connection failure
    mock_conn.fetchrow = AsyncMock(side_effect=asyncpg.PostgresError("Connection lost"))
    
    with pytest.raises(DatabaseError) as exc_info:
        await handler.execute(mock_db_pool, valid_request)
        
    assert "Telemetry query failed" in str(exc_info.value)

async def test_execute_unexpected_error(handler, mock_db_pool, mock_conn, valid_request):
    """
    Verify that unexpected exceptions are caught and wrapped in DatabaseError.
    """
    # Simulate an unexpected runtime error during query execution
    mock_conn.fetchrow = AsyncMock(side_effect=ValueError("Unexpected parsing error"))
    
    with pytest.raises(DatabaseError) as exc_info:
        await handler.execute(mock_db_pool, valid_request)
        
    assert "Unexpected telemetry query failure" in str(exc_info.value)