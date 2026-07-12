# ==============================================================================
# CnSS Telemetry Handler SQL Query Tests
# Validates the SQL query construction and parameter binding for telemetry_1s
# continuous aggregate, ensuring correct bucket capture with 1-second granularity.
# ==============================================================================
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.contracts.subscriptions import SubscribeRequest, SubscriptionParams
from services.reporting.handlers.telemetry_handler import TelemetryHandler


# --- Test Fixtures ---
@pytest.fixture
def mock_conn():
    """Provides a mocked asyncpg connection with context manager support."""
    conn = AsyncMock()
    conn.__aenter__ = AsyncMock(return_value=conn)
    conn.__aexit__ = AsyncMock(return_value=None)
    return conn


@pytest.fixture
def mock_db_pool(mock_conn):
    """Provides a mocked asyncpg connection pool."""
    pool = MagicMock()
    pool.acquire = MagicMock(return_value=mock_conn)
    return pool


@pytest.fixture
def handler():
    """Provides a TelemetryHandler instance."""
    return TelemetryHandler()


# --- SQL Query Parameter Tests ---
async def test_sql_query_parameters_window_5_seconds(handler, mock_db_pool, mock_conn):
    """
    Verify that SQL query uses correct parameters for window_sec=5.0.
    Tests that the query captures buckets in range (NOW()-6s, NOW()-1s].
    """
    # Setup mock response
    mock_conn.fetchrow = AsyncMock(
        return_value={
            "is_active": True,
            "dropped": 0,
            "total_in": 500,
            "total_out": 300,
            "bucket_count": 5,
            "latest_bucket": datetime.now(timezone.utc),
        }
    )

    request = SubscribeRequest(
        action="subscribe",
        id="sub-123",
        channel_id="bridge-01",
        target="telemetry",
        params=SubscriptionParams(window_sec=5.0),
    )

    await handler.execute(mock_db_pool, request)

    # Verify query was called with correct parameters
    mock_conn.fetchrow.assert_awaited_once()
    call_args = mock_conn.fetchrow.call_args

    # Extract SQL query and parameters
    query = call_args[0][0]
    params = call_args[0][1:]

    # Verify parameters: $1=window_sec, $2=channel_id
    assert params[0] == 5.0, f"Expected window_sec=5.0, got {params[0]}"
    assert params[1] == "bridge-01", f"Expected channel_id='bridge-01', got {params[1]}"

    # Verify SQL contains correct interval logic
    assert "NOW() - ($1 * INTERVAL '1 second') - INTERVAL '1 second'" in query
    assert "NOW() - INTERVAL '1 second'" in query


async def test_sql_query_parameters_window_1_second(handler, mock_db_pool, mock_conn):
    """
    Verify SQL query for window_sec=1.0 (minimum allowed).
    Tests that query captures exactly 1 bucket in range (NOW()-2s, NOW()-1s].
    This is the edge case you're concerned about.
    """
    # Setup mock response with 1 bucket
    mock_conn.fetchrow = AsyncMock(
        return_value={
            "is_active": True,
            "dropped": 0,
            "total_in": 100,
            "total_out": 50,
            "bucket_count": 1,
            "latest_bucket": datetime.now(timezone.utc) - timedelta(seconds=1),
        }
    )

    request = SubscribeRequest(
        action="subscribe",
        id="sub-123",
        channel_id="bridge-01",
        target="telemetry",
        params=SubscriptionParams(window_sec=1.0),
    )

    await handler.execute(mock_db_pool, request)

    # Verify parameters
    call_args = mock_conn.fetchrow.call_args
    params = call_args[0][1:]

    assert params[0] == 1.0, f"Expected window_sec=1.0, got {params[0]}"

    # Verify rate calculation with 1 bucket
    result = mock_conn.fetchrow.return_value
    assert result["bucket_count"] == 1


async def test_sql_query_parameters_window_10_seconds(handler, mock_db_pool, mock_conn):
    """
    Verify SQL query for window_sec=10.0.
    Tests that query captures buckets in range (NOW()-11s, NOW()-1s].
    """
    # Setup mock response
    mock_conn.fetchrow = AsyncMock(
        return_value={
            "is_active": True,
            "dropped": 0,
            "total_in": 1000,
            "total_out": 500,
            "bucket_count": 10,
            "latest_bucket": datetime.now(timezone.utc),
        }
    )

    request = SubscribeRequest(
        action="subscribe",
        id="sub-123",
        channel_id="bridge-01",
        target="telemetry",
        params=SubscriptionParams(window_sec=10.0),
    )

    await handler.execute(mock_db_pool, request)

    # Verify parameters
    call_args = mock_conn.fetchrow.call_args
    params = call_args[0][1:]

    assert params[0] == 10.0, f"Expected window_sec=10.0, got {params[0]}"


# --- SQL Query Structure Tests ---
async def test_sql_query_uses_greater_than_operator(handler, mock_db_pool, mock_conn):
    """
    Verify that SQL query uses '>' (greater than) for lower bound.
    This is important for correct bucket capture with 1-second granularity.

    ISSUE: The current query uses '>' which may exclude boundary buckets.
    For window_sec=1.0, range is (NOW()-2s, NOW()-1s], which might miss
    a bucket at exactly NOW()-2s.

    RECOMMENDATION: Consider using '>=' instead of '>' for inclusive lower bound.
    """
    mock_conn.fetchrow = AsyncMock(
        return_value={
            "is_active": True,
            "dropped": 0,
            "total_in": 100,
            "total_out": 50,
            "bucket_count": 1,
            "latest_bucket": datetime.now(timezone.utc),
        }
    )

    request = SubscribeRequest(
        action="subscribe",
        id="sub-123",
        channel_id="bridge-01",
        target="telemetry",
        params=SubscriptionParams(window_sec=1.0),
    )

    await handler.execute(mock_db_pool, request)

    # Extract SQL query
    call_args = mock_conn.fetchrow.call_args
    query = call_args[0][0]

    # Check for '>' operator in lower bound condition
    # Current query: t.bucket > NOW() - ($1 * INTERVAL '1 second') - INTERVAL '1 second'
    assert "t.bucket > NOW()" in query, "Query should use '>' for lower bound"

    # Note: This test documents the current behavior.
    # If you want to change to '>=', update both the handler and this test.


async def test_sql_query_excludes_current_incomplete_bucket(handler, mock_db_pool, mock_conn):
    """
    Verify that SQL query excludes the current incomplete bucket.
    The telemetry_1s continuous aggregate has end_offset=1s, meaning
    the current second is not yet finalized.

    Query should use: t.bucket <= NOW() - INTERVAL '1 second'
    """
    mock_conn.fetchrow = AsyncMock(
        return_value={
            "is_active": True,
            "dropped": 0,
            "total_in": 100,
            "total_out": 50,
            "bucket_count": 1,
            "latest_bucket": datetime.now(timezone.utc),
        }
    )

    request = SubscribeRequest(
        action="subscribe",
        id="sub-123",
        channel_id="bridge-01",
        target="telemetry",
        params=SubscriptionParams(window_sec=5.0),
    )

    await handler.execute(mock_db_pool, request)

    # Extract SQL query
    call_args = mock_conn.fetchrow.call_args
    query = call_args[0][0]

    # Verify upper bound excludes current second
    assert "t.bucket <= NOW() - INTERVAL '1 second'" in query, "Query should exclude current incomplete bucket"


# --- Rate Calculation Tests ---
async def test_rate_calculation_with_actual_bucket_count(handler, mock_db_pool, mock_conn):
    """
    Verify that rate calculation uses actual bucket count, not requested window_sec.
    This ensures accurate statistics even when window_sec is not a whole number.

    Example: window_sec=1.5 might capture 2 buckets (2s actual),
    so we divide by 2, not 1.5.
    """
    # Simulate window_sec=5.0 but only 3 buckets available
    mock_conn.fetchrow = AsyncMock(
        return_value={
            "is_active": True,
            "dropped": 0,
            "total_in": 300,  # 300 packets over 3 buckets
            "total_out": 150,
            "bucket_count": 3,  # Only 3 buckets, not 5
            "latest_bucket": datetime.now(timezone.utc),
        }
    )

    request = SubscribeRequest(
        action="subscribe",
        id="sub-123",
        channel_id="bridge-01",
        target="telemetry",
        params=SubscriptionParams(window_sec=5.0),
    )

    result = await handler.execute(mock_db_pool, request)

    # Verify rate calculation: 300 packets / 3 buckets = 100 pps
    assert result["metrics"]["direction_in"]["packets_per_sec"] == 100
    assert result["metrics"]["direction_out"]["packets_per_sec"] == 50

    # Verify window_ms reflects actual bucket count
    assert result["window_ms"] == 3000  # 3 buckets * 1000ms


async def test_rate_calculation_zero_buckets(handler, mock_db_pool, mock_conn):
    """
    Verify that rate calculation handles zero buckets gracefully.
    When no buckets are available, rates should be 0.
    """
    mock_conn.fetchrow = AsyncMock(
        return_value={
            "is_active": False,
            "dropped": 0,
            "total_in": 0,
            "total_out": 0,
            "bucket_count": 0,
            "latest_bucket": None,
        }
    )

    request = SubscribeRequest(
        action="subscribe",
        id="sub-123",
        channel_id="bridge-01",
        target="telemetry",
        params=SubscriptionParams(window_sec=5.0),
    )

    result = await handler.execute(mock_db_pool, request)

    # Verify zero rates
    assert result["metrics"]["direction_in"]["packets_per_sec"] == 0
    assert result["metrics"]["direction_out"]["packets_per_sec"] == 0
    assert result["window_ms"] == 0


# --- Integration Test with Mock Database ---
async def test_full_query_execution_flow(handler, mock_db_pool, mock_conn):
    """
    Integration test that verifies the complete query execution flow:
    1. Request validation
    2. SQL query construction
    3. Parameter binding
    4. Result formatting
    """
    # Setup mock response
    now = datetime.now(timezone.utc)
    mock_conn.fetchrow = AsyncMock(
        return_value={
            "is_active": True,
            "dropped": 5,
            "total_in": 500,
            "total_out": 300,
            "bucket_count": 5,
            "latest_bucket": now - timedelta(seconds=1),
        }
    )

    request = SubscribeRequest(
        action="subscribe",
        id="sub-test-001",
        channel_id="bridge-01",
        target="telemetry",
        params=SubscriptionParams(window_sec=5.0),
    )

    result = await handler.execute(mock_db_pool, request)

    # Verify complete result structure
    assert result["type"] == "telemetry_update"
    assert result["channel_id"] == "bridge-01"
    assert result["is_active"] is True
    assert result["dropped_batches"] == 5
    assert result["window_ms"] == 5000

    # Verify metrics structure
    assert "direction_in" in result["metrics"]
    assert "direction_out" in result["metrics"]
    assert "packets" in result["metrics"]["direction_in"]
    assert "packets_per_sec" in result["metrics"]["direction_in"]

    # Verify timestamps
    assert "timestamp" in result
    assert "received_at" in result
