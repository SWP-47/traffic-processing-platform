import pytest
import asyncio
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch
from app.store.memory import InMemoryStateStore
from app.udp_server import TelemetryUDPProtocol


@pytest.fixture
def store():
    return InMemoryStateStore()


@pytest.mark.asyncio
async def test_recovery_on_new_udp_state(store):
    """
    Given a channel receives UDP telemetry after being marked inactive,
        When the batch is processed, Then is_active is set back to true.
    """
    now = datetime.now(timezone.utc)

    # 1. Setup inactive channel
    await store.update_channel_activity("ch-recover", 1, now - timedelta(seconds=10))
    await store.set_channel_inactive("ch-recover")

    ch = await store.get_channel("ch-recover")
    assert ch.is_active is False

    # 2. Simulate new UDP batch processing
    await store.update_channel_activity("ch-recover", 2, now)

    ch = await store.get_channel("ch-recover")
    assert ch.is_active is True, "Channel should be active after new UDP"
    assert ch.last_sequence == 2
