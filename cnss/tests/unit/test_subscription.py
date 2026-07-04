# ==============================================================================
# CnSS WebSocket Subscription Manager Unit Tests
# Validates subscription registration, listener tracking, and cleanup logic
# against architectural specifications (architecture.md §2.3, §4.2).
# ==============================================================================

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from core.exceptions import RedisError
from services.websocket.subscription import (
    ACTIVE_HASHES_KEY,
    LISTENERS_KEY_PREFIX,
    PUSH_CHANNEL_PREFIX,
    REGISTRY_KEY_PREFIX,
    SubscriptionManager,
)


# --- Test Fixtures ---

@pytest.fixture
def mock_redis():
    """Provides a mocked Redis client instance with pipeline support."""
    redis = AsyncMock()
    # Pipeline commands are SYNCHRONOUS in redis.asyncio and return the pipeline for chaining.
    # Only pipeline.execute() is async.
    pipeline = MagicMock()
    pipeline.set = MagicMock(return_value=pipeline)
    pipeline.sadd = MagicMock(return_value=pipeline)
    pipeline.srem = MagicMock(return_value=pipeline)
    pipeline.delete = MagicMock(return_value=pipeline)
    pipeline.execute = AsyncMock(return_value=[])
    redis.pipeline = MagicMock(return_value=pipeline)
    # Async methods used directly (not in pipeline)
    redis.scard = AsyncMock(return_value=1)
    return redis


@pytest.fixture
def mock_session():
    """Provides a mocked Session instance."""
    session = AsyncMock()
    session.client_id = "client-uuid-123"
    session.add_subscription = AsyncMock()
    session.remove_subscription = AsyncMock()
    return session


@pytest.fixture
def mock_request():
    """Provides a mocked SubscribeRequest instance."""
    request = MagicMock()
    request.query_hash = "abc123def456"
    request.channel_id = "bridge-01"
    request.id = "sub-abc-123"
    request.target = "telemetry"
    request.model_dump_json = MagicMock(return_value='{"action":"subscribe","id":"sub-abc-123"}')
    return request


@pytest.fixture
def manager(mock_redis):
    """Provides a SubscriptionManager instance with a mocked Redis client."""
    with patch("services.websocket.subscription.get_redis_client", return_value=mock_redis):
        yield SubscriptionManager()


# --- Key Construction Tests ---

def test_registry_key_format(manager):
    """
    Architecture §3.2: Registry key must follow 'sub:registry:{query_hash}' pattern.
    """
    key = manager._get_registry_key("abc123")
    assert key == "sub:registry:abc123"
    assert key.startswith(REGISTRY_KEY_PREFIX)


def test_listeners_key_format(manager):
    """
    Architecture §3.2: Listeners key must follow 'sub:listeners:{query_hash}' pattern.
    """
    key = manager._get_listeners_key("abc123")
    assert key == "sub:listeners:abc123"
    assert key.startswith(LISTENERS_KEY_PREFIX)


def test_push_channel_format(manager):
    """
    Architecture §3.2: Pub/Sub channel must follow 'ws:push:{query_hash}' pattern.
    """
    channel = manager._get_push_channel("abc123")
    assert channel == "ws:push:abc123"
    assert channel.startswith(PUSH_CHANNEL_PREFIX)


# --- Subscribe Success Tests ---

async def test_subscribe_registers_in_redis(manager, mock_redis, mock_session, mock_request):
    """
    Architecture §2.3.3: subscribe() must atomically:
    1. Write registry with SET NX (no overwrite).
    2. Add composite 'client_id:sub_id' to listeners set.
    3. Index hash in active_hashes set.
    4. Track subscription in the client's session.
    """
    query_hash, push_channel = await manager.subscribe(mock_session, mock_request)

    assert query_hash == "abc123def456"
    assert push_channel == "ws:push:abc123def456"

    # Verify pipeline was created with transaction=False
    mock_redis.pipeline.assert_called_once_with(transaction=False)
    pipeline = mock_redis.pipeline.return_value

    # Verify SET NX was called with serialized request
    pipeline.set.assert_called_once()
    set_args = pipeline.set.call_args[0]
    assert set_args[0] == "sub:registry:abc123def456"
    assert set_args[1] == mock_request.model_dump_json()
    # nx is passed as a keyword argument, so we check it via .kwargs
    assert pipeline.set.call_args.kwargs["nx"] is True

    # Verify composite listener member was added
    pipeline.sadd.assert_any_call("sub:listeners:abc123def456", "client-uuid-123:sub-abc-123")

    # Verify hash was indexed in active_hashes
    pipeline.sadd.assert_any_call(ACTIVE_HASHES_KEY, "abc123def456")

    # Verify pipeline was executed
    pipeline.execute.assert_awaited_once()

    # Verify session tracking was updated
    mock_session.add_subscription.assert_awaited_once_with("abc123def456", "sub-abc-123")


async def test_subscribe_uses_nx_to_prevent_overwrite(manager, mock_redis, mock_session, mock_request):
    """
    Architecture §3.2: Registry key has NO TTL and must not be overwritten
    when multiple clients subscribe to the same query_hash.
    SET NX ensures the first subscription's JSON is preserved.
    """
    await manager.subscribe(mock_session, mock_request)

    pipeline = mock_redis.pipeline.return_value
    # The 'nx' keyword argument must be True to prevent overwriting existing registry
    assert pipeline.set.call_args.kwargs["nx"] is True, "SET must use NX flag to prevent overwriting existing registry"


async def test_subscribe_listener_member_is_composite(manager, mock_redis, mock_session, mock_request):
    """
    Architecture §3.2: Listener set stores composite 'client_id:sub_id' to allow
    a single client to maintain multiple parallel subscriptions to the same query_hash.
    """
    await manager.subscribe(mock_session, mock_request)

    pipeline = mock_redis.pipeline.return_value
    # Find the SADD call for the listeners key
    for call in pipeline.sadd.call_args_list:
        args = call[0]
        if args[0] == "sub:listeners:abc123def456":
            member = args[1]
            # Must be composite: client_id:sub_id
            assert ":" in member
            client_id, sub_id = member.rsplit(":", 1)
            assert client_id == "client-uuid-123"
            assert sub_id == "sub-abc-123"
            break
    else:
        pytest.fail("SADD was not called for the listeners key")


# --- Subscribe Error Handling Tests ---

async def test_subscribe_wraps_redis_error(manager, mock_redis, mock_session, mock_request):
    """
    Verify that Redis errors during subscription are wrapped in RedisError
    to maintain consistent error handling across the WebSocket service.
    """
    pipeline = mock_redis.pipeline.return_value
    pipeline.execute.side_effect = Exception("Connection lost")

    with pytest.raises(RedisError) as exc_info:
        await manager.subscribe(mock_session, mock_request)

    assert "Subscription registration failed" in str(exc_info.value)
    assert "client-uuid-123" in str(exc_info.value)


# --- Unsubscribe Success Tests ---

async def test_unsubscribe_removes_listener(manager, mock_redis, mock_session, mock_request):
    """
    Architecture §4.4: unsubscribe() must remove 'client_id:sub_id' from the listeners set
    and update the session tracking.
    """
    # Other listeners still remain (scard > 0)
    mock_redis.scard.return_value = 2

    query_hash = await manager.unsubscribe(mock_session, mock_request)

    assert query_hash == "abc123def456"

    # Verify SREM was called with composite member
    mock_redis.srem.assert_awaited_once_with(
        "sub:listeners:abc123def456",
        "client-uuid-123:sub-abc-123",
    )

    # Verify session tracking was updated
    mock_session.remove_subscription.assert_awaited_once_with("abc123def456", "sub-abc-123")

    # Verify pipeline was NOT created (other listeners remain)
    mock_redis.pipeline.assert_not_called()


async def test_unsubscribe_last_listener_cleans_up(manager, mock_redis, mock_session, mock_request):
    """
    Architecture §4.4: When the last listener unsubscribes, the manager must:
    1. Delete the registry key (stop Reporting Worker from querying DB).
    2. Delete the listeners key.
    3. Remove the hash from active_hashes.
    This prevents unnecessary SQL execution for abandoned subscriptions.
    """
    # Last listener removed (scard == 0)
    mock_redis.scard.return_value = 0

    await manager.unsubscribe(mock_session, mock_request)

    # Verify SREM was called first
    mock_redis.srem.assert_awaited_once_with(
        "sub:listeners:abc123def456",
        "client-uuid-123:sub-abc-123",
    )

    # Verify cleanup pipeline was created
    mock_redis.pipeline.assert_called_once_with(transaction=False)
    pipeline = mock_redis.pipeline.return_value

    # Verify registry key deletion
    pipeline.delete.assert_any_call("sub:registry:abc123def456")
    # Verify listeners key deletion
    pipeline.delete.assert_any_call("sub:listeners:abc123def456")
    # Verify active_hashes removal
    pipeline.srem.assert_called_once_with(ACTIVE_HASHES_KEY, "abc123def456")

    # Verify pipeline was executed
    pipeline.execute.assert_awaited_once()

    # Verify session tracking was still updated
    mock_session.remove_subscription.assert_awaited_once_with("abc123def456", "sub-abc-123")


# --- Unsubscribe Error Handling Tests ---

async def test_unsubscribe_wraps_redis_error(manager, mock_redis, mock_session, mock_request):
    """
    Verify that Redis errors during unsubscription are wrapped in RedisError.
    """
    mock_redis.srem.side_effect = Exception("Connection lost")

    with pytest.raises(RedisError) as exc_info:
        await manager.unsubscribe(mock_session, mock_request)

    assert "Subscription unregistration failed" in str(exc_info.value)
    assert "client-uuid-123" in str(exc_info.value)


async def test_unsubscribe_wraps_cleanup_pipeline_error(manager, mock_redis, mock_session, mock_request):
    """
    Verify that Redis errors during cleanup pipeline execution are wrapped in RedisError.
    """
    mock_redis.scard.return_value = 0
    pipeline = mock_redis.pipeline.return_value
    pipeline.execute.side_effect = Exception("Pipeline failed")

    with pytest.raises(RedisError) as exc_info:
        await manager.unsubscribe(mock_session, mock_request)

    assert "Subscription unregistration failed" in str(exc_info.value)


# --- Active Hashes Index Tests ---

async def test_subscribe_indexes_hash_in_active_set(manager, mock_redis, mock_session, mock_request):
    """
    Architecture §3.2: The active_hashes set replaces the blocking KEYS command,
    providing O(1) lookup for the Reporting Worker to discover active subscriptions.
    """
    await manager.subscribe(mock_session, mock_request)

    pipeline = mock_redis.pipeline.return_value
    # Find the SADD call for active_hashes
    for call in pipeline.sadd.call_args_list:
        args = call[0]
        if args[0] == ACTIVE_HASHES_KEY:
            assert args[1] == "abc123def456"
            break
    else:
        pytest.fail("SADD was not called for the active_hashes key")


async def test_unsubscribe_removes_hash_from_active_set(manager, mock_redis, mock_session, mock_request):
    """
    Architecture §4.4: When the last listener unsubscribes, the hash must be removed
    from active_hashes to stop the Reporting Worker from polling the DB.
    """
    mock_redis.scard.return_value = 0

    await manager.unsubscribe(mock_session, mock_request)

    pipeline = mock_redis.pipeline.return_value
    pipeline.srem.assert_called_once_with(ACTIVE_HASHES_KEY, "abc123def456")