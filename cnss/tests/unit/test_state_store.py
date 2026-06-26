import pytest
from datetime import datetime, timezone, timedelta
from app.store.memory import InMemoryStateStore
from app.models import WSClientSession
from unittest.mock import MagicMock


@pytest.fixture
def store():
    """Provides a fresh InMemoryStateStore for each test."""
    return InMemoryStateStore()


# --- Auto-create new channel ---
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


# --- Parse and update in-memory state ---
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


# --- Detect dropped batches ---
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


# --- Handle out-of-order/duplicates gracefully ---
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

# --- ubscription Target Filtering ---
@pytest.mark.asyncio
async def test_get_subscribers_by_target(store):
    """Test filtering sessions by specific subscription target."""
    await store.get_or_create_channel("sub-test-ch")
    
    # Create mock sessions
    ws1 = MagicMock()
    ws2 = MagicMock()
    ws3 = MagicMock()
    
    session1 = WSClientSession(websocket=ws1, user=MagicMock(), channel_id="sub-test-ch")
    session1.subscriptions["lan_hosts"] = {"sort_by": "sent", "limit": 5}
    
    session2 = WSClientSession(websocket=ws2, user=MagicMock(), channel_id="sub-test-ch")
    session2.subscriptions["wan_hosts"] = {"sort_by": "received", "limit": 10}
    
    session3 = WSClientSession(websocket=ws3, user=MagicMock(), channel_id="sub-test-ch")
    # No subscriptions
    
    await store.add_listener("sub-test-ch", session1)
    await store.add_listener("sub-test-ch", session2)
    await store.add_listener("sub-test-ch", session3)
    
    # Query for lan_hosts
    lan_subs = await store.get_subscribers_by_target("sub-test-ch", "lan_hosts")
    assert len(lan_subs) == 1
    assert session1 in lan_subs
    
    # Query for wan_hosts
    wan_subs = await store.get_subscribers_by_target("sub-test-ch", "wan_hosts")
    assert len(wan_subs) == 1
    assert session2 in wan_subs
    
    # Query for non-existent target
    empty_subs = await store.get_subscribers_by_target("sub-test-ch", "unknown_target")
    assert len(empty_subs) == 0