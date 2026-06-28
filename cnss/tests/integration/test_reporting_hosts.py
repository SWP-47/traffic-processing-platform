import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock
from app.store import StateStore as InMemoryStateStore
from app.models import WSClientSession
from app.tasks import reporting_worker_task


@pytest.fixture
def mock_store():
    return InMemoryStateStore()


@pytest.fixture
def mock_settings():
    with patch("app.tasks.settings") as mock_s:
        mock_s.activity_timeout_ms = 5000
        mock_s.channel_retention_ms = 86400000
        mock_s.reporting_interval_sec = 1.0
        mock_s.reporting_window_sec = 3.0
        yield mock_s


async def run_reporting_iteration(store, last_seen_map, metrics=None):
    """Helper to run the reporting worker for exactly one loop iteration."""
    if metrics is None:
        metrics = {}
    with patch("app.tasks.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        mock_sleep.side_effect = [None, asyncio.CancelledError()]
        with patch("app.tasks.state_store", store):
            with patch(
                "app.tasks.get_reporting_data",
                new_callable=AsyncMock,
                return_value=(metrics, last_seen_map),
            ):
                with patch(
                    "app.tasks.broadcast_telemetry_update", new_callable=AsyncMock
                ):
                    with patch(
                        "app.tasks.get_top_hosts",
                        new_callable=AsyncMock,
                        return_value=[],
                    ) as mock_hosts_db:
                        with patch(
                            "app.tasks.broadcast_hosts_update", new_callable=AsyncMock
                        ) as mock_broadcast_hosts:
                            await reporting_worker_task()
                            return mock_hosts_db, mock_broadcast_hosts


@pytest.mark.asyncio
async def test_reporting_worker_skips_db_query_when_no_subscribers(
    mock_store, mock_settings
):
    """
    Given zero subscribers for a target,
    When the reporting worker runs,
    Then the heavy DB query for that target is completely skipped.
    """
    now = datetime.now(timezone.utc)
    await mock_store.update_channel_activity("ch-no-subs", 1, now)
    last_seen_map = {"ch-no-subs": now}

    mock_hosts_db, mock_broadcast_hosts = await run_reporting_iteration(
        mock_store, last_seen_map
    )

    # get_top_hosts should NOT have been called
    mock_hosts_db.assert_not_called()
    mock_broadcast_hosts.assert_not_called()


@pytest.mark.asyncio
async def test_reporting_worker_queries_and_broadcasts_when_subscribers_exist(
    mock_store, mock_settings
):
    """
    Given active subscribers,
    When the reporting worker runs,
    Then it queries the DB and broadcasts the update ONLY to subscribed sessions.
    """
    now = datetime.now(timezone.utc)
    await mock_store.update_channel_activity("ch-with-subs", 1, now)
    last_seen_map = {"ch-with-subs": now}

    # Create a mock session with a subscription
    mock_ws = AsyncMock()
    session = WSClientSession(
        websocket=mock_ws, user=MagicMock(), channel_id="ch-with-subs"
    )
    session.subscriptions["lan_hosts"] = {"sort_by": "sent", "limit": 5}
    await mock_store.add_listener("ch-with-subs", session)

    mock_hosts = [
        {
            "ip": "10.0.0.1",
            "sent_per_sec": 100.0,
            "received_per_sec": 50.0,
            "last_seen": now.isoformat(),
        }
    ]

    with patch("app.tasks.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        mock_sleep.side_effect = [None, asyncio.CancelledError()]
        with patch("app.tasks.state_store", mock_store):
            with patch(
                "app.tasks.get_reporting_data",
                new_callable=AsyncMock,
                return_value=({}, last_seen_map),
            ):
                with patch(
                    "app.tasks.broadcast_telemetry_update", new_callable=AsyncMock
                ):
                    with patch(
                        "app.tasks.get_top_hosts",
                        new_callable=AsyncMock,
                        return_value=mock_hosts,
                    ) as mock_hosts_db:
                        with patch(
                            "app.tasks.broadcast_hosts_update", new_callable=AsyncMock
                        ) as mock_broadcast_hosts:
                            await reporting_worker_task()

                            # Verify DB was queried with correct parameters
                            mock_hosts_db.assert_called_once()
                            args, kwargs = mock_hosts_db.call_args
                            assert kwargs["channel_id"] == "ch-with-subs"
                            assert kwargs["target"] == "lan_hosts"
                            assert kwargs["sort_by"] == "sent"
                            assert kwargs["limit"] == 5

                            # Verify broadcast was called with the correct sessions
                            mock_broadcast_hosts.assert_called_once()
                            b_args, b_kwargs = mock_broadcast_hosts.call_args
                            assert b_kwargs["channel_id"] == "ch-with-subs"
                            assert b_kwargs["target"] == "lan_hosts"
                            assert session in b_kwargs["sessions"]
