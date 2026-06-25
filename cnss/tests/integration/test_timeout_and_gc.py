import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch
from app.store.memory import InMemoryStateStore
from app.tasks import background_timeout_and_gc_task, reporting_worker_task


@pytest.fixture
def mock_store():
    return InMemoryStateStore()


@pytest.fixture
def mock_settings():
    with patch("app.tasks.settings") as mock_s:
        mock_s.activity_timeout_ms = 5000
        mock_s.channel_retention_ms = 86400000  # 24 hours
        mock_s.reporting_interval_sec = 1.0
        mock_s.reporting_window_sec = 3.0
        yield mock_s


async def run_reporting_iteration(store, last_seen_map, metrics=None):
    """Helper to run the reporting worker for exactly one loop iteration."""
    if metrics is None:
        metrics = {}
    with patch("app.tasks.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        # First sleep passes, second raises CancelledError to break the loop
        mock_sleep.side_effect = [None, asyncio.CancelledError()]
        with patch("app.tasks.state_store", store):
            with patch(
                "app.tasks.get_reporting_data", new_callable=AsyncMock
            ) as mock_db:
                mock_db.return_value = (metrics, last_seen_map)
                with patch(
                    "app.tasks.broadcast_telemetry_update", new_callable=AsyncMock
                ) as mock_broadcast:
                    await reporting_worker_task()
                    return mock_broadcast


async def run_gc_iteration(store):
    """Helper to run the GC task for exactly one loop iteration."""
    with patch("app.tasks.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        # First sleep passes, second raises CancelledError to break the loop
        mock_sleep.side_effect = [None, asyncio.CancelledError()]
        with patch("app.tasks.state_store", store):
            await background_timeout_and_gc_task()


@pytest.mark.asyncio
async def test_timeout_detection_and_isolation(mock_store, mock_settings):
    """
    Given a channel has not received UDP telemetry for >5000ms,
    When the reporting worker runs, Then it sets is_active=false.
    Given multiple channels exist, When timeout is detected for one channel,
    Then other channels are unaffected.
    """
    now = datetime.now(timezone.utc)

    # Channel A: Timed out (6000ms > 5000ms)
    await mock_store.update_channel_activity(
        "ch-a", 1, now - timedelta(milliseconds=6000)
    )
    # Channel B: Active (1000ms < 5000ms)
    await mock_store.update_channel_activity(
        "ch-b", 1, now - timedelta(milliseconds=1000)
    )

    # Simulate DB returning last_seen timestamps
    last_seen_map = {
        "ch-a": now - timedelta(milliseconds=6000),
        "ch-b": now - timedelta(milliseconds=1000),
    }

    await run_reporting_iteration(mock_store, last_seen_map)

    ch_a = await mock_store.get_channel("ch-a")
    ch_b = await mock_store.get_channel("ch-b")

    assert ch_a is not None
    assert ch_a.is_active is False, "Timed out channel should be inactive"
    assert ch_b is not None
    assert ch_b.is_active is True, "Active channel should remain unaffected"


@pytest.mark.asyncio
async def test_broadcast_on_timeout(mock_store, mock_settings):
    """
    Given a channel's is_active changes to false,
    When the reporting worker runs, Then a telemetry_update event
    with is_active: false is pushed to all WebSocket listeners.
    """
    now = datetime.now(timezone.utc)
    await mock_store.update_channel_activity(
        "ch-timeout", 1, now - timedelta(milliseconds=6000)
    )

    # Add a mock WebSocket listener
    mock_ws = AsyncMock()
    await mock_store.add_listener("ch-timeout", mock_ws)

    last_seen_map = {"ch-timeout": now - timedelta(milliseconds=6000)}

    mock_broadcast = await run_reporting_iteration(mock_store, last_seen_map)

    # Verify broadcast was called for the timed-out channel
    mock_broadcast.assert_called_once()
    args, kwargs = mock_broadcast.call_args

    channel_id = args[0] if args else kwargs.get("channel_id")
    assert channel_id == "ch-timeout"
    assert kwargs.get("is_active") is False
    # Check that window_sec is passed correctly based on settings
    assert kwargs.get("window_sec") == 3.0


@pytest.mark.asyncio
async def test_reporting_worker_aggregates_metrics(mock_store, mock_settings):
    """
    Given the DB returns aggregated metrics for a channel,
    When the reporting worker runs, Then it passes the correct packets_in,
    packets_out, and window_sec to the broadcast function.
    """
    now = datetime.now(timezone.utc)
    await mock_store.update_channel_activity("ch-metrics", 1, now)

    last_seen_map = {"ch-metrics": now}
    # Simulate DB aggregation: 150 packets IN (direction 0), 300 packets OUT (direction 1)
    metrics = {"ch-metrics": {0: 150, 1: 300}}

    mock_broadcast = await run_reporting_iteration(mock_store, last_seen_map, metrics)

    mock_broadcast.assert_called_once()
    args, kwargs = mock_broadcast.call_args

    assert kwargs.get("channel_id") == "ch-metrics"
    assert kwargs.get("is_active") is True
    assert kwargs.get("packets_in") == 150
    assert kwargs.get("packets_out") == 300
    assert kwargs.get("window_sec") == 3.0


@pytest.mark.asyncio
async def test_garbage_collection(mock_store, mock_settings):
    """
    Given a channel has is_active=false for >24 hours AND has zero WebSocket listeners,
    When the garbage collector runs,
    Then the channel is removed from the in-memory registry.
    """
    now = datetime.now(timezone.utc)
    # Create channel and manually set it to inactive and old
    await mock_store.update_channel_activity("ch-gc", 1, now)
    await mock_store.set_channel_inactive("ch-gc")

    # Override timestamp to simulate 25 hours of inactivity
    async with mock_store._lock:
        mock_store._channels["ch-gc"].last_activity_timestamp = now - timedelta(
            hours=25
        )

    # Ensure no listeners
    assert len(await mock_store.get_listeners("ch-gc")) == 0

    await run_gc_iteration(mock_store)

    ch = await mock_store.get_channel("ch-gc")
    assert ch is None, "Channel should be garbage collected"


@pytest.mark.asyncio
async def test_gc_not_triggered_with_listeners(mock_store, mock_settings):
    """
    GC should NOT remove the channel if it has active listeners.
    """
    now = datetime.now(timezone.utc)
    await mock_store.update_channel_activity("ch-gc-listeners", 1, now)
    await mock_store.set_channel_inactive("ch-gc-listeners")

    async with mock_store._lock:
        mock_store._channels["ch-gc-listeners"].last_activity_timestamp = (
            now - timedelta(hours=25)
        )

    # Add a listener
    mock_ws = AsyncMock()
    await mock_store.add_listener("ch-gc-listeners", mock_ws)

    await run_gc_iteration(mock_store)

    ch = await mock_store.get_channel("ch-gc-listeners")
    assert ch is not None, "Channel with listeners should NOT be garbage collected"
