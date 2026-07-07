# ==============================================================================
# CnSS WebSocket Service Integration Tests
# Validates the end-to-end WebSocket connection lifecycle, subscription management,
# session handling, and garbage collection against a live Redis instance.
# Requires Redis and TimescaleDB to be running (e.g., via `make dev`).
# ==============================================================================

import asyncio
import json
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.contracts.auth import TokenPayload
from core.contracts.subscriptions import SubscribeRequest, SubscriptionParams
from core.redis.client import close_redis_client, get_redis_client, init_redis_client
from core.security.jwt import create_access_token
from services.websocket.gc import GarbageCollector
from services.websocket.pubsub_consumer import PubSubConsumer
from services.websocket.session import SESSION_KEY_PREFIX, Session
from services.websocket.subscription import (
    ACTIVE_HASHES_KEY,
    LISTENERS_KEY_PREFIX,
    REGISTRY_KEY_PREFIX,
    SubscriptionManager,
)

# --- Test Constants ---
TEST_CHANNEL_ID = "ws-test-channel-01"
TEST_CHANNEL_ID_2 = "ws-test-channel-02"
TEST_WS_PORT = 8765  # Use a different port to avoid conflicts


# --- Fixtures ---
@pytest.fixture
async def redis_setup():
    """
    Initializes the global Redis client for the test.
    Ensures a clean state by flushing test-specific keys before and after tests.
    Uses function scope to align with pytest-asyncio's default event loop lifecycle,
    preventing 'Event loop is closed' errors when global clients are reused across loops.
    """
    # Reset the global Redis client to ensure it binds to the current test's event loop
    await close_redis_client()

    await init_redis_client()
    redis = get_redis_client()

    # Clean up any leftover data from previous failed runs
    await redis.flushdb()

    yield redis

    # Teardown: Clean up after the test has run
    await redis.flushdb()

    # Close the client to release resources and reset global state
    await close_redis_client()


@pytest.fixture
def mock_db_pool():
    """Provides a mocked asyncpg connection pool for snapshot tests."""
    pool = AsyncMock()
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value={"channel_id": TEST_CHANNEL_ID})
    conn.fetch = AsyncMock(return_value=[])
    pool.acquire = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=conn), __aexit__=AsyncMock()))
    return pool


@pytest.fixture
def valid_token_payload():
    """Provides a valid TokenPayload for testing."""
    return TokenPayload(
        sub="user-123",
        jti=str(uuid.uuid4()),
        iat=int(datetime.now(timezone.utc).timestamp()),
        exp=int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
        role="viewer",
        scope=[TEST_CHANNEL_ID, TEST_CHANNEL_ID_2],
    )


@pytest.fixture
def admin_token_payload():
    """Provides an admin TokenPayload for testing."""
    return TokenPayload(
        sub="admin-123",
        jti=str(uuid.uuid4()),
        iat=int(datetime.now(timezone.utc).timestamp()),
        exp=int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
        role="admin",
        scope=[],
    )


@pytest.fixture
def valid_access_token(valid_token_payload):
    """Generates a valid JWT access token."""
    return create_access_token(
        subject=valid_token_payload.sub,
        role=valid_token_payload.role,
        scope=valid_token_payload.scope,
    )


@pytest.fixture
def admin_access_token(admin_token_payload):
    """Generates an admin JWT access token."""
    return create_access_token(
        subject=admin_token_payload.sub,
        role=admin_token_payload.role,
        scope=admin_token_payload.scope,
    )


@pytest.fixture
def session(redis_setup, valid_token_payload):
    """Provides a Session instance connected to the test Redis."""
    return Session(
        client_id="test-client-uuid",
        channel_id=TEST_CHANNEL_ID,
        payload=valid_token_payload,
    )


@pytest.fixture
def subscription_manager(redis_setup):
    """Provides a SubscriptionManager instance connected to the test Redis."""
    return SubscriptionManager()


@pytest.fixture
def garbage_collector(redis_setup):
    """Provides a GarbageCollector instance connected to the test Redis."""
    return GarbageCollector()


# --- Helper Functions ---
def create_subscribe_request(
    channel_id: str = TEST_CHANNEL_ID,
    target: str = "telemetry",
    sub_id: str = "sub-123",
) -> SubscribeRequest:
    """Constructs a valid SubscribeRequest for testing."""
    return SubscribeRequest(
        action="subscribe",
        id=sub_id,
        channel_id=channel_id,
        target=target,
        params=SubscriptionParams(),
    )


# --- Session Management Integration Tests ---
async def test_session_creation_with_ttl(redis_setup, session):
    """
    Architecture §2.3.7: Session must be created with strict TTL of 10 seconds.
    Verifies that the session key exists in Redis with correct TTL.
    """
    redis = redis_setup

    # Create session
    await session.create()

    # Verify session key exists
    session_key = f"{SESSION_KEY_PREFIX}{session.client_id}"
    exists = await redis.exists(session_key)
    assert exists == 1, "Session key should exist after creation"

    # Verify TTL is set (should be close to 10 seconds)
    ttl = await redis.ttl(session_key)
    assert 8 <= ttl <= 10, f"TTL should be ~10 seconds, got {ttl}"

    # Verify session data
    session_data = await redis.hgetall(session_key)
    assert session_data["client_id"] == session.client_id
    assert session_data["channel_id"] == session.channel_id
    assert session_data["role"] == session.role

    # Cleanup
    await session.destroy()


async def test_session_heartbeat_refresh(redis_setup, session):
    """
    Architecture §2.3.7: Heartbeat must refresh session TTL periodically.
    Verifies that refresh_ttl resets the TTL to 10 seconds.
    """
    redis = redis_setup

    # Create session
    await session.create()

    # Wait a bit to let TTL decrease
    await asyncio.sleep(2)

    # Refresh TTL
    await session.refresh_ttl()

    # Verify TTL is reset to ~10 seconds
    session_key = f"{SESSION_KEY_PREFIX}{session.client_id}"
    ttl = await redis.ttl(session_key)
    assert 9 <= ttl <= 10, f"TTL should be refreshed to ~10 seconds, got {ttl}"

    # Cleanup
    await session.destroy()


async def test_session_destruction(redis_setup, session):
    """
    Architecture §2.3.6: Session must be destroyed on client disconnect.
    Verifies that session and subs keys are removed from Redis.
    """
    redis = redis_setup

    # Create session
    await session.create()

    # Add a subscription
    await session.add_subscription("hash-abc", "sub-123")

    # Destroy session
    await session.destroy()

    # Verify session key is removed
    session_key = f"{SESSION_KEY_PREFIX}{session.client_id}"
    exists = await redis.exists(session_key)
    assert exists == 0, "Session key should be removed after destruction"

    # Verify subs key is removed
    subs_key = f"{SESSION_KEY_PREFIX}{session.client_id}:subs"
    exists = await redis.exists(subs_key)
    assert exists == 0, "Subs key should be removed after destruction"


# --- Subscription Management Integration Tests ---
async def test_subscribe_creates_registry_and_listeners(redis_setup, subscription_manager, session):
    """
    Architecture §2.3.3: Subscribe must create registry entry and add listener.
    Verifies that sub:registry:{hash} and sub:listeners:{hash} are created.
    """
    redis = redis_setup

    # Create session
    await session.create()

    # Create subscribe request
    request = create_subscribe_request(sub_id="sub-test-001")

    # Subscribe
    query_hash, push_channel = await subscription_manager.subscribe(session, request)

    # Verify registry key exists
    registry_key = f"{REGISTRY_KEY_PREFIX}{query_hash}"
    registry_data = await redis.get(registry_key)
    assert registry_data is not None, "Registry key should exist after subscription"

    # Verify registry contains correct JSON
    registry_json = json.loads(registry_data)
    assert registry_json["channel_id"] == request.channel_id
    assert registry_json["target"] == request.target

    # Verify listener is added
    listeners_key = f"{LISTENERS_KEY_PREFIX}{query_hash}"
    listeners = await redis.smembers(listeners_key)
    assert f"{session.client_id}:{request.id}" in listeners, "Listener should be added to set"

    # Verify hash is indexed in active_hashes
    active_hashes = await redis.smembers(ACTIVE_HASHES_KEY)
    assert query_hash in active_hashes, "Query hash should be in active_hashes set"

    # Cleanup
    await redis.delete(registry_key, listeners_key)
    await redis.srem(ACTIVE_HASHES_KEY, query_hash)
    await session.destroy()


async def test_subscribe_query_hash_excludes_id(redis_setup, subscription_manager, session):
    """
    Architecture §4.2: Query hash must exclude client-provided 'id' field.
    Verifies that two subscriptions with different IDs produce the same hash.
    """
    redis = redis_setup

    # Create session
    await session.create()

    # Create two requests with different IDs but same params
    request1 = create_subscribe_request(sub_id="sub-aaa-111")
    request2 = create_subscribe_request(sub_id="sub-bbb-222")

    # Subscribe first request
    hash1, _ = await subscription_manager.subscribe(session, request1)

    # Subscribe second request
    hash2, _ = await subscription_manager.subscribe(session, request2)

    # Verify hashes are identical (id is excluded)
    assert hash1 == hash2, "Query hashes should be identical when id is excluded"

    # Verify both listeners are in the same set
    listeners_key = f"{LISTENERS_KEY_PREFIX}{hash1}"
    listeners = await redis.smembers(listeners_key)
    assert f"{session.client_id}:sub-aaa-111" in listeners
    assert f"{session.client_id}:sub-bbb-222" in listeners

    # Cleanup
    await redis.delete(listeners_key, f"{REGISTRY_KEY_PREFIX}{hash1}")
    await redis.srem(ACTIVE_HASHES_KEY, hash1)
    await session.destroy()


async def test_unsubscribe_removes_listener(redis_setup, subscription_manager, session):
    """
    Architecture §4.4: Unsubscribe must remove listener from set.
    Verifies that the listener is removed but registry remains if other listeners exist.
    """
    redis = redis_setup

    # Create session
    await session.create()

    # Subscribe
    request = create_subscribe_request(sub_id="sub-unsub-test")
    query_hash, _ = await subscription_manager.subscribe(session, request)

    # Add another listener (simulate another client)
    listeners_key = f"{LISTENERS_KEY_PREFIX}{query_hash}"
    await redis.sadd(listeners_key, "other-client:sub-other")

    # Unsubscribe
    await subscription_manager.unsubscribe(session, request)

    # Verify listener is removed
    listeners = await redis.smembers(listeners_key)
    assert f"{session.client_id}:sub-unsub-test" not in listeners
    assert "other-client:sub-other" in listeners, "Other listener should remain"

    # Verify registry still exists (other listener present)
    registry_key = f"{REGISTRY_KEY_PREFIX}{query_hash}"
    exists = await redis.exists(registry_key)
    assert exists == 1, "Registry should remain when other listeners exist"

    # Cleanup
    await redis.delete(registry_key, listeners_key)
    await redis.srem(ACTIVE_HASHES_KEY, query_hash)
    await session.destroy()


async def test_unsubscribe_last_listener_cleans_up(redis_setup, subscription_manager, session):
    """
    Architecture §4.4: When last listener unsubscribes, registry must be deleted.
    Verifies that registry, listeners, and active_hashes are cleaned up.
    """
    redis = redis_setup

    # Create session
    await session.create()

    # Subscribe
    request = create_subscribe_request(sub_id="sub-last-listener")
    query_hash, _ = await subscription_manager.subscribe(session, request)

    # Unsubscribe (last listener)
    await subscription_manager.unsubscribe(session, request)

    # Verify registry is deleted
    registry_key = f"{REGISTRY_KEY_PREFIX}{query_hash}"
    exists = await redis.exists(registry_key)
    assert exists == 0, "Registry should be deleted when last listener unsubscribes"

    # Verify listeners key is deleted
    listeners_key = f"{LISTENERS_KEY_PREFIX}{query_hash}"
    exists = await redis.exists(listeners_key)
    assert exists == 0, "Listeners key should be deleted"

    # Verify hash is removed from active_hashes
    active_hashes = await redis.smembers(ACTIVE_HASHES_KEY)
    assert query_hash not in active_hashes, "Hash should be removed from active_hashes"

    # Cleanup
    await session.destroy()


# --- Garbage Collection Integration Tests ---
async def test_gc_cleanup_on_disconnect(redis_setup, garbage_collector, subscription_manager, session):
    """
    Architecture §2.3.6: GC must clean up all subscriptions on disconnect.
    Verifies that all listener entries are removed and empty registries are deleted.
    """
    redis = redis_setup

    # Create session
    await session.create()

    # Subscribe to multiple targets
    request1 = create_subscribe_request(target="telemetry", sub_id="sub-gc-1")
    request2 = create_subscribe_request(target="hosts_table", sub_id="sub-gc-2")

    hash1, _ = await subscription_manager.subscribe(session, request1)
    hash2, _ = await subscription_manager.subscribe(session, request2)

    # Verify subscriptions exist
    listeners1 = await redis.smembers(f"{LISTENERS_KEY_PREFIX}{hash1}")
    listeners2 = await redis.smembers(f"{LISTENERS_KEY_PREFIX}{hash2}")
    assert len(listeners1) == 1
    assert len(listeners2) == 1

    # Simulate disconnect: run GC cleanup
    await garbage_collector.cleanup(session.client_id)

    # Verify all listeners are removed
    listeners1 = await redis.smembers(f"{LISTENERS_KEY_PREFIX}{hash1}")
    listeners2 = await redis.smembers(f"{LISTENERS_KEY_PREFIX}{hash2}")
    assert len(listeners1) == 0, "All listeners should be removed after GC"
    assert len(listeners2) == 0, "All listeners should be removed after GC"

    # Verify registries are deleted (no listeners remain)
    exists1 = await redis.exists(f"{REGISTRY_KEY_PREFIX}{hash1}")
    exists2 = await redis.exists(f"{REGISTRY_KEY_PREFIX}{hash2}")
    assert exists1 == 0, "Registry should be deleted when no listeners remain"
    assert exists2 == 0, "Registry should be deleted when no listeners remain"

    # Cleanup
    await session.destroy()


async def test_gc_preserves_other_listeners(redis_setup, garbage_collector, subscription_manager, session):
    """
    Architecture §2.3.6: GC must preserve other listeners when cleaning up one client.
    Verifies that only the disconnecting client's entries are removed.
    """
    redis = redis_setup

    # Create session
    await session.create()

    # Subscribe
    request = create_subscribe_request(sub_id="sub-gc-preserve")
    query_hash, _ = await subscription_manager.subscribe(session, request)

    # Add another listener (simulate another client)
    listeners_key = f"{LISTENERS_KEY_PREFIX}{query_hash}"
    await redis.sadd(listeners_key, "other-client:sub-other")

    # Run GC cleanup for our session
    await garbage_collector.cleanup(session.client_id)

    # Verify our listener is removed
    listeners = await redis.smembers(listeners_key)
    assert f"{session.client_id}:sub-gc-preserve" not in listeners

    # Verify other listener is preserved
    assert "other-client:sub-other" in listeners, "Other listener should be preserved"

    # Verify registry still exists (other listener present)
    registry_key = f"{REGISTRY_KEY_PREFIX}{query_hash}"
    exists = await redis.exists(registry_key)
    assert exists == 1, "Registry should remain when other listeners exist"

    # Cleanup
    await redis.delete(registry_key, listeners_key)
    await redis.srem(ACTIVE_HASHES_KEY, query_hash)
    await session.destroy()


# --- Pub/Sub Consumer Integration Tests ---
async def test_pubsub_message_routing(redis_setup, session, subscription_manager):
    """
    Architecture §2.3.5: Pub/Sub consumer must route messages to correct clients.
    Verifies that messages are sent to all listeners of a query_hash.
    """
    redis = redis_setup

    # Create session
    await session.create()

    # Subscribe
    request = create_subscribe_request(sub_id="sub-pubsub-test")
    query_hash, push_channel = await subscription_manager.subscribe(session, request)

    # Mock WebSocket
    mock_ws = AsyncMock()
    mock_ws.send = AsyncMock()

    # Create Pub/Sub consumer with mock WebSocket getter
    def get_websocket(client_id: str):
        if client_id == session.client_id:
            return mock_ws
        return None

    consumer = PubSubConsumer(get_websocket=get_websocket)

    # Simulate incoming Pub/Sub message
    message = {
        "type": "pmessage",
        "channel": f"ws:push:{query_hash}".encode("utf-8"),
        "data": json.dumps({"type": "telemetry_update", "data": "test"}).encode("utf-8"),
    }

    await consumer._handle_message(message)

    # Verify message was sent to WebSocket
    mock_ws.send.assert_awaited_once()

    # Verify payload contains injected sub_id
    sent_data = mock_ws.send.call_args[0][0]
    sent_payload = json.loads(sent_data)
    assert sent_payload["id"] == request.id, "sub_id should be injected as 'id' field"

    # Cleanup
    await redis.delete(f"{REGISTRY_KEY_PREFIX}{query_hash}", f"{LISTENERS_KEY_PREFIX}{query_hash}")
    await redis.srem(ACTIVE_HASHES_KEY, query_hash)
    await session.destroy()


# --- Edge Case Tests ---
async def test_session_expiration(redis_setup, valid_token_payload):
    """
    Architecture §2.3.7: Session must expire after TTL if heartbeat fails.
    Verifies that session key is automatically removed by Redis after TTL.
    """
    redis = redis_setup

    # Create session with short TTL for testing (we'll manually set it)
    session = Session(
        client_id="test-expiration-client",
        channel_id=TEST_CHANNEL_ID,
        payload=valid_token_payload,
    )

    await session.create()

    # Manually set TTL to 2 seconds for faster testing
    session_key = f"{SESSION_KEY_PREFIX}{session.client_id}"
    await redis.expire(session_key, 2)

    # Wait for expiration
    await asyncio.sleep(3)

    # Verify session key is expired
    exists = await redis.exists(session_key)
    assert exists == 0, "Session key should expire after TTL"


async def test_multiple_parallel_subscriptions(redis_setup, subscription_manager, session):
    """
    Architecture §4.1: Client can maintain multiple parallel subscriptions.
    Verifies that a single client can subscribe to the same query_hash multiple times.
    """
    redis = redis_setup

    # Create session
    await session.create()

    # Subscribe multiple times with different IDs
    request1 = create_subscribe_request(sub_id="sub-parallel-1")
    request2 = create_subscribe_request(sub_id="sub-parallel-2")
    request3 = create_subscribe_request(sub_id="sub-parallel-3")

    hash1, _ = await subscription_manager.subscribe(session, request1)
    hash2, _ = await subscription_manager.subscribe(session, request2)
    hash3, _ = await subscription_manager.subscribe(session, request3)

    # All hashes should be identical (same params, different IDs)
    assert hash1 == hash2 == hash3, "All parallel subscriptions should have same hash"

    # Verify all listeners are in the set
    listeners_key = f"{LISTENERS_KEY_PREFIX}{hash1}"
    listeners = await redis.smembers(listeners_key)
    assert len(listeners) == 3, "All 3 listeners should be in the set"
    assert f"{session.client_id}:sub-parallel-1" in listeners
    assert f"{session.client_id}:sub-parallel-2" in listeners
    assert f"{session.client_id}:sub-parallel-3" in listeners

    # Cleanup
    await redis.delete(listeners_key, f"{REGISTRY_KEY_PREFIX}{hash1}")
    await redis.srem(ACTIVE_HASHES_KEY, hash1)
    await session.destroy()
