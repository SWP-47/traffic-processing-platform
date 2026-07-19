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
from services.reporting.handlers import (
    HostDetailsHandler,
    HostsTableHandler,
    HostTopDestinationsHandler,
    HostTopPortsHandler,
    TelemetryHandler,
)
from services.reporting.poller import PUSH_CHANNEL_PREFIX, Poller


async def refresh_telemetry_1s(conn):
    """
    Refreshes the telemetry_1s continuous aggregate with retries to handle
    LockNotAvailableError due to concurrent background refresh policies.
    """
    for attempt in range(5):
        try:
            await conn.execute(
                "CALL refresh_continuous_aggregate"
                "('telemetry_1s', NOW() - INTERVAL '1 hour', NOW() - INTERVAL '1 second')"
            )
            return
        except asyncpg.exceptions.LockNotAvailableError:
            if attempt == 4:
                raise
            await asyncio.sleep(0.1)


# --- Test Constants ---
TEST_CHANNEL_ID_SYNC = "integration-test-ch-sync"
TEST_CHANNEL_ID_ACTIVE = "integration-test-ch-active"
TEST_CHANNEL_ID_TIMEOUT = "integration-test-ch-timeout"
TEST_CHANNEL_ID_TELEMETRY = "integration-test-ch-telemetry"
TEST_CHANNEL_ID_TELEMETRY_PROTO = "integration-test-ch-telemetry-proto"
TEST_CHANNEL_ID_TELEMETRY_EMPTY = "integration-test-ch-telemetry-empty"
TEST_CHANNEL_ID_HOSTS = "integration-test-ch-hosts"
TEST_CHANNEL_ID_DETAILS = "integration-test-ch-details"
TEST_CHANNEL_ID_TOP_DEST = "integration-test-ch-top-dest"
TEST_CHANNEL_ID_TOP_PORTS = "integration-test-ch-top-ports"
TEST_CHANNEL_ID_SIMULATED = "integration-test-ch-simulated"


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
        await refresh_telemetry_1s(conn)

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


async def test_poller_executes_host_details_handler_and_publishes(redis_setup, db_pool_setup):
    """
    Architecture §2.2.2 & §4.4: Poller delegates query to HostDetailsHandler,
    which executes a query to get real-time Tx/Rx rates for a specific host.
    """
    redis = redis_setup
    db_pool = db_pool_setup
    query_hash = "integration-test-query-hash-details"
    listeners_key = f"{LISTENERS_KEY_PREFIX}{query_hash}"
    registry_key = f"{REGISTRY_KEY_PREFIX}{query_hash}"

    # Setup active hash and registry
    subscribe_json = json.dumps(
        {
            "action": "subscribe",
            "id": "sub-details-1",
            "channel_id": TEST_CHANNEL_ID_DETAILS,
            "target": "host_details",
            "params": {
                "host_ip": "192.168.1.100",
                "period_sec": 10.0,
            },
        }
    )
    await redis.set(registry_key, subscribe_json)
    await redis.sadd(ACTIVE_HASHES_KEY, query_hash)

    # Add active listener and session
    await redis.sadd(listeners_key, "client_poller:sub-details-1")
    await redis.hset(f"{SESSION_KEY_PREFIX}client_poller", "client_id", "client_poller")

    # Insert channel and packet flows into TimescaleDB
    now = datetime.now(timezone.utc)
    async with db_pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO channels (channel_id, is_active, dropped, last_activity_at) VALUES ($1, $2, $3, $4)",
            TEST_CHANNEL_ID_DETAILS,
            True,
            0,
            now,
        )

        # Insert raw packet flows:
        # tx_per_sec: 2 packets (src_ip = '192.168.1.100')
        # rx_per_sec: 1 packet (dst_ip = '192.168.1.100')
        await conn.execute(
            """
            INSERT INTO packet_flows (time, channel_id, direction, src_ip, dst_ip, src_port, dst_port, protocol)
            VALUES (NOW() - INTERVAL '2 seconds', $1, 1, '192.168.1.100', '8.8.8.8', 12345, 80, 'TCP'),
                   (NOW() - INTERVAL '2 seconds', $1, 1, '192.168.1.100', '8.8.8.8', 12346, 80, 'TCP'),
                   (NOW() - INTERVAL '3 seconds', $1, 0, '8.8.8.8', '192.168.1.100', 80, 12345, 'TCP')
            """,
            TEST_CHANNEL_ID_DETAILS,
        )

    # Set up Poller
    poller = Poller()
    handler = HostDetailsHandler()
    poller.register_handler("host_details", handler)

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
    assert payload["type"] == "host_details_update"
    assert payload["channel_id"] == TEST_CHANNEL_ID_DETAILS
    assert payload["host_ip"] == "192.168.1.100"
    # tx_per_sec = 2 packets / 10s = 0.2
    assert abs(payload["tx_per_sec"] - 0.2) < 0.0001
    # rx_per_sec = 1 packet / 10s = 0.1
    assert abs(payload["rx_per_sec"] - 0.1) < 0.0001


async def test_poller_executes_host_top_destinations_handler_and_publishes(redis_setup, db_pool_setup):
    """
    Architecture §2.2.2 & §4.4: Poller delegates query to HostTopDestinationsHandler,
    which aggregates top remote IPs communicating with host_ip and classifies them as LAN/WAN.
    """
    redis = redis_setup
    db_pool = db_pool_setup
    query_hash = "integration-test-query-hash-top-dest"
    listeners_key = f"{LISTENERS_KEY_PREFIX}{query_hash}"
    registry_key = f"{REGISTRY_KEY_PREFIX}{query_hash}"

    # Setup active hash and registry
    subscribe_json = json.dumps(
        {
            "action": "subscribe",
            "id": "sub-top-dest-1",
            "channel_id": TEST_CHANNEL_ID_TOP_DEST,
            "target": "host_top_destinations",
            "params": {
                "host_ip": "192.168.1.100",
                "period_sec": 10.0,
                "limit": 5,
            },
        }
    )
    await redis.set(registry_key, subscribe_json)
    await redis.sadd(ACTIVE_HASHES_KEY, query_hash)

    # Add active listener and session
    await redis.sadd(listeners_key, "client_poller:sub-top-dest-1")
    await redis.hset(f"{SESSION_KEY_PREFIX}client_poller", "client_id", "client_poller")

    # Insert channel and packet flows into TimescaleDB
    now = datetime.now(timezone.utc)
    async with db_pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO channels (channel_id, is_active, dropped, last_activity_at) VALUES ($1, $2, $3, $4)",
            TEST_CHANNEL_ID_TOP_DEST,
            True,
            0,
            now,
        )

        # Insert raw packet flows:
        # 1. 192.168.1.100 communicating with 8.8.8.8 (WAN) -> direction=1, src_ip='192.168.1.100', dst_ip='8.8.8.8'
        # 2. 192.168.1.100 communicating with 8.8.8.9 (WAN) -> direction=0, dst_ip='192.168.1.100', src_ip='8.8.8.9'
        await conn.execute(
            """
            INSERT INTO packet_flows (time, channel_id, direction, src_ip, dst_ip, src_port, dst_port, protocol)
            VALUES (NOW() - INTERVAL '2 seconds', $1, 1, '192.168.1.100', '8.8.8.8', 12345, 80, 'TCP'),
                   (NOW() - INTERVAL '2 seconds', $1, 0, '8.8.8.9', '192.168.1.100', 80, 12345, 'TCP')
            """,
            TEST_CHANNEL_ID_TOP_DEST,
        )

    # Set up Poller
    poller = Poller()
    handler = HostTopDestinationsHandler()
    poller.register_handler("host_top_destinations", handler)

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
    assert payload["type"] == "host_top_destinations_update"
    assert payload["channel_id"] == TEST_CHANNEL_ID_TOP_DEST
    assert payload["host_ip"] == "192.168.1.100"
    assert payload["total_count"] == 2

    destinations = payload["destinations"]
    assert len(destinations) == 2

    dest_ips = {d["ip"]: d for d in destinations}
    assert "8.8.8.8" in dest_ips
    assert "8.8.8.9" in dest_ips

    # Both remote IPs should be classified as WAN because they communicate across the bridge
    assert dest_ips["8.8.8.8"]["location"] == "WAN"
    assert dest_ips["8.8.8.9"]["location"] == "WAN"
    # received_per_sec = 1 packet / 10s = 0.1
    assert abs(dest_ips["8.8.8.8"]["received_per_sec"] - 0.1) < 0.0001
    assert abs(dest_ips["8.8.8.9"]["received_per_sec"] - 0.1) < 0.0001


async def test_poller_executes_host_top_ports_handler_and_publishes(redis_setup, db_pool_setup):
    """
    Architecture §2.2.2 & §4.4: Poller delegates query to HostTopPortsHandler,
    which aggregates top remote ports and protocols communicating with host_ip.
    """
    redis = redis_setup
    db_pool = db_pool_setup
    query_hash = "integration-test-query-hash-top-ports"
    listeners_key = f"{LISTENERS_KEY_PREFIX}{query_hash}"
    registry_key = f"{REGISTRY_KEY_PREFIX}{query_hash}"

    # Setup active hash and registry
    subscribe_json = json.dumps(
        {
            "action": "subscribe",
            "id": "sub-top-ports-1",
            "channel_id": TEST_CHANNEL_ID_TOP_PORTS,
            "target": "host_top_ports",
            "params": {
                "host_ip": "192.168.1.100",
                "period_sec": 10.0,
                "limit": 5,
            },
        }
    )
    await redis.set(registry_key, subscribe_json)
    await redis.sadd(ACTIVE_HASHES_KEY, query_hash)

    # Add active listener and session
    await redis.sadd(listeners_key, "client_poller:sub-top-ports-1")
    await redis.hset(f"{SESSION_KEY_PREFIX}client_poller", "client_id", "client_poller")

    # Insert channel and packet flows into TimescaleDB
    now = datetime.now(timezone.utc)
    async with db_pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO channels (channel_id, is_active, dropped, last_activity_at) VALUES ($1, $2, $3, $4)",
            TEST_CHANNEL_ID_TOP_PORTS,
            True,
            0,
            now,
        )

        # Insert raw packet flows:
        # 1. 192.168.1.100 (host) communicating with remote port 443 (TCP)
        # -> direction=1 (OUT), dst_port=443, protocol='TCP'
        # 2. 192.168.1.100 (host) communicating with remote port 53 (UDP)
        # -> direction=0 (IN), src_port=53, protocol='UDP'
        await conn.execute(
            """
            INSERT INTO packet_flows (time, channel_id, direction, src_ip, dst_ip, src_port, dst_port, protocol)
            VALUES (NOW() - INTERVAL '2 seconds', $1, 1, '192.168.1.100', '8.8.8.8', 12345, 443, 'TCP'),
                   (NOW() - INTERVAL '2 seconds', $1, 0, '8.8.8.8', '192.168.1.100', 53, 12345, 'UDP')
            """,
            TEST_CHANNEL_ID_TOP_PORTS,
        )

    # Set up Poller
    poller = Poller()
    handler = HostTopPortsHandler()
    poller.register_handler("host_top_ports", handler)

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
    assert payload["type"] == "host_top_ports_update"
    assert payload["channel_id"] == TEST_CHANNEL_ID_TOP_PORTS
    assert payload["host_ip"] == "192.168.1.100"
    assert payload["total_count"] == 2

    ports = payload["ports"]
    assert len(ports) == 2

    port_map = {p["port"]: p for p in ports}
    assert 443 in port_map
    assert 53 in port_map

    assert port_map[443]["protocol"] == "TCP"
    assert port_map[53]["protocol"] == "UDP"
    assert abs(port_map[443]["packets_per_sec"] - 0.1) < 0.0001
    assert abs(port_map[53]["packets_per_sec"] - 0.1) < 0.0001


async def test_telemetry_aggregation_across_protocols(redis_setup, db_pool_setup):
    """
    Architecture §2.2.2 & §3.1: Verify that TelemetryHandler correctly aggregates
    telemetry data across multiple protocols within the same 1-second buckets,
    using COUNT(DISTINCT bucket) for correct rate calculations.
    Also validates that the returned 'timestamp' matches the latest bucket time
    and 'received_at' is a valid current timestamp.
    """
    redis = redis_setup
    db_pool = db_pool_setup
    query_hash = "integration-test-query-hash-telemetry-proto"
    listeners_key = f"{LISTENERS_KEY_PREFIX}{query_hash}"
    registry_key = f"{REGISTRY_KEY_PREFIX}{query_hash}"

    # Setup active hash and registry
    subscribe_json = json.dumps(
        {
            "action": "subscribe",
            "id": "sub-telemetry-proto",
            "channel_id": TEST_CHANNEL_ID_TELEMETRY_PROTO,
            "target": "telemetry",
            "params": {"window_sec": 5.0},
        }
    )
    await redis.set(registry_key, subscribe_json)
    await redis.sadd(ACTIVE_HASHES_KEY, query_hash)

    # Add active listener and session
    await redis.sadd(listeners_key, "client_poller:sub-telemetry-proto")
    await redis.hset(f"{SESSION_KEY_PREFIX}client_poller", "client_id", "client_poller")

    # Insert channel and packet flows into TimescaleDB
    now = datetime.now(timezone.utc)
    async with db_pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO channels (channel_id, is_active, dropped, last_activity_at) VALUES ($1, $2, $3, $4)",
            TEST_CHANNEL_ID_TELEMETRY_PROTO,
            True,
            0,
            now,
        )

        # Insert raw packet flows with multiple protocols:
        # Bucket at NOW() - 2 seconds:
        #   - 1 TCP packet IN
        #   - 1 UDP packet IN
        #   - 1 TCP packet OUT
        # Bucket at NOW() - 3 seconds:
        #   - 1 UDP packet IN
        await conn.execute(
            """
            INSERT INTO packet_flows (time, channel_id, direction, src_ip, dst_ip, src_port, dst_port, protocol)
            VALUES (NOW() - INTERVAL '2 seconds', $1, 0, '192.168.1.10', '8.8.8.8', 12345, 80, 'TCP'),
                   (NOW() - INTERVAL '2 seconds', $1, 0, '192.168.1.11', '8.8.8.8', 12345, 53, 'UDP'),
                   (NOW() - INTERVAL '2 seconds', $1, 1, '8.8.8.8', '192.168.1.10', 80, 12345, 'TCP'),
                   (NOW() - INTERVAL '3 seconds', $1, 0, '192.168.1.11', '8.8.8.8', 12345, 53, 'UDP')
            """,
            TEST_CHANNEL_ID_TELEMETRY_PROTO,
        )

        # Manually refresh the continuous aggregate
        await refresh_telemetry_1s(conn)

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

    # Parse and validate message data
    payload = json.loads(msg["data"])
    assert payload["type"] == "telemetry_update"
    assert payload["channel_id"] == TEST_CHANNEL_ID_TELEMETRY_PROTO
    assert payload["is_active"] is True

    # Verify that the two buckets are counted as exactly 2 seconds of window
    assert payload["window_ms"] == 2000

    metrics = payload["metrics"]
    # packets_in: 2 in bucket -2s, 1 in bucket -3s -> total = 3
    assert metrics["direction_in"]["packets"] == 3
    # pps_in: 3 packets / 2s actual window = 1 pps
    assert metrics["direction_in"]["packets_per_sec"] == 1

    # packets_out: 1 in bucket -2s -> total = 1
    assert metrics["direction_out"]["packets"] == 1
    # pps_out: 1 packet / 2s actual window = 0 pps (integer division)
    assert metrics["direction_out"]["packets_per_sec"] == 0

    # Validate timestamps
    # 1. 'timestamp' should match the latest bucket time.
    timestamp_parsed = datetime.fromisoformat(payload["timestamp"])
    assert timestamp_parsed < datetime.now(timezone.utc)

    # 2. 'received_at' should be a valid timestamp representing current time
    received_at_parsed = datetime.fromisoformat(payload["received_at"])
    assert abs((received_at_parsed - datetime.now(timezone.utc)).total_seconds()) < 5.0


async def test_telemetry_aggregation_no_activity(redis_setup, db_pool_setup):
    """
    Architecture §2.2.2 & §3.1: Verify that when there is no packet activity in the window,
    TelemetryHandler returns zero counts/rates, window_ms is 0, and the 'timestamp'
    defaults to the current time.
    """
    redis = redis_setup
    db_pool = db_pool_setup
    query_hash = "integration-test-query-hash-telemetry-empty"
    listeners_key = f"{LISTENERS_KEY_PREFIX}{query_hash}"
    registry_key = f"{REGISTRY_KEY_PREFIX}{query_hash}"

    # Setup active hash and registry
    subscribe_json = json.dumps(
        {
            "action": "subscribe",
            "id": "sub-telemetry-empty",
            "channel_id": TEST_CHANNEL_ID_TELEMETRY_EMPTY,
            "target": "telemetry",
            "params": {"window_sec": 5.0},
        }
    )
    await redis.set(registry_key, subscribe_json)
    await redis.sadd(ACTIVE_HASHES_KEY, query_hash)

    # Add active listener and session
    await redis.sadd(listeners_key, "client_poller:sub-telemetry-empty")
    await redis.hset(f"{SESSION_KEY_PREFIX}client_poller", "client_id", "client_poller")

    # Insert channel with no packet flows into TimescaleDB
    now = datetime.now(timezone.utc)
    async with db_pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO channels (channel_id, is_active, dropped, last_activity_at) VALUES ($1, $2, $3, $4)",
            TEST_CHANNEL_ID_TELEMETRY_EMPTY,
            False,
            0,
            now,
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

    # Parse and validate message data
    payload = json.loads(msg["data"])
    assert payload["type"] == "telemetry_update"
    assert payload["channel_id"] == TEST_CHANNEL_ID_TELEMETRY_EMPTY
    assert payload["is_active"] is False
    assert payload["window_ms"] == 0
    assert payload["dropped_batches"] == 0

    metrics = payload["metrics"]
    assert metrics["direction_in"]["packets"] == 0
    assert metrics["direction_in"]["packets_per_sec"] == 0
    assert metrics["direction_out"]["packets"] == 0
    assert metrics["direction_out"]["packets_per_sec"] == 0

    # Without packets, timestamp should default to the current time (now)
    timestamp_parsed = datetime.fromisoformat(payload["timestamp"])
    assert abs((timestamp_parsed - datetime.now(timezone.utc)).total_seconds()) < 5.0


async def test_simulated_traffic_multi_subscription(redis_setup, db_pool_setup):
    """
    Architecture §2.2: Simulate 10 seconds of active traffic with two packets per second,
    then subscribe to 5 different targets (telemetry, hosts_table, host_details,
    host_top_destinations, host_top_ports) and verify that all handlers calculate
    correct aggregated data and timestamps.
    """
    redis = redis_setup
    db_pool = db_pool_setup

    # 1. Setup subscription requests, hashes, registry, and active listeners in Redis
    # We use a 12-second window/period to comfortably envelope the 10 seconds of traffic
    # (from NOW() - 11s to NOW() - 2s)
    # without hitting the NOW() - 1s end offset boundary of the telemetry continuous aggregate.
    targets = ["telemetry", "hosts_table", "host_details", "host_top_destinations", "host_top_ports"]
    query_hashes = {}

    for target in targets:
        params = {"period_sec": 12.0}
        if target == "telemetry":
            params = {"window_sec": 12.0}
        elif target in ["host_details", "host_top_destinations", "host_top_ports"]:
            params = {"host_ip": "192.168.1.10", "period_sec": 12.0, "limit": 10}

        subscribe_json = json.dumps(
            {
                "action": "subscribe",
                "id": f"sub-{target}-simulated",
                "channel_id": TEST_CHANNEL_ID_SIMULATED,
                "target": target,
                "params": params,
            }
        )
        query_hash = f"simulated-hash-{target}"
        query_hashes[target] = query_hash

        await redis.set(f"{REGISTRY_KEY_PREFIX}{query_hash}", subscribe_json)
        await redis.sadd(ACTIVE_HASHES_KEY, query_hash)

        # Add active listener and session
        await redis.sadd(f"{LISTENERS_KEY_PREFIX}{query_hash}", f"client_simulated:sub-{target}-simulated")

    await redis.hset(f"{SESSION_KEY_PREFIX}client_simulated", "client_id", "client_simulated")

    # 2. Insert channel and 10 seconds of simulated traffic in TimescaleDB
    # We insert 2 packets IN and 2 packets OUT for each second i in [2..11]
    now = datetime.now(timezone.utc)
    async with db_pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO channels (channel_id, is_active, dropped, last_activity_at) VALUES ($1, $2, $3, $4)",
            TEST_CHANNEL_ID_SIMULATED,
            True,
            0,
            now,
        )

        for i in range(2, 12):
            await conn.execute(
                f"""
                INSERT INTO packet_flows (time, channel_id, direction, src_ip, dst_ip, src_port, dst_port, protocol)
                VALUES (NOW() - INTERVAL '{i} seconds', $1, 0, '8.8.8.8', '192.168.1.10', 443, 12345, 'TCP'),
                       (NOW() - INTERVAL '{i} seconds', $1, 0, '8.8.8.9', '192.168.1.10', 53, 12345, 'UDP'),
                       (NOW() - INTERVAL '{i} seconds', $1, 1, '192.168.1.10', '8.8.8.8', 12345, 443, 'TCP'),
                       (NOW() - INTERVAL '{i} seconds', $1, 1, '192.168.1.10', '8.8.8.9', 12345, 53, 'UDP')
                """,
                TEST_CHANNEL_ID_SIMULATED,
            )

        # Manually refresh continuous aggregate
        await refresh_telemetry_1s(conn)

    # 3. Setup Poller and register all 5 handlers
    poller = Poller()
    poller.register_handler("telemetry", TelemetryHandler())
    poller.register_handler("hosts_table", HostsTableHandler())
    poller.register_handler("host_details", HostDetailsHandler())
    poller.register_handler("host_top_destinations", HostTopDestinationsHandler())
    poller.register_handler("host_top_ports", HostTopPortsHandler())

    # 4. Subscribe to Pub/Sub push channels pattern
    pubsub = redis.pubsub()
    await pubsub.psubscribe(f"{PUSH_CHANNEL_PREFIX}*")

    # 5. Run poller tick to execute all handlers and publish
    await poller._tick()

    # 6. Read and aggregate all 5 published messages
    received_payloads = {}
    try:
        async with asyncio.timeout(3.0):
            async for message in pubsub.listen():
                if message["type"] == "pmessage":
                    channel = message["channel"]
                    if isinstance(channel, bytes):
                        channel = channel.decode("utf-8")
                    query_hash = channel[len(PUSH_CHANNEL_PREFIX) :]

                    data = json.loads(message["data"])
                    received_payloads[query_hash] = data

                    if len(received_payloads) == 5:
                        break
    except asyncio.TimeoutError:
        pass

    assert len(received_payloads) == 5, f"Expected 5 messages, got {len(received_payloads)}"

    # 7. Validate telemetry payload
    telemetry_data = received_payloads[query_hashes["telemetry"]]
    assert telemetry_data["type"] == "telemetry_update"
    assert telemetry_data["channel_id"] == TEST_CHANNEL_ID_SIMULATED
    assert telemetry_data["window_ms"] == 10000  # 10 buckets = 10000ms
    assert telemetry_data["metrics"]["direction_in"]["packets"] == 20
    assert telemetry_data["metrics"]["direction_in"]["packets_per_sec"] == 2
    assert telemetry_data["metrics"]["direction_out"]["packets"] == 20
    assert telemetry_data["metrics"]["direction_out"]["packets_per_sec"] == 2

    # 8. Validate hosts_table payload
    hosts_data = received_payloads[query_hashes["hosts_table"]]
    assert hosts_data["type"] == "hosts_table_update"
    assert hosts_data["total_count"] == 3
    hosts_list = {h["ip"]: h for h in hosts_data["hosts"]}
    assert "192.168.1.10" in hosts_list
    assert hosts_list["192.168.1.10"]["location"] == "LAN"
    assert abs(hosts_list["192.168.1.10"]["tx_per_sec"] - (20.0 / 12.0)) < 0.0001
    assert abs(hosts_list["192.168.1.10"]["rx_per_sec"] - (20.0 / 12.0)) < 0.0001

    assert "8.8.8.8" in hosts_list
    assert hosts_list["8.8.8.8"]["location"] == "WAN"
    assert abs(hosts_list["8.8.8.8"]["tx_per_sec"] - (10.0 / 12.0)) < 0.0001
    assert abs(hosts_list["8.8.8.8"]["rx_per_sec"] - (10.0 / 12.0)) < 0.0001

    # 9. Validate host_details payload
    details_data = received_payloads[query_hashes["host_details"]]
    assert details_data["type"] == "host_details_update"
    assert details_data["host_ip"] == "192.168.1.10"
    assert abs(details_data["tx_per_sec"] - (20.0 / 12.0)) < 0.0001
    assert abs(details_data["rx_per_sec"] - (20.0 / 12.0)) < 0.0001

    # 10. Validate host_top_destinations payload
    dest_data = received_payloads[query_hashes["host_top_destinations"]]
    assert dest_data["type"] == "host_top_destinations_update"
    assert dest_data["total_count"] == 2
    dests = {d["ip"]: d for d in dest_data["destinations"]}
    assert "8.8.8.8" in dests
    assert dests["8.8.8.8"]["location"] == "WAN"
    assert abs(dests["8.8.8.8"]["received_per_sec"] - (20.0 / 12.0)) < 0.0001

    # 11. Validate host_top_ports payload
    ports_data = received_payloads[query_hashes["host_top_ports"]]
    assert ports_data["type"] == "host_top_ports_update"
    assert ports_data["total_count"] == 2
    ports_list = {p["port"]: p for p in ports_data["ports"]}
    assert 443 in ports_list
    assert ports_list[443]["protocol"] == "TCP"
    assert abs(ports_list[443]["packets_per_sec"] - (20.0 / 12.0)) < 0.0001
    assert 53 in ports_list
    assert ports_list[53]["protocol"] == "UDP"
    assert abs(ports_list[53]["packets_per_sec"] - (20.0 / 12.0)) < 0.0001


async def test_telemetry_packet_size_aggregation(redis_setup, db_pool_setup):
    """
    Architecture §2.2.2 & §4.3: Verify that the 'size' field from packet_flows
    is correctly aggregated into bytes_in/bytes_out in the telemetry_1s continuous
    aggregate, and that the TelemetryHandler returns accurate bytes_per_sec metrics.
    """
    redis = redis_setup
    db_pool = db_pool_setup
    query_hash = "integration-test-query-hash-telemetry-size"
    listeners_key = f"{LISTENERS_KEY_PREFIX}{query_hash}"
    registry_key = f"{REGISTRY_KEY_PREFIX}{query_hash}"

    # Setup active hash and registry
    subscribe_json = json.dumps(
        {
            "action": "subscribe",
            "id": "sub-telemetry-size",
            "channel_id": TEST_CHANNEL_ID_TELEMETRY,
            "target": "telemetry",
            "params": {"window_sec": 5.0},
        }
    )
    await redis.set(registry_key, subscribe_json)
    await redis.sadd(ACTIVE_HASHES_KEY, query_hash)

    # Add active listener and session
    await redis.sadd(listeners_key, "client_poller:sub-telemetry-size")
    await redis.hset(f"{SESSION_KEY_PREFIX}client_poller", "client_id", "client_poller")

    # Insert channel and packet flows with specific sizes:
    # direction=0 (IN): 2 packets with sizes 100 and 200 bytes -> bytes_in = 300
    # direction=1 (OUT): 1 packet with size 500 bytes -> bytes_out = 500
    now = datetime.now(timezone.utc)
    async with db_pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO channels (channel_id, is_active, dropped, last_activity_at) VALUES ($1, $2, $3, $4)",
            TEST_CHANNEL_ID_TELEMETRY,
            True,
            0,
            now,
        )

        await conn.execute(
            """
            INSERT INTO packet_flows (time, channel_id, direction, src_ip, dst_ip, src_port, dst_port, protocol, size)
            VALUES (NOW() - INTERVAL '2 seconds', $1, 0, '192.168.1.10', '8.8.8.8', 12345, 80, 'TCP', 100),
                   (NOW() - INTERVAL '2 seconds', $1, 0, '192.168.1.11', '8.8.8.8', 12345, 53, 'UDP', 200),
                   (NOW() - INTERVAL '2 seconds', $1, 1, '8.8.8.8', '192.168.1.10', 80, 12345, 'TCP', 500)
            """,
            TEST_CHANNEL_ID_TELEMETRY,
        )

        await refresh_telemetry_1s(conn)

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

    # Parse and validate message data
    payload = json.loads(msg["data"])
    assert payload["type"] == "telemetry_update"
    assert payload["channel_id"] == TEST_CHANNEL_ID_TELEMETRY

    metrics = payload["metrics"]

    # bytes_in: 100 + 200 = 300 bytes
    assert metrics["direction_in"]["bytes"] == 300
    # bytes_per_sec: 300 / 1s = 300 bps (1 bucket at NOW()-2s)
    assert metrics["direction_in"]["bytes_per_sec"] == 300

    # bytes_out: 500 bytes
    assert metrics["direction_out"]["bytes"] == 500
    # bytes_per_sec: 500 / 1s = 500 bps
    assert metrics["direction_out"]["bytes_per_sec"] == 500

    # Verify packet counts still correct
    assert metrics["direction_in"]["packets"] == 2
    assert metrics["direction_out"]["packets"] == 1


async def test_telemetry_packet_size_across_multiple_buckets(redis_setup, db_pool_setup):
    """
    Architecture §2.2.2: Verify that packet sizes are correctly aggregated across
    multiple 1-second buckets in telemetry_1s, and that bytes_per_sec is calculated
    using the actual bucket count.
    """
    redis = redis_setup
    db_pool = db_pool_setup
    query_hash = "integration-test-query-hash-telemetry-size-multi"
    listeners_key = f"{LISTENERS_KEY_PREFIX}{query_hash}"
    registry_key = f"{REGISTRY_KEY_PREFIX}{query_hash}"

    # Setup active hash and registry
    subscribe_json = json.dumps(
        {
            "action": "subscribe",
            "id": "sub-telemetry-size-multi",
            "channel_id": TEST_CHANNEL_ID_TELEMETRY_PROTO,
            "target": "telemetry",
            "params": {"window_sec": 5.0},
        }
    )
    await redis.set(registry_key, subscribe_json)
    await redis.sadd(ACTIVE_HASHES_KEY, query_hash)

    # Add active listener and session
    await redis.sadd(listeners_key, "client_poller:sub-telemetry-size-multi")
    await redis.hset(f"{SESSION_KEY_PREFIX}client_poller", "client_id", "client_poller")

    # Insert packet flows across multiple buckets with varying sizes:
    # Bucket at NOW() - 2 seconds:
    #   - 2 IN packets: size 150 + 250 = 400 bytes
    #   - 1 OUT packet: size 300 bytes
    # Bucket at NOW() - 3 seconds:
    #   - 1 IN packet: size 100 bytes
    # Total IN bytes: 500, Total OUT bytes: 300
    # Actual window: 2 buckets = 2 seconds
    # bytes_per_sec IN: 500 / 2 = 250, bytes_per_sec OUT: 300 / 2 = 150
    now = datetime.now(timezone.utc)
    async with db_pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO channels (channel_id, is_active, dropped, last_activity_at) VALUES ($1, $2, $3, $4)",
            TEST_CHANNEL_ID_TELEMETRY_PROTO,
            True,
            0,
            now,
        )

        await conn.execute(
            """
            INSERT INTO packet_flows (time, channel_id, direction, src_ip, dst_ip, src_port, dst_port, protocol, size)
            VALUES (NOW() - INTERVAL '2 seconds', $1, 0, '192.168.1.10', '8.8.8.8', 12345, 80, 'TCP', 150),
                   (NOW() - INTERVAL '2 seconds', $1, 0, '192.168.1.11', '8.8.8.8', 12345, 53, 'UDP', 250),
                   (NOW() - INTERVAL '2 seconds', $1, 1, '8.8.8.8', '192.168.1.10', 80, 12345, 'TCP', 300),
                   (NOW() - INTERVAL '3 seconds', $1, 0, '192.168.1.11', '8.8.8.8', 12345, 53, 'UDP', 100)
            """,
            TEST_CHANNEL_ID_TELEMETRY_PROTO,
        )

        await refresh_telemetry_1s(conn)

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

    # Parse and validate message data
    payload = json.loads(msg["data"])
    assert payload["type"] == "telemetry_update"
    assert payload["channel_id"] == TEST_CHANNEL_ID_TELEMETRY_PROTO

    metrics = payload["metrics"]

    # Verify window is 2 seconds (2 buckets)
    assert payload["window_ms"] == 2000

    # Total bytes
    assert metrics["direction_in"]["bytes"] == 500
    assert metrics["direction_out"]["bytes"] == 300

    # bytes_per_sec calculated using actual bucket count (2 seconds)
    assert metrics["direction_in"]["bytes_per_sec"] == 250
    assert metrics["direction_out"]["bytes_per_sec"] == 150

    # Verify packet counts
    assert metrics["direction_in"]["packets"] == 3
    assert metrics["direction_out"]["packets"] == 1
