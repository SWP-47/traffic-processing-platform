# ==============================================================================
# CnSS Reporting Worker Integration Tests
# Validates the background aggregation, channel state synchronization, and ghost
# subscription cleanup against a live Redis instance and TimescaleDB database.
# Requires Redis and TimescaleDB to be running (e.g., via `make dev`).
# ==============================================================================

import asyncio
import json
import time
from datetime import datetime, timedelta, timezone

import asyncpg
import pytest

from core.config import settings
from core.database import close_db_pool, get_db_pool, init_db_pool
from core.redis.client import close_redis_client, get_redis_client, init_redis_client
from services.reporting.channel_state_syncer import STATE_KEY_PREFIX, ChannelStateSyncer
from services.reporting.ghost_cleaner import (
    ACTIVE_HASHES_KEY,
    LISTENERS_KEY_PREFIX,
    REGISTRY_KEY_PREFIX,
    SESSION_KEY_PREFIX,
    GhostCleaner,
)
from services.reporting.handlers.hosts_table_handler import HostsTableHandler
from services.reporting.handlers.telemetry_handler import TelemetryHandler
from services.reporting.poller import PUSH_CHANNEL_PREFIX, Poller

# --- Test Constants ---
TEST_CHANNEL_ID_SYNC = "integration-test-ch-sync"
TEST_CHANNEL_ID_ACTIVE = "integration-test-ch-active"
TEST_CHANNEL_ID_TIMEOUT = "integration-test-ch-timeout"
TEST_CHANNEL_ID_TELEMETRY = "integration-test-ch-telemetry"
TEST_CHANNEL_ID_HOSTS = "integration-test-ch-hosts"


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

    # Clean up any leftover data from previous runs
    await redis.flushdb()

    yield redis

    # Teardown: Clean up after the test has run
    await redis.flushdb()

    # Close the client to release resources and reset global state
    await close_redis_client()


@pytest.fixture
async def db_pool_setup():
    """
    Initializes the global TimescaleDB connection pool for the test.
    Cleans up any test-specific channel records before and after tests.
    Uses function scope to align with the asyncio loop lifecycle of each test.
    """
    await init_db_pool()
    pool = get_db_pool()

    # Clean up test-specific channels
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM packet_flows WHERE channel_id LIKE 'integration-test-%'")
        await conn.execute("DELETE FROM channels WHERE channel_id LIKE 'integration-test-%'")

    yield pool

    # Teardown: clean up test-specific channels
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM packet_flows WHERE channel_id LIKE 'integration-test-%'")
        await conn.execute("DELETE FROM channels WHERE channel_id LIKE 'integration-test-%'")

    await close_db_pool()


# --- Channel State Syncer Integration Tests ---
async def test_channel_state_syncer_syncs_active_channel(redis_setup, db_pool_setup):
    """
    Architecture §2.2.7 & §2.2.9: The channel state syncer must scan Redis for
    active channels, read and atomically reset their dropped_delta via Lua script,
    and update the corresponding row in TimescaleDB with is_active=TRUE,
    the exact last_activity_at timestamp, and the accumulated dropped packet count.
    """
    redis = redis_setup
    db_pool = db_pool_setup
    state_key = f"{STATE_KEY_PREFIX}{TEST_CHANNEL_ID_SYNC}"

    # Verify channel is not in DB originally
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM channels WHERE channel_id = $1", TEST_CHANNEL_ID_SYNC)
        assert row is None

    # Setup Redis state
    now_ts = int(time.time())
    last_activity_dt = datetime.fromtimestamp(now_ts, tz=timezone.utc)

    await redis.hset(
        state_key,
        mapping={
            "last_activity_at": str(now_ts),
            "dropped_delta": "42",
            "is_active": "1",
        },
    )

    # Run syncer cycle
    syncer = ChannelStateSyncer()
    await syncer._sync_cycle()

    # Verify database was updated
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM channels WHERE channel_id = $1", TEST_CHANNEL_ID_SYNC)
        assert row is not None
        assert row["is_active"] is True
        assert row["dropped"] == 42
        assert abs((row["last_activity_at"] - last_activity_dt).total_seconds()) < 1.0

    # Verify Redis dropped_delta was reset to 0 by the Lua script
    dropped_delta = await redis.hget(state_key, "dropped_delta")
    assert int(dropped_delta) == 0


async def test_channel_state_syncer_mass_timeout_deactivation(redis_setup, db_pool_setup):
    """
    Architecture §2.2.7: The channel state syncer must execute a single mass UPDATE query
    to set is_active=FALSE for all channels that are currently marked is_active=TRUE but
    whose last_activity_at is older than the timeout threshold.
    """
    db_pool = db_pool_setup

    now = datetime.now(timezone.utc)
    active_time = now - timedelta(seconds=1)
    # 10s is older than activity_timeout_ms (default 5s)
    timeout_time = now - timedelta(seconds=10)

    # Insert both channels in the DB as active
    async with db_pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO channels (channel_id, is_active, dropped, last_activity_at) VALUES ($1, $2, $3, $4)",
            TEST_CHANNEL_ID_ACTIVE,
            True,
            0,
            active_time,
        )
        await conn.execute(
            "INSERT INTO channels (channel_id, is_active, dropped, last_activity_at) VALUES ($1, $2, $3, $4)",
            TEST_CHANNEL_ID_TIMEOUT,
            True,
            0,
            timeout_time,
        )

    # Run syncer mass-deactivation
    syncer = ChannelStateSyncer()
    deactivated = await syncer._deactivate_timed_out_channels()
    assert deactivated == 1

    # Verify database state
    async with db_pool.acquire() as conn:
        row_active = await conn.fetchrow("SELECT * FROM channels WHERE channel_id = $1", TEST_CHANNEL_ID_ACTIVE)
        assert row_active["is_active"] is True

        row_timeout = await conn.fetchrow("SELECT * FROM channels WHERE channel_id = $1", TEST_CHANNEL_ID_TIMEOUT)
        assert row_timeout["is_active"] is False
        # Verify last_activity_at was preserved
        assert abs((row_timeout["last_activity_at"] - timeout_time).total_seconds()) < 1.0


# --- Ghost Cleaner Integration Tests ---
async def test_ghost_cleaner_removes_stale_listeners(redis_setup):
    """
    Architecture §2.2.8 & §2.2.10: GhostCleaner validates each client in a subscription's
    listener set against its ephemeral session key ws:session:{client_id}.
    Stale listener entries are SREM'd. If the listener set becomes empty, the subscription
    registry and active hash index entries are deleted.
    """
    redis = redis_setup
    query_hash = "integration-test-query-hash-1"
    listeners_key = f"{LISTENERS_KEY_PREFIX}{query_hash}"
    registry_key = f"{REGISTRY_KEY_PREFIX}{query_hash}"

    # Setup registry
    subscribe_json = json.dumps(
        {
            "action": "subscribe",
            "id": "sub-1",
            "channel_id": "integration-test-ch",
            "target": "telemetry",
            "params": {},
        }
    )
    await redis.set(registry_key, subscribe_json)
    await redis.sadd(ACTIVE_HASHES_KEY, query_hash)

    # Setup listeners: client_1 (active session), client_2 (no session/stale)
    await redis.sadd(listeners_key, "client_1:sub-1", "client_2:sub-2")

    # Set up session for client_1
    await redis.hset(f"{SESSION_KEY_PREFIX}client_1", "client_id", "client_1")
    # client_2 has no session key set

    cleaner = GhostCleaner()
    await cleaner._scan_and_clean()

    # client_2:sub-2 should be removed, but client_1:sub-1 should remain.
    # Registry and active hashes must remain because client_1 is active.
    listeners = await redis.smembers(listeners_key)
    assert "client_1:sub-1" in listeners
    assert "client_2:sub-2" not in listeners
    assert len(listeners) == 1

    assert await redis.exists(registry_key) == 1
    assert query_hash in await redis.smembers(ACTIVE_HASHES_KEY)

    # Now remove client_1's session key (marking them stale/ghost too)
    await redis.delete(f"{SESSION_KEY_PREFIX}client_1")

    # Run cleanup again
    await cleaner._scan_and_clean()

    # The subscription should be fully cleaned up
    assert await redis.exists(listeners_key) == 0
    assert await redis.exists(registry_key) == 0
    assert query_hash not in await redis.smembers(ACTIVE_HASHES_KEY)


# --- Poller & Subscription Handler Integration Tests ---
async def test_poller_skips_when_no_active_listeners(redis_setup, db_pool_setup):
    """
    Architecture §2.2.5: Before executing SQL, the Poller checks if any WebSocket
    clients are listening. If no clients are listening, the SQL query is skipped.
    """
    redis = redis_setup
    query_hash = "integration-test-query-hash-skip"
    registry_key = f"{REGISTRY_KEY_PREFIX}{query_hash}"

    # Setup active hash and registry
    subscribe_json = json.dumps(
        {
            "action": "subscribe",
            "id": "sub-1",
            "channel_id": TEST_CHANNEL_ID_TELEMETRY,
            "target": "telemetry",
            "params": {"window_sec": 5.0},
        }
    )
    await redis.set(registry_key, subscribe_json)
    await redis.sadd(ACTIVE_HASHES_KEY, query_hash)
    # Do NOT add any listeners to the set

    # Setup custom poller
    poller = Poller()
    handler = TelemetryHandler()
    poller.register_handler("telemetry", handler)

    # Run poller tick
    # We can subscribe to the Redis push channel and verify no messages are published.
    pubsub = redis.pubsub()
    await pubsub.subscribe(f"{PUSH_CHANNEL_PREFIX}{query_hash}")

    await poller._tick()

    # Verify no message was published
    msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=0.1)
    assert msg is None


async def test_poller_executes_telemetry_handler_and_publishes(redis_setup, db_pool_setup):
    """
    Architecture §2.2.1, §2.2.2, §2.2.3 & §2.2.6: Poller detects active hash,
    validates listener exists, retrieves registry, delegates query to TelemetryHandler,
    and publishes the aggregated metric update payload to Redis Pub/Sub.
    """
    redis = redis_setup
    db_pool = db_pool_setup
    query_hash = "integration-test-query-hash-telemetry"
    listeners_key = f"{LISTENERS_KEY_PREFIX}{query_hash}"
    registry_key = f"{REGISTRY_KEY_PREFIX}{query_hash}"

    # Setup active hash and registry
    subscribe_json = json.dumps(
        {
            "action": "subscribe",
            "id": "sub-telemetry-1",
            "channel_id": TEST_CHANNEL_ID_TELEMETRY,
            "target": "telemetry",
            "params": {"window_sec": 5.0},
        }
    )
    await redis.set(registry_key, subscribe_json)
    await redis.sadd(ACTIVE_HASHES_KEY, query_hash)

    # Add active listener and session
    await redis.sadd(listeners_key, "client_poller:sub-telemetry-1")
    await redis.hset(f"{SESSION_KEY_PREFIX}client_poller", "client_id", "client_poller")

    # Insert channel and packet flows into TimescaleDB
    now = datetime.now(timezone.utc)
    async with db_pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO channels (channel_id, is_active, dropped, last_activity_at) VALUES ($1, $2, $3, $4)",
            TEST_CHANNEL_ID_TELEMETRY,
            True,
            0,
            now,
        )

        # Insert raw packet flows in the last few seconds
        await conn.execute(
            """
            INSERT INTO packet_flows (time, channel_id, direction, src_ip, dst_ip, src_port, dst_port, protocol)
            VALUES (NOW() - INTERVAL '2 seconds', $1, 0, '192.168.1.10', '8.8.8.8', 12345, 80, 'TCP'),
                   (NOW() - INTERVAL '2 seconds', $1, 1, '8.8.8.8', '192.168.1.10', 80, 12345, 'TCP'),
                   (NOW() - INTERVAL '3 seconds', $1, 0, '192.168.1.10', '8.8.8.8', 12345, 80, 'TCP')
            """,
            TEST_CHANNEL_ID_TELEMETRY,
        )

        # Manually refresh the continuous aggregate so telemetry_1s reflects the inserted rows
        await conn.execute(
            "CALL refresh_continuous_aggregate('telemetry_1s', NOW() - INTERVAL '1 hour', NOW() - INTERVAL '1 second')"
        )

    # Set up Poller
    poller = Poller()
    handler = TelemetryHandler()
    poller.register_handler("telemetry", handler)

    # Setup Pub/Sub listener
    pubsub = redis.pubsub()
    await pubsub.subscribe(f"{PUSH_CHANNEL_PREFIX}{query_hash}")

    # Run poller tick
    await poller._tick()

    # Get published message
    msg = None
    try:
        async with asyncio.timeout(2.0):
            async for message in pubsub.listen():
                if message["type"] == "message":
                    msg = message
                    break
    except asyncio.TimeoutError:
        pass

    assert msg is not None

    # Parse message data
    payload = json.loads(msg["data"])
    assert payload["type"] == "telemetry_update"
    assert payload["channel_id"] == TEST_CHANNEL_ID_TELEMETRY
    assert payload["is_active"] is True
    # The actual window should match the bucket count in DB.
    # In our inserted data, buckets are at NOW() - 2 seconds and NOW() - 3 seconds,
    # so bucket_count = 2, representing a 2.0-second actual window.
    assert payload["window_ms"] == 2000
    assert payload["dropped_batches"] == 0

    metrics = payload["metrics"]
    # 2 packets in (one at NOW()-2s, one at NOW()-3s) / 2s window = 1 pps
    assert metrics["direction_in"]["packets"] == 2
    assert metrics["direction_in"]["packets_per_sec"] == 1
    # 1 packet out (at NOW()-2s) / 2s window = 0 pps (since integer division 1/2 = 0)
    assert metrics["direction_out"]["packets"] == 1
    assert metrics["direction_out"]["packets_per_sec"] == 0


async def test_poller_executes_hosts_table_handler_and_publishes(redis_setup, db_pool_setup):
    """
    Architecture §2.2.2 & §4.4: Poller delegates query to HostsTableHandler,
    which executes a dynamic SQL query directly against the raw packet_flows hypertable
    to retrieve paginated hosts list, classified by LAN/WAN location, and publishes to Redis.
    """
    redis = redis_setup
    db_pool = db_pool_setup
    query_hash = "integration-test-query-hash-hosts"
    listeners_key = f"{LISTENERS_KEY_PREFIX}{query_hash}"
    registry_key = f"{REGISTRY_KEY_PREFIX}{query_hash}"

    # Setup active hash and registry
    subscribe_json = json.dumps(
        {
            "action": "subscribe",
            "id": "sub-hosts-1",
            "channel_id": TEST_CHANNEL_ID_HOSTS,
            "target": "hosts_table",
            "params": {
                "period_sec": 10.0,
                "limit": 10,
            },
        }
    )
    await redis.set(registry_key, subscribe_json)
    await redis.sadd(ACTIVE_HASHES_KEY, query_hash)

    # Add active listener and session
    await redis.sadd(listeners_key, "client_poller:sub-hosts-1")
    await redis.hset(f"{SESSION_KEY_PREFIX}client_poller", "client_id", "client_poller")

    # Insert channel and packet flows into TimescaleDB
    now = datetime.now(timezone.utc)
    async with db_pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO channels (channel_id, is_active, dropped, last_activity_at) VALUES ($1, $2, $3, $4)",
            TEST_CHANNEL_ID_HOSTS,
            True,
            0,
            now,
        )

        # Insert raw packet flows in the last few seconds
        # direction=0: packets_in (dst_ip '192.168.1.100' is LAN, src_ip '8.8.8.8' is WAN)
        # direction=1: packets_out (src_ip '192.168.1.100' is LAN, dst_ip '8.8.8.8' is WAN)
        await conn.execute(
            """
            INSERT INTO packet_flows (time, channel_id, direction, src_ip, dst_ip, src_port, dst_port, protocol)
            VALUES (NOW() - INTERVAL '2 seconds', $1, 0, '8.8.8.8', '192.168.1.100', 80, 12345, 'TCP'),
                   (NOW() - INTERVAL '2 seconds', $1, 1, '192.168.1.100', '8.8.8.8', 12345, 80, 'TCP')
            """,
            TEST_CHANNEL_ID_HOSTS,
        )

    # Set up Poller
    poller = Poller()
    handler = HostsTableHandler()
    poller.register_handler("hosts_table", handler)

    # Setup Pub/Sub listener
    pubsub = redis.pubsub()
    await pubsub.subscribe(f"{PUSH_CHANNEL_PREFIX}{query_hash}")

    # Run poller tick
    await poller._tick()

    # Get published message
    msg = None
    try:
        async with asyncio.timeout(2.0):
            async for message in pubsub.listen():
                if message["type"] == "message":
                    msg = message
                    break
    except asyncio.TimeoutError:
        pass

    assert msg is not None

    # Parse message data
    payload = json.loads(msg["data"])
    assert payload["type"] == "hosts_table_update"
    assert payload["channel_id"] == TEST_CHANNEL_ID_HOSTS
    assert payload["target"] == "hosts_table"
    assert payload["total_count"] == 2

    # Verify LAN/WAN classification
    hosts = payload["hosts"]
    assert len(hosts) == 2

    host_ips = {h["ip"]: h for h in hosts}
    assert "192.168.1.100" in host_ips
    assert "8.8.8.8" in host_ips

    assert host_ips["192.168.1.100"]["location"] == "LAN"
    assert host_ips["8.8.8.8"]["location"] == "WAN"
