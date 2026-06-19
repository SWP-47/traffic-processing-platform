import pytest
from datetime import datetime, timezone, timedelta
from app.store.memory import InMemoryStateStore


@pytest.fixture
def store():
    """Provides a fresh InMemoryStateStore for each test."""
    return InMemoryStateStore()


# --- AC 2: Auto-create new channel ---
@pytest.mark.asyncio
async def test_ac2_auto_create_channel(store):
    channel_id = "new-channel"
    now = datetime.now(timezone.utc)

    # Verify channel doesn't exist initially
    assert await store.get_channel(channel_id) is None

    # Trigger creation via update
    await store.update_channel_activity(
        channel_id, incoming_sequence=1, server_received_at=now
    )

    channel = await store.get_channel(channel_id)
    assert channel is not None
    assert channel.channel_id == channel_id
    assert channel.is_active is True
    assert channel.last_activity_timestamp == now
    assert channel.last_sequence == 1
    assert isinstance(channel.listeners, set)
    assert len(channel.listeners) == 0  # Empty listeners set


# --- AC 1: Parse and update in-memory state ---
@pytest.mark.asyncio
async def test_ac1_update_in_memory_state(store):
    channel_id = "test-channel"
    now = datetime.now(timezone.utc)
    later = now + timedelta(seconds=1)

    # Initial update
    await store.update_channel_activity(
        channel_id, incoming_sequence=10, server_received_at=now
    )
    channel = await store.get_channel(channel_id)
    assert channel.last_sequence == 10

    # Subsequent update
    await store.update_channel_activity(
        channel_id, incoming_sequence=11, server_received_at=later
    )
    channel = await store.get_channel(channel_id)
    assert channel.last_sequence == 11
    assert channel.last_activity_timestamp == later


# --- AC 3: Detect dropped batches ---
@pytest.mark.asyncio
async def test_ac3_detect_dropped_batches(store):
    channel_id = "drop-test"
    now = datetime.now(timezone.utc)

    # First batch (sequence 1)
    await store.update_channel_activity(
        channel_id, incoming_sequence=1, server_received_at=now
    )

    # Second batch with a gap (missed sequences 2, 3, 4 -> incoming is 5)
    dropped = await store.update_channel_activity(
        channel_id, incoming_sequence=5, server_received_at=now
    )

    assert dropped == 3
    channel = await store.get_channel(channel_id)
    assert channel.last_sequence == 5


# --- AC 4: Handle out-of-order/duplicates gracefully ---
@pytest.mark.asyncio
async def test_ac4_out_of_order_handling(store):
    channel_id = "ooo-test"
    now = datetime.now(timezone.utc)
    later = now + timedelta(seconds=1)

    # First batch (sequence 5)
    await store.update_channel_activity(
        channel_id, incoming_sequence=5, server_received_at=now
    )

    # Out-of-order batch arrives (sequence 3)
    dropped = await store.update_channel_activity(
        channel_id, incoming_sequence=3, server_received_at=later
    )

    # Dropped must be 0
    assert dropped == 0

    channel = await store.get_channel(channel_id)
    # Timestamp MUST still update
    assert channel.last_activity_timestamp == later
    # Last sequence MUST NOT regress
    assert channel.last_sequence == 5
