import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch
from app.store.memory import InMemoryStateStore
from app.tasks import reporting_worker_task

@pytest.fixture
def mock_store():
    return InMemoryStateStore()

@pytest.fixture
def mock_settings():
    with patch("app.tasks.settings") as mock_s:
        mock_s.activity_timeout_ms = 5000
        mock_s.reporting_interval_sec = 1.0
        mock_s.reporting_window_sec = 3.0
        yield mock_s

async def run_reporting_iteration(store, last_seen_map, metrics=None):
    if metrics is None: metrics = {}
    with patch("app.tasks.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        mock_sleep.side_effect = [None, asyncio.CancelledError()]
        with patch("app.tasks.state_store", store):
            with patch("app.tasks.get_reporting_data", new_callable=AsyncMock, return_value=(metrics, last_seen_map)):
                with patch("app.tasks.broadcast_telemetry_update", new_callable=AsyncMock) as mock_broadcast:
                    with patch("app.tasks.get_top_hosts", new_callable=AsyncMock, return_value=[]):
                        with patch("app.tasks.broadcast_hosts_update", new_callable=AsyncMock):
                            await reporting_worker_task()
                            return mock_broadcast

@pytest.mark.asyncio
async def test_timeout_detection_broadcasts_inactive(mock_store, mock_settings):
    """
    Given a channel has not received UDP telemetry for >5000ms,
    When the reporting worker runs, Then it broadcasts is_active=false.
    """
    now = datetime.now(timezone.utc)
    await mock_store.update_channel_activity("ch-a", 1, now - timedelta(milliseconds=6000))
    await mock_store.update_channel_activity("ch-b", 1, now - timedelta(milliseconds=1000))

    last_seen_map = {
        "ch-a": now - timedelta(milliseconds=6000),
        "ch-b": now - timedelta(milliseconds=1000),
    }
    
    mock_broadcast = await run_reporting_iteration(mock_store, last_seen_map)
    
    # Проверяем, что broadcast вызывался для обоих каналов
    assert mock_broadcast.call_count == 2
    
    # Собираем аргументы вызовов
    calls = {call.kwargs["channel_id"]: call.kwargs for call in mock_broadcast.call_args_list}
    
    assert calls["ch-a"]["is_active"] is False, "Timed out channel should broadcast as inactive"
    assert calls["ch-b"]["is_active"] is True, "Active channel should broadcast as active"

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
    metrics = {"ch-metrics": {0: 150, 1: 300}}
    
    mock_broadcast = await run_reporting_iteration(mock_store, last_seen_map, metrics)
    
    mock_broadcast.assert_called_once()
    kwargs = mock_broadcast.call_args.kwargs
    assert kwargs["channel_id"] == "ch-metrics"
    assert kwargs["is_active"] is True
    assert kwargs["packets_in"] == 150
    assert kwargs["packets_out"] == 300
    assert kwargs["window_sec"] == 3.0