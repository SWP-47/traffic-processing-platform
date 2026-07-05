# ==============================================================================
# CnSS WebSocket Session Manager Unit Tests
# Validates ephemeral session state management in Redis, strict TTL enforcement,
# and subscription tracking against architectural specifications (§2.3, §3.2).
# ==============================================================================

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.contracts.auth import TokenPayload
from core.exceptions import RedisError
from services.websocket.session import (
    SESSION_KEY_PREFIX,
    SESSION_SUBS_SUFFIX,
    SESSION_TTL_SEC,
    Session,
)

# --- Test Fixtures ---


@pytest.fixture
def mock_redis():
    """Provides a mocked Redis client instance with pipeline support."""
    redis = AsyncMock()
    # Create a mock pipeline that returns itself for method chaining
    pipeline = MagicMock()
    pipeline.hset = MagicMock(return_value=pipeline)
    pipeline.expire = MagicMock(return_value=pipeline)
    pipeline.delete = MagicMock(return_value=pipeline)
    pipeline.execute = AsyncMock(return_value=[])
    redis.pipeline = MagicMock(return_value=pipeline)
    return redis


@pytest.fixture
def mock_payload():
    """Provides a valid TokenPayload for testing."""
    return TokenPayload(
        sub="user-123",
        jti="jti-456",
        iat=1700000000,
        exp=1800000000,
        role="viewer",
        scope=["bridge-01"],
    )


@pytest.fixture
def session(mock_redis, mock_payload):
    """Provides a Session instance with a mocked Redis client."""
    with patch("services.websocket.session.get_redis_client", return_value=mock_redis):
        yield Session(
            client_id="client-uuid-123",
            channel_id="bridge-01",
            payload=mock_payload,
        )


# --- Session Creation Tests ---


async def test_create_session_pipeline_operations(session, mock_redis):
    """
    Architecture §2.3 & §3.2: Session creation must use a pipeline to atomically:
    1. Store session metadata in a Hash (HSET).
    2. Set strict TTL of 10 seconds (EXPIRE).
    3. Initialize subscription tracking set (DELETE to ensure clean state).
    """
    await session.create()

    # Verify pipeline was created
    mock_redis.pipeline.assert_called_once_with(transaction=False)
    pipeline = mock_redis.pipeline.return_value

    # Verify HSET was called with correct mapping
    pipeline.hset.assert_called_once()
    call_args = pipeline.hset.call_args
    assert call_args[0][0] == f"{SESSION_KEY_PREFIX}client-uuid-123"
    mapping = call_args[1]["mapping"]
    assert mapping["client_id"] == "client-uuid-123"
    assert mapping["channel_id"] == "bridge-01"
    assert mapping["user_id"] == "user-123"
    assert mapping["role"] == "viewer"
    assert "created_at" in mapping

    # Verify EXPIRE was called with strict 10s TTL
    pipeline.expire.assert_called_once_with(f"{SESSION_KEY_PREFIX}client-uuid-123", SESSION_TTL_SEC)
    assert SESSION_TTL_SEC == 10

    # Verify DELETE was called for the subs key
    pipeline.delete.assert_called_once_with(f"{SESSION_KEY_PREFIX}client-uuid-123{SESSION_SUBS_SUFFIX}")

    # Verify pipeline execution
    pipeline.execute.assert_awaited_once()


async def test_create_session_handles_redis_error(session, mock_redis):
    """
    Verify that Redis errors during session creation are wrapped in RedisError.
    """
    pipeline = mock_redis.pipeline.return_value
    pipeline.execute.side_effect = Exception("Connection lost")

    with pytest.raises(RedisError) as exc_info:
        await session.create()

    assert "Session creation failed" in str(exc_info.value)


# --- TTL Refresh Tests ---


async def test_refresh_ttl_updates_expiration(session, mock_redis):
    """
    Architecture §2.3.7: The WebSocket Service must periodically refresh the session TTL
    (e.g., every 5 seconds) via a background heartbeat task to prevent premature expiration.
    """
    await session.refresh_ttl()

    # Verify EXPIRE was called with the correct key and 10s TTL
    mock_redis.expire.assert_awaited_once_with(f"{SESSION_KEY_PREFIX}client-uuid-123", SESSION_TTL_SEC)


async def test_refresh_ttl_handles_redis_error(session, mock_redis):
    """
    Verify that Redis errors during TTL refresh are logged but do not crash the handler.
    (The code catches the exception and logs it without raising).
    """
    mock_redis.expire.side_effect = Exception("Connection lost")

    # Should not raise any exceptions
    await session.refresh_ttl()


# --- Session Destruction Tests ---


async def test_destroy_session_removes_keys(session, mock_redis):
    """
    Architecture §2.3.6: On client disconnect, the session and its tracking set
    must be removed from Redis to prevent memory leaks.
    """
    await session.destroy()

    # Verify DELETE was called for both session key and subs key
    mock_redis.delete.assert_awaited_once_with(
        f"{SESSION_KEY_PREFIX}client-uuid-123",
        f"{SESSION_KEY_PREFIX}client-uuid-123{SESSION_SUBS_SUFFIX}",
    )


# --- Subscription Tracking Tests ---


async def test_add_subscription_stores_composite_key(session, mock_redis):
    """
    Architecture §3.2: The session's tracking set must store active subscription instances
    as 'query_hash:sub_id' strings for rapid garbage collection.
    """
    await session.add_subscription("hash-abc", "sub-123")

    # Verify SADD was called with the correct key and composite value
    mock_redis.sadd.assert_awaited_once_with(
        f"{SESSION_KEY_PREFIX}client-uuid-123{SESSION_SUBS_SUFFIX}",
        "hash-abc:sub-123",
    )


async def test_remove_subscription_deletes_composite_key(session, mock_redis):
    """
    Verify that removing a subscription deletes the specific 'query_hash:sub_id' entry.
    """
    await session.remove_subscription("hash-abc", "sub-123")

    # Verify SREM was called with the correct key and composite value
    mock_redis.srem.assert_awaited_once_with(
        f"{SESSION_KEY_PREFIX}client-uuid-123{SESSION_SUBS_SUFFIX}",
        "hash-abc:sub-123",
    )


async def test_get_subscriptions_returns_list(session, mock_redis):
    """
    Architecture §2.3.6: On client disconnect, the GC reads the session's tracking set
    to find all 'query_hash:sub_id' pairs for cleanup.
    """
    mock_redis.smembers.return_value = {"hash-abc:sub-123", "hash-def:sub-456"}

    subs = await session.get_subscriptions()

    # Verify SMEMBERS was called for the subs key
    mock_redis.smembers.assert_awaited_once_with(f"{SESSION_KEY_PREFIX}client-uuid-123{SESSION_SUBS_SUFFIX}")

    # Verify the returned list contains the expected composite keys
    assert len(subs) == 2
    assert "hash-abc:sub-123" in subs
    assert "hash-def:sub-456" in subs


async def test_get_subscriptions_returns_empty_list_on_none(session, mock_redis):
    """
    Verify that an empty list is returned if the tracking set is empty or missing.
    """
    mock_redis.smembers.return_value = None

    subs = await session.get_subscriptions()

    assert subs == []


async def test_get_subscriptions_handles_redis_error(session, mock_redis):
    """
    Verify that Redis errors during subscription retrieval are handled gracefully.
    """
    mock_redis.smembers.side_effect = Exception("Connection lost")

    subs = await session.get_subscriptions()

    assert subs == []
