# ==============================================================================
# CnSS WebSocket Pub/Sub Consumer Unit Tests
# Validates pattern subscription, message routing, ID injection, and listener
# grouping against architectural specifications (architecture.md §2.3.5).
# ==============================================================================

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.websocket.pubsub_consumer import (
    PUSH_CHANNEL_PATTERN,
    PUSH_CHANNEL_PREFIX_LEN,
    PubSubConsumer,
)


# --- Async Iterator Helper ---
async def _blocking_async_iterator(stop_event: asyncio.Event):
    """
    Blocking async iterator that simulates a long-running Redis Pub/Sub listener.
    Waits until the stop_event is set, then yields once to terminate.
    """
    while not stop_event.is_set():
        await asyncio.sleep(0.1)
    yield  # Makes this an async generator (reached only when stop_event is set)


# --- Async Iterator Helper ---
async def _empty_async_iterator():
    """
    Empty async iterator to replace AsyncMock for pubsub.listen().
    AsyncMock returns a coroutine, but 'async for' requires an async iterator.
    """
    return
    yield  # Makes this an async generator


# --- Test Fixtures ---


@pytest.fixture
def mock_redis():
    """Provides a mocked Redis client with pubsub support."""
    redis = MagicMock()
    pubsub = MagicMock()
    pubsub.psubscribe = AsyncMock()

    # Create a stop event for controlling the iterator lifecycle
    stop_event = asyncio.Event()

    # Use blocking async generator instead of empty iterator
    pubsub.listen = lambda: _blocking_async_iterator(stop_event)
    pubsub.stop_event = stop_event  # Store for cleanup
    pubsub.unsubscribe = AsyncMock()
    pubsub.close = AsyncMock()
    redis.pubsub = MagicMock(return_value=pubsub)
    redis.smembers = AsyncMock()
    return redis


@pytest.fixture
def mock_websocket():
    """Provides a mocked WebSocket connection."""
    ws = MagicMock()
    ws.send = AsyncMock()
    return ws


@pytest.fixture
def get_websocket_func(mock_websocket):
    """Provides a callback function that returns a mock WebSocket."""

    def _get_websocket(client_id: str):
        if client_id == "missing-client":
            return None
        return mock_websocket

    return _get_websocket


@pytest.fixture
def consumer(mock_redis, get_websocket_func):
    """Provides a PubSubConsumer instance with mocked dependencies."""
    with patch("services.websocket.pubsub_consumer.get_redis_client", return_value=mock_redis):
        yield PubSubConsumer(get_websocket=get_websocket_func)


# --- Start/Stop Lifecycle Tests ---


async def test_start_subscribes_to_pattern(consumer, mock_redis):
    """
    Architecture §2.3.5: Consumer must subscribe to all ws:push:* channels
    using pattern subscription for dynamic channel discovery.
    """
    await consumer.start()

    # Give the background task a chance to execute
    await asyncio.sleep(0)

    # Verify pubsub was created
    mock_redis.pubsub.assert_called_once()

    # Verify pattern subscription was called
    pubsub = mock_redis.pubsub.return_value
    pubsub.psubscribe.assert_awaited_once_with(PUSH_CHANNEL_PATTERN)

    # Verify task was created
    assert consumer._task is not None
    assert not consumer._task.done()

    # Cleanup
    await consumer.stop()


async def test_stop_cancels_task_and_cleans_up(consumer, mock_redis):
    """
    Verify that stop() gracefully cancels the background task and cleans up
    Redis pubsub resources.
    """
    await consumer.start()

    # Give the background task a chance to execute
    await asyncio.sleep(0)

    task = consumer._task

    await consumer.stop()

    # Verify task was cancelled
    assert task.cancelled() or task.done()

    # Verify pubsub cleanup
    pubsub = mock_redis.pubsub.return_value
    pubsub.unsubscribe.assert_awaited_once()
    pubsub.close.assert_awaited_once()

    # Verify pubsub reference was cleared
    assert consumer._pubsub is None


# --- Message Handling Tests ---


async def test_handle_message_routes_to_correct_client(consumer, mock_redis, mock_websocket):
    """
    Architecture §2.3.5: Consumer must extract query_hash from channel name,
    retrieve listeners, and route messages to the correct WebSocket clients.
    """
    # Prepare mock data
    query_hash = "abc123"
    channel_name = f"ws:push:{query_hash}"
    payload = {"type": "telemetry_update", "data": "test"}

    # Mock listeners (format: client_id:sub_id)
    mock_redis.smembers.return_value = [b"client-1:sub-1", b"client-2:sub-2"]

    # Create message
    message = {
        "type": "pmessage",
        "channel": channel_name.encode("utf-8"),
        "data": json.dumps(payload).encode("utf-8"),
    }

    await consumer._handle_message(message)

    # Verify query_hash extraction
    assert channel_name[PUSH_CHANNEL_PREFIX_LEN:] == query_hash

    # Verify listeners were retrieved
    mock_redis.smembers.assert_awaited_once_with(f"sub:listeners:{query_hash}")

    # Verify messages were sent to both clients
    assert mock_websocket.send.await_count == 2


async def test_handle_message_injects_sub_id_as_id(consumer, mock_redis, mock_websocket):
    """
    Architecture §2.3.5: Consumer must inject the sub_id into the JSON payload
    as the "id" field before sending to the client.
    """
    query_hash = "abc123"
    channel_name = f"ws:push:{query_hash}"
    payload = {"type": "telemetry_update", "data": "test"}

    # Mock single listener
    mock_redis.smembers.return_value = [b"client-1:sub-123"]

    message = {
        "type": "pmessage",
        "channel": channel_name.encode("utf-8"),
        "data": json.dumps(payload).encode("utf-8"),
    }

    await consumer._handle_message(message)

    # Verify send was called
    mock_websocket.send.assert_awaited_once()

    # Extract the sent payload
    sent_data = mock_websocket.send.call_args[0][0]
    sent_payload = json.loads(sent_data)

    # Verify "id" field was injected with sub_id
    assert "id" in sent_payload
    assert sent_payload["id"] == "sub-123"

    # Verify original payload fields are preserved
    assert sent_payload["type"] == "telemetry_update"
    assert sent_payload["data"] == "test"


async def test_handle_message_groups_listeners_by_client_id(consumer, mock_redis, mock_websocket):
    """
    Architecture §2.3.5: Consumer must group listeners by client_id to optimize
    WebSocket lookups (one lookup per client, not per subscription).
    """
    query_hash = "abc123"
    channel_name = f"ws:push:{query_hash}"
    payload = {"type": "telemetry_update"}

    # Mock multiple subscriptions for the same client
    mock_redis.smembers.return_value = [
        b"client-1:sub-1",
        b"client-1:sub-2",
        b"client-2:sub-3",
    ]

    message = {
        "type": "pmessage",
        "channel": channel_name.encode("utf-8"),
        "data": json.dumps(payload).encode("utf-8"),
    }

    await consumer._handle_message(message)

    # Verify messages were sent (2 for client-1, 1 for client-2)
    assert mock_websocket.send.await_count == 3


async def test_handle_message_skips_missing_clients(consumer, mock_redis, mock_websocket):
    """
    Verify that consumer gracefully handles cases where a client is no longer
    connected (get_websocket returns None).
    """
    query_hash = "abc123"
    channel_name = f"ws:push:{query_hash}"
    payload = {"type": "telemetry_update"}

    # Mock one existing client and one missing client
    mock_redis.smembers.return_value = [
        b"client-1:sub-1",
        b"missing-client:sub-2",
    ]

    message = {
        "type": "pmessage",
        "channel": channel_name.encode("utf-8"),
        "data": json.dumps(payload).encode("utf-8"),
    }

    # Should not raise exception
    await consumer._handle_message(message)

    # Verify only one message was sent (to existing client)
    assert mock_websocket.send.await_count == 1


async def test_handle_message_handles_malformed_json(consumer, mock_redis):
    """
    Verify that consumer gracefully handles malformed JSON in the message data.
    """
    query_hash = "abc123"
    channel_name = f"ws:push:{query_hash}"

    mock_redis.smembers.return_value = [b"client-1:sub-1"]

    message = {
        "type": "pmessage",
        "channel": channel_name.encode("utf-8"),
        "data": b"not valid json",
    }

    # Should not raise exception, just log error
    await consumer._handle_message(message)


async def test_handle_message_handles_empty_listeners(consumer, mock_redis):
    """
    Verify that consumer handles cases where no listeners are registered
    for a query_hash (e.g., all clients disconnected).
    """
    query_hash = "abc123"
    channel_name = f"ws:push:{query_hash}"
    payload = {"type": "telemetry_update"}

    # Mock empty listener set
    mock_redis.smembers.return_value = []

    message = {
        "type": "pmessage",
        "channel": channel_name.encode("utf-8"),
        "data": json.dumps(payload).encode("utf-8"),
    }

    # Should not raise exception
    await consumer._handle_message(message)


async def test_handle_message_handles_send_error(consumer, mock_redis, mock_websocket):
    """
    Verify that consumer gracefully handles WebSocket send errors without
    crashing the entire consumer loop.
    """
    query_hash = "abc123"
    channel_name = f"ws:push:{query_hash}"
    payload = {"type": "telemetry_update"}

    mock_redis.smembers.return_value = [b"client-1:sub-1"]

    # Mock send error
    mock_websocket.send.side_effect = Exception("Connection closed")

    message = {
        "type": "pmessage",
        "channel": channel_name.encode("utf-8"),
        "data": json.dumps(payload).encode("utf-8"),
    }

    # Should not raise exception
    await consumer._handle_message(message)


# --- Edge Cases ---


async def test_handle_message_handles_bytes_and_strings(consumer, mock_redis, mock_websocket):
    """
    Verify that consumer correctly handles both bytes and string formats
    for channel names and data (Redis can return either depending on config).
    """
    query_hash = "abc123"
    payload = {"type": "telemetry_update"}

    # Test with bytes
    mock_redis.smembers.return_value = [b"client-1:sub-1"]

    message_bytes = {
        "type": "pmessage",
        "channel": f"ws:push:{query_hash}".encode("utf-8"),
        "data": json.dumps(payload).encode("utf-8"),
    }

    await consumer._handle_message(message_bytes)
    assert mock_websocket.send.await_count == 1

    # Reset and test with strings
    mock_websocket.send.reset_mock()
    mock_redis.smembers.return_value = ["client-1:sub-1"]

    message_strings = {
        "type": "pmessage",
        "channel": f"ws:push:{query_hash}",
        "data": json.dumps(payload),
    }

    await consumer._handle_message(message_strings)
    assert mock_websocket.send.await_count == 1


async def test_handle_message_handles_redis_error(consumer, mock_redis):
    """
    Verify that consumer gracefully handles Redis errors when retrieving listeners.
    """
    query_hash = "abc123"
    channel_name = f"ws:push:{query_hash}"
    payload = {"type": "telemetry_update"}

    # Mock Redis error
    mock_redis.smembers.side_effect = Exception("Redis connection lost")

    message = {
        "type": "pmessage",
        "channel": channel_name.encode("utf-8"),
        "data": json.dumps(payload).encode("utf-8"),
    }

    # Should not raise exception
    await consumer._handle_message(message)
