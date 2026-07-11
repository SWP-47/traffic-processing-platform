# ==============================================================================
# CnSS Reporting Poller Unit Tests
# Validates active subscription polling, listener verification, registry retrieval,
# and Redis Pub/Sub publishing behavior against architectural specifications
# (architecture.md §2.2, §2.3).
# ==============================================================================

import json
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

from services.reporting.poller import ACTIVE_HASHES_KEY, LISTENERS_KEY_PREFIX, Poller


# --- Test Fixtures ---

@pytest.fixture
def mock_redis():
    """Provides a mocked Redis client instance for the Reporting Poller."""
    redis = AsyncMock()
    redis.smembers = AsyncMock()
    redis.get = AsyncMock()
    redis.publish = AsyncMock()
    return redis


@pytest.fixture
def mock_db_pool():
    """Provides a mocked asyncpg connection pool."""
    return MagicMock()


@pytest.fixture
def poller(mock_redis, mock_db_pool):
    """Provides a Poller instance with mocked Redis and DB dependencies."""
    with patch("services.reporting.poller.get_redis_client", return_value=mock_redis), patch(
        "services.reporting.poller.get_db_pool", return_value=mock_db_pool
    ):
        yield Poller()


@pytest.fixture
def telemetry_handler():
    """Provides a mocked subscription handler for the 'telemetry' target."""
    handler = MagicMock()
    handler.execute = AsyncMock(return_value={"data": [1, 2, 3]})
    return handler


# --- Poller Lifecycle Tests ---

async def test_tick_skips_when_no_active_hashes(poller, mock_redis):
    """
    Architecture §2.2: If no active subscription hashes exist, the Reporting Worker
    must skip SQL execution and avoid unnecessary Redis/DB activity.
    """
    mock_redis.smembers.return_value = []

    await poller._tick()

    mock_redis.smembers.assert_awaited_once_with(ACTIVE_HASHES_KEY)
    mock_redis.get.assert_not_awaited()
    mock_redis.publish.assert_not_awaited()


async def test_process_subscription_skips_when_no_listeners(poller, mock_redis):
    """
    Architecture §2.2.5: The Reporting Worker must skip SQL when a subscription has
    no active WebSocket listeners.
    """
    mock_redis.smembers.return_value = []

    await poller._process_subscription("hash-abc")

    mock_redis.smembers.assert_awaited_once_with(f"{LISTENERS_KEY_PREFIX}hash-abc")
    mock_redis.get.assert_not_awaited()
    mock_redis.publish.assert_not_awaited()


async def test_process_subscription_skips_when_registry_missing(poller, mock_redis):
    """
    Architecture §2.2.2: If the subscription hash exists but the registry entry is
    missing, the worker must skip processing and let ghost cleanup resolve it.
    """
    mock_redis.smembers.side_effect = [["client-1:sub-1"]]
    mock_redis.get.return_value = None

    await poller._process_subscription("hash-abc")

    mock_redis.get.assert_awaited_once_with("sub:registry:hash-abc")
    mock_redis.publish.assert_not_awaited()


async def test_process_subscription_skips_when_registry_json_is_invalid(poller, mock_redis):
    """
    Architecture §2.2.2: Invalid registry JSON must not crash the Reporting Worker.
    """
    mock_redis.smembers.side_effect = [["client-1:sub-1"]]
    mock_redis.get.return_value = "not-json"

    await poller._process_subscription("hash-abc")

    mock_redis.publish.assert_not_awaited()


async def test_process_subscription_skips_when_no_handler_registered(poller, mock_redis):
    """
    Architecture §2.2.3: Subscription targets without registered handlers must be
    ignored to prevent accidental SQL execution.
    """
    mock_redis.smembers.side_effect = [["client-1:sub-1"]]
    mock_redis.get.return_value = json.dumps(
        {
            "action": "subscribe",
            "id": "sub-123",
            "channel_id": "bridge-01",
            "target": "unknown_target",
            "params": {},
        }
    )

    await poller._process_subscription("hash-abc")

    mock_redis.publish.assert_not_awaited()


async def test_process_subscription_publishes_handler_result(poller, mock_redis, mock_db_pool, telemetry_handler):
    """
    Architecture §2.2.3: Active subscriptions with listeners must be routed to the
    registered handler and the result published to ws:push:{query_hash}.
    """
    poller.register_handler("telemetry", telemetry_handler)
    mock_redis.smembers.side_effect = [["client-1:sub-1"]]
    mock_redis.get.return_value = json.dumps(
        {
            "action": "subscribe",
            "id": "sub-123",
            "channel_id": "bridge-01",
            "target": "telemetry",
            "params": {},
        }
    )

    await poller._process_subscription("hash-abc")

    telemetry_handler.execute.assert_awaited_once_with(mock_db_pool, ANY)
    mock_redis.publish.assert_awaited_once()
    channel, payload = mock_redis.publish.call_args[0]
    assert channel == "ws:push:hash-abc"
    assert json.loads(payload) == {"data": [1, 2, 3]}


async def test_process_subscription_handles_handler_exception(poller, mock_redis, telemetry_handler):
    """
    Architecture §2.2.3: Handler execution failures must be caught and should not
    cause the polling task to crash.
    """
    telemetry_handler.execute.side_effect = Exception("db error")
    poller.register_handler("telemetry", telemetry_handler)
    mock_redis.smembers.side_effect = [["client-1:sub-1"]]
    mock_redis.get.return_value = json.dumps(
        {
            "action": "subscribe",
            "id": "sub-123",
            "channel_id": "bridge-01",
            "target": "telemetry",
            "params": {},
        }
    )

    await poller._process_subscription("hash-abc")

    mock_redis.publish.assert_not_awaited()
