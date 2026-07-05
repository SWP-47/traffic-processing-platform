# ==============================================================================
# CnSS WebSocket Garbage Collector Unit Tests
# Validates Redis subscription state cleanup upon client disconnect, ensuring
# no orphaned listener entries remain and empty registry keys are purged.
# ==============================================================================

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.websocket.gc import (
    ACTIVE_HASHES_KEY,
    GarbageCollector,
)

# --- Test Fixtures ---


@pytest.fixture
def mock_redis():
    """Provides a mocked Redis client instance with pipeline support."""
    redis = AsyncMock()
    # Pipeline commands are SYNCHRONOUS in redis.asyncio and return the pipeline for chaining.
    pipeline = MagicMock()
    pipeline.delete = MagicMock(return_value=pipeline)
    pipeline.srem = MagicMock(return_value=pipeline)
    pipeline.execute = AsyncMock(return_value=[])
    redis.pipeline = MagicMock(return_value=pipeline)
    return redis


@pytest.fixture
def gc(mock_redis):
    """Provides a GarbageCollector instance with a mocked Redis client."""
    with patch("services.websocket.gc.get_redis_client", return_value=mock_redis):
        yield GarbageCollector()


# --- Cleanup Method Tests ---


async def test_cleanup_empty_session(gc, mock_redis):
    """
    Verify that cleanup does nothing if the client has no active subscriptions.
    """
    mock_redis.smembers.return_value = []

    await gc.cleanup("client-uuid-123")

    # Verify SMEMBERS was called for the session subs key
    mock_redis.smembers.assert_awaited_once_with("ws:session:client-uuid-123:subs")
    # Verify no further Redis operations were performed
    mock_redis.srem.assert_not_awaited()


async def test_cleanup_multiple_subscriptions(gc, mock_redis):
    """
    Verify that cleanup processes all active subscription pairs for the client.
    """
    mock_redis.smembers.return_value = [b"hash-1:sub-1", b"hash-2:sub-2"]
    mock_redis.srem.return_value = 1
    mock_redis.scard.return_value = 0

    await gc.cleanup("client-uuid-123")

    # Verify SREM was called for both listeners keys
    assert mock_redis.srem.await_count == 2
    mock_redis.srem.assert_any_await("sub:listeners:hash-1", "client-uuid-123:sub-1")
    mock_redis.srem.assert_any_await("sub:listeners:hash-2", "client-uuid-123:sub-2")


async def test_cleanup_handles_redis_error(gc, mock_redis):
    """
    Verify that Redis errors during cleanup are caught and do not crash the handler.
    """
    mock_redis.smembers.side_effect = Exception("Connection lost")

    # Should not raise any exceptions
    await gc.cleanup("client-uuid-123")


# --- Cleanup Subscription Method Tests ---


async def test_cleanup_subscription_removes_member_and_purges_empty_set(gc, mock_redis):
    """
    Verify that if the listener set becomes empty after SREM, the registry,
    listeners key, and active hash index are purged via a pipeline.
    """
    mock_redis.srem.return_value = 1
    mock_redis.scard.return_value = 0

    await gc._cleanup_subscription("client-uuid-123", "hash-abc", "sub-123")

    # Verify SREM was called with the composite member
    mock_redis.srem.assert_awaited_once_with("sub:listeners:hash-abc", "client-uuid-123:sub-123")

    # Verify SCARD was called to check remaining listeners
    mock_redis.scard.assert_awaited_once_with("sub:listeners:hash-abc")

    # Verify pipeline was created and executed
    mock_redis.pipeline.assert_called_once_with(transaction=False)
    pipeline = mock_redis.pipeline.return_value

    pipeline.delete.assert_any_call("sub:registry:hash-abc")
    pipeline.delete.assert_any_call("sub:listeners:hash-abc")
    pipeline.srem.assert_called_once_with(ACTIVE_HASHES_KEY, "hash-abc")
    pipeline.execute.assert_awaited_once()


async def test_cleanup_subscription_keeps_non_empty_set(gc, mock_redis):
    """
    Verify that if other listeners remain in the set, no pipeline cleanup is performed.
    """
    mock_redis.srem.return_value = 1
    mock_redis.scard.return_value = 2

    await gc._cleanup_subscription("client-uuid-123", "hash-abc", "sub-123")

    # Verify SREM and SCARD were called
    mock_redis.srem.assert_awaited_once()
    mock_redis.scard.assert_awaited_once()

    # Verify pipeline was NOT created (other listeners remain)
    mock_redis.pipeline.assert_not_called()


async def test_cleanup_subscription_member_not_found(gc, mock_redis):
    """
    Verify that if SREM returns 0 (member was already removed or never existed),
    no further checks or cleanups are performed.
    """
    mock_redis.srem.return_value = 0

    await gc._cleanup_subscription("client-uuid-123", "hash-abc", "sub-123")

    # Verify SREM was called
    mock_redis.srem.assert_awaited_once()

    # Verify SCARD and pipeline were NOT called
    mock_redis.scard.assert_not_awaited()
    mock_redis.pipeline.assert_not_called()


async def test_cleanup_subscription_handles_srem_error(gc, mock_redis):
    """
    Verify that Redis errors during SREM are caught and do not crash the handler.
    """
    mock_redis.srem.side_effect = Exception("Connection lost")

    # Should not raise any exceptions
    await gc._cleanup_subscription("client-uuid-123", "hash-abc", "sub-123")


async def test_cleanup_subscription_handles_pipeline_error(gc, mock_redis):
    """
    Verify that Redis errors during pipeline execution are caught and do not crash the handler.
    """
    mock_redis.srem.return_value = 1
    mock_redis.scard.return_value = 0
    pipeline = mock_redis.pipeline.return_value
    pipeline.execute.side_effect = Exception("Pipeline failed")

    # Should not raise any exceptions
    await gc._cleanup_subscription("client-uuid-123", "hash-abc", "sub-123")
