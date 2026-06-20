import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch
from app.store.memory import InMemoryStateStore
from app.tasks import background_timeout_and_gc_task


@pytest.fixture
def mock_store():
    return InMemoryStateStore()


@pytest.fixture
def mock_settings():
    with patch("app.tasks.settings") as mock_s:
        mock_s.activity_timeout_ms = 5000
        mock_s.channel_retention_ms = 86400000  # 24 hours
        yield mock_s


async def run_single_iteration(store):
    """Helper to run the background task for exactly one loop iteration."""
    with patch("app.tasks.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        # First sleep passes, second raises CancelledError to break the loop
        mock_sleep.side_effect = [None, asyncio.CancelledError()]

        with patch("app.tasks.state_store", store):
            with patch(
                "app.tasks.broadcast_telemetry_update", new_callable=AsyncMock
            ) as mock_broadcast:
                # The task catches CancelledError internally and breaks gracefully,
                # so it returns normally instead of raising the exception.
                await background_timeout_and_gc_task()
                return mock_broadcast


@pytest.mark.asyncio
async def test_timeout_detection_and_isolation(mock_store, mock_settings):
    """
    Given a channel has not received UDP telemetry for >5000ms,
        When the timeout checker runs, Then it sets is_active=false.
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

    await run_single_iteration(mock_store)

    ch_a = await mock_store.get_channel("ch-a")
    ch_b = await mock_store.get_channel("ch-b")

    assert ch_a is not None
    assert ch_a.is_active is False, "AC 1 Failed: Timed out channel should be inactive"

    assert ch_b is not None
    assert (
        ch_b.is_active is True
    ), "AC 3 Failed: Active channel should remain unaffected"


@pytest.mark.asyncio
async def test_broadcast_on_timeout(mock_store, mock_settings):
    """
    Given a channel's is_active changes to false,
        When the state update occurs, Then a telemetry_update event
        with is_active: false is pushed to all WebSocket listeners.
    """
    now = datetime.now(timezone.utc)
    await mock_store.update_channel_activity(
        "ch-timeout", 1, now - timedelta(milliseconds=6000)
    )

    # Add a mock WebSocket listener
    mock_ws = AsyncMock()
    await mock_store.add_listener("ch-timeout", mock_ws)

    mock_broadcast = await run_single_iteration(mock_store)

    # Verify broadcast was called for the timed-out channel
    mock_broadcast.assert_called_once()
    args, kwargs = mock_broadcast.call_args

    # Check arguments (channel_id can be positional or kwarg depending on implementation)
    channel_id = args[0] if args else kwargs.get("channel_id")
    assert channel_id == "ch-timeout"
    assert kwargs.get("is_active") is False


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

    await run_single_iteration(mock_store)

    ch = await mock_store.get_channel("ch-gc")
    assert ch is None, "AC 4 Failed: Channel should be garbage collected"


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

    await run_single_iteration(mock_store)

    ch = await mock_store.get_channel("ch-gc-listeners")
    assert (
        ch is not None
    ), "AC 4 Negative Failed: Channel with listeners should NOT be garbage collected"
