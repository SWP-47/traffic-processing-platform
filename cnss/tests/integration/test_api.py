# ==============================================================================
# CnSS REST API & Authentication Integration Tests
# Validates HTTP authentication endpoints (login, refresh, logout), discovery
# scopes (/channels, /status), and historical data retrieval (/history)
# against a live TimescaleDB and Redis instance.
# Requires Redis and TimescaleDB to be running (e.g., via `make dev`).
# ==============================================================================

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient

from core.database import close_db_pool, get_db_pool, init_db_pool
from core.redis.client import close_redis_client, get_redis_client, init_redis_client
from core.security.passwords import hash_password
from services.api.main import app


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
TEST_VIEWER_USERNAME = "test-viewer"
TEST_ADMIN_USERNAME = "test-admin"
TEST_PASSWORD = "password123"
TEST_CHANNEL_API_1 = "integration-test-ch-api-1"
TEST_CHANNEL_API_2 = "integration-test-ch-api-2"


# --- Fixtures ---
@pytest.fixture
async def redis_setup():
    """
    Initializes the global Redis client for the test.
    Ensures a clean state by flushing Redis before and after the test.
    """
    await close_redis_client()
    await init_redis_client()
    redis = get_redis_client()
    await redis.flushdb()

    yield redis

    await redis.flushdb()
    await close_redis_client()


@pytest.fixture
async def db_pool_setup():
    """
    Initializes the global TimescaleDB connection pool for the test.
    Cleans up any test-specific user and channel records before and after tests.
    """
    await init_db_pool()
    pool = get_db_pool()

    # Initial cleanup
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM user_channel_scopes WHERE channel_id LIKE 'integration-test-%'")
        await conn.execute("DELETE FROM users WHERE username LIKE 'test-%'")
        await conn.execute("DELETE FROM packet_flows WHERE channel_id LIKE 'integration-test-%'")
        await conn.execute("DELETE FROM channels WHERE channel_id LIKE 'integration-test-%'")

    yield pool

    # Teardown cleanup
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM user_channel_scopes WHERE channel_id LIKE 'integration-test-%'")
        await conn.execute("DELETE FROM users WHERE username LIKE 'test-%'")
        await conn.execute("DELETE FROM packet_flows WHERE channel_id LIKE 'integration-test-%'")
        await conn.execute("DELETE FROM channels WHERE channel_id LIKE 'integration-test-%'")

    await close_db_pool()


@pytest.fixture
async def api_client():
    """
    Provides an httpx.AsyncClient instance for calling FastAPI endpoints.
    Uses 'https' scheme so that httpx accepts and sends back 'Secure' cookies.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="https://test") as client:
        yield client


# --- Integration Tests ---


async def test_api_login_success_viewer(redis_setup, db_pool_setup, api_client):
    """
    Architecture §2.4 & §5.1: Test successful login for a viewer.
    Validates password verification, JWT scope retrieval, access token generation,
    and refresh token HttpOnly cookie configuration.
    """
    db_pool = db_pool_setup
    viewer_id = uuid.uuid4()

    # Seed test database
    async with db_pool.acquire() as conn:
        # Create user
        pwd_hash = hash_password(TEST_PASSWORD)
        await conn.execute(
            "INSERT INTO users (id, username, password_hash, role) VALUES ($1, $2, $3, $4)",
            viewer_id,
            TEST_VIEWER_USERNAME,
            pwd_hash,
            "viewer",
        )
        # Create channels
        await conn.execute(
            "INSERT INTO channels (channel_id, is_active) VALUES ($1, $2), ($3, $4)",
            TEST_CHANNEL_API_1,
            True,
            TEST_CHANNEL_API_2,
            False,
        )
        # Grant scope for channel 1 only
        await conn.execute(
            "INSERT INTO user_channel_scopes (user_id, channel_id) VALUES ($1, $2)", viewer_id, TEST_CHANNEL_API_1
        )

    # Call Login Endpoint
    response = await api_client.post(
        "/api/v1/auth/login", json={"username": TEST_VIEWER_USERNAME, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200
    data = response.json()

    # Verify Response Body
    assert data["token_type"] == "Bearer"
    assert "access_token" in data
    assert data["role"] == "viewer"
    assert data["scope"] == [TEST_CHANNEL_API_1]

    # Verify HttpOnly Cookie
    assert "refresh_token" in response.cookies
    refresh_cookie = response.cookies.get("refresh_token")
    assert refresh_cookie is not None


async def test_api_login_success_admin(redis_setup, db_pool_setup, api_client):
    """
    Architecture §2.4 & §5.1: Test successful login for an admin.
    Verifies that admin role receives scopes for all registered channels automatically.
    """
    db_pool = db_pool_setup
    admin_id = uuid.uuid4()

    # Seed test database
    async with db_pool.acquire() as conn:
        pwd_hash = hash_password(TEST_PASSWORD)
        await conn.execute(
            "INSERT INTO users (id, username, password_hash, role) VALUES ($1, $2, $3, $4)",
            admin_id,
            TEST_ADMIN_USERNAME,
            pwd_hash,
            "admin",
        )
        await conn.execute(
            "INSERT INTO channels (channel_id, is_active) VALUES ($1, $2), ($3, $4)",
            TEST_CHANNEL_API_1,
            True,
            TEST_CHANNEL_API_2,
            False,
        )

    response = await api_client.post(
        "/api/v1/auth/login", json={"username": TEST_ADMIN_USERNAME, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "admin"
    # Admin has all registered channels in their scope (subset assertion to accommodate existing DB seeding)
    assert {TEST_CHANNEL_API_1, TEST_CHANNEL_API_2}.issubset(set(data["scope"]))


async def test_api_login_invalid_credentials(redis_setup, db_pool_setup, api_client):
    """
    Architecture §6.1: Validates that invalid username or password returns
    401 status with standardized 'invalid_credentials' JSON schema.
    """
    # Try logging in with user that doesn't exist
    response = await api_client.post(
        "/api/v1/auth/login", json={"username": "non-existent-user", "password": TEST_PASSWORD}
    )
    assert response.status_code == 401
    assert response.json() == {"error": "invalid_credentials", "message": "Invalid username or password."}


async def test_api_token_refresh_lifecycle(redis_setup, db_pool_setup, api_client):
    """
    Architecture §5.3: Test full token refresh lifecycle including access token renewal,
    token revocation on logout, and blocking subsequent refresh attempts using blacklisted JTI.
    """
    db_pool = db_pool_setup
    viewer_id = uuid.uuid4()

    # Seed test database
    async with db_pool.acquire() as conn:
        pwd_hash = hash_password(TEST_PASSWORD)
        await conn.execute(
            "INSERT INTO users (id, username, password_hash, role) VALUES ($1, $2, $3, $4)",
            viewer_id,
            TEST_VIEWER_USERNAME,
            pwd_hash,
            "viewer",
        )

    # 1. Login to get cookies
    login_response = await api_client.post(
        "/api/v1/auth/login", json={"username": TEST_VIEWER_USERNAME, "password": TEST_PASSWORD}
    )
    assert login_response.status_code == 200
    initial_access_token = login_response.json()["access_token"]
    assert "refresh_token" in login_response.cookies

    # 2. Refresh access token
    refresh_response = await api_client.post("/api/v1/auth/refresh")
    assert refresh_response.status_code == 200
    refresh_data = refresh_response.json()
    assert "access_token" in refresh_data
    assert refresh_data["access_token"] != initial_access_token

    # 3. Logout (revokes refresh token JTI in Redis)
    logout_response = await api_client.post("/api/v1/auth/logout")
    assert logout_response.status_code == 200
    assert logout_response.json() == {"message": "Successfully logged out."}

    # Verify cookie Max-Age cleared
    # In httpx AsyncClient, subsequent requests won't automatically send the cookie if it is deleted.
    refresh_response_2 = await api_client.post("/api/v1/auth/refresh")
    assert refresh_response_2.status_code == 401
    assert refresh_response_2.json()["error"] == "unauthorized"


async def test_api_channels_scope_filtering(redis_setup, db_pool_setup, api_client):
    """
    Architecture §5.1: Test that GET /api/v1/channels correctly filters returned
    channels based on the authenticated user's role and scopes.
    """
    db_pool = db_pool_setup
    viewer_id = uuid.uuid4()
    admin_id = uuid.uuid4()

    # Seed test database
    async with db_pool.acquire() as conn:
        pwd_hash = hash_password(TEST_PASSWORD)
        await conn.execute(
            "INSERT INTO users (id, username, password_hash, role) VALUES ($1, $2, $3, $4), ($5, $6, $7, $8)",
            viewer_id,
            TEST_VIEWER_USERNAME,
            pwd_hash,
            "viewer",
            admin_id,
            TEST_ADMIN_USERNAME,
            pwd_hash,
            "admin",
        )
        await conn.execute(
            "INSERT INTO channels (channel_id, is_active) VALUES ($1, $2), ($3, $4)",
            TEST_CHANNEL_API_1,
            True,
            TEST_CHANNEL_API_2,
            False,
        )
        await conn.execute(
            "INSERT INTO user_channel_scopes (user_id, channel_id) VALUES ($1, $2)", viewer_id, TEST_CHANNEL_API_1
        )

    # 1. Login as Viewer
    login_viewer = await api_client.post(
        "/api/v1/auth/login", json={"username": TEST_VIEWER_USERNAME, "password": TEST_PASSWORD}
    )
    viewer_token = login_viewer.json()["access_token"]

    # Request channels list as Viewer
    headers = {"Authorization": f"Bearer {viewer_token}"}
    response = await api_client.get("/api/v1/channels", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["channels"][0]["channel_id"] == TEST_CHANNEL_API_1

    # 2. Login as Admin
    login_admin = await api_client.post(
        "/api/v1/auth/login", json={"username": TEST_ADMIN_USERNAME, "password": TEST_PASSWORD}
    )
    admin_token = login_admin.json()["access_token"]

    # Request channels list as Admin
    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    response_admin = await api_client.get("/api/v1/channels", headers=headers_admin)
    assert response_admin.status_code == 200
    data_admin = response_admin.json()
    assert data_admin["total"] >= 2
    channel_ids = {c["channel_id"] for c in data_admin["channels"]}
    assert {TEST_CHANNEL_API_1, TEST_CHANNEL_API_2}.issubset(channel_ids)


async def test_api_channel_status_access_control(redis_setup, db_pool_setup, api_client):
    """
    Architecture §2.4 & §5.1: Test GET /api/v1/channel/{channel_id}/status endpoint.
    Asserts 200 on successful authorized access, 403 on scope mismatch, and 404 when channel does not exist in registry.
    """
    db_pool = db_pool_setup
    viewer_id = uuid.uuid4()
    non_existent_channel = "integration-test-ch-non-existent"

    # Seed test database (seed scopes prior to login)
    async with db_pool.acquire() as conn:
        pwd_hash = hash_password(TEST_PASSWORD)
        await conn.execute(
            "INSERT INTO users (id, username, password_hash, role) VALUES ($1, $2, $3, $4)",
            viewer_id,
            TEST_VIEWER_USERNAME,
            pwd_hash,
            "viewer",
        )
        await conn.execute(
            "INSERT INTO channels (channel_id, is_active) VALUES ($1, $2), ($3, $4)",
            TEST_CHANNEL_API_1,
            True,
            TEST_CHANNEL_API_2,
            False,
        )
        await conn.execute(
            "INSERT INTO user_channel_scopes (user_id, channel_id) VALUES ($1, $2), ($1, $3)",
            viewer_id,
            TEST_CHANNEL_API_1,
            non_existent_channel,
        )

    # Login as Viewer
    login_viewer = await api_client.post(
        "/api/v1/auth/login", json={"username": TEST_VIEWER_USERNAME, "password": TEST_PASSWORD}
    )
    viewer_token = login_viewer.json()["access_token"]
    headers = {"Authorization": f"Bearer {viewer_token}"}

    # Case 1: Authorized Access (200)
    resp_ok = await api_client.get(f"/api/v1/channel/{TEST_CHANNEL_API_1}/status", headers=headers)
    assert resp_ok.status_code == 200
    assert resp_ok.json()["channel_id"] == TEST_CHANNEL_API_1
    assert resp_ok.json()["is_active"] is True

    # Case 2: Unauthorized Scope (403)
    resp_forbidden = await api_client.get(f"/api/v1/channel/{TEST_CHANNEL_API_2}/status", headers=headers)
    assert resp_forbidden.status_code == 403
    assert resp_forbidden.json()["error"] == "forbidden"

    # Case 3: Channel Not Found in Registry (404)
    resp_not_found = await api_client.get(f"/api/v1/channel/{non_existent_channel}/status", headers=headers)
    assert resp_not_found.status_code == 404
    assert resp_not_found.json()["error"] == "not_found"


async def test_api_channel_history_and_validation(redis_setup, db_pool_setup, api_client):
    """
    Architecture §2.4.3 & §3.1: Test historical telemetry endpoint GET /api/v1/channel/{channel_id}/history.
    Validates dynamic bucket size calculation, zero-filling for empty series, and bounds validation rules.
    """
    db_pool = db_pool_setup
    viewer_id = uuid.uuid4()

    # Seed user and active channel
    async with db_pool.acquire() as conn:
        pwd_hash = hash_password(TEST_PASSWORD)
        await conn.execute(
            "INSERT INTO users (id, username, password_hash, role) VALUES ($1, $2, $3, $4)",
            viewer_id,
            TEST_VIEWER_USERNAME,
            pwd_hash,
            "viewer",
        )
        await conn.execute("INSERT INTO channels (channel_id, is_active) VALUES ($1, $2)", TEST_CHANNEL_API_1, True)
        await conn.execute(
            "INSERT INTO user_channel_scopes (user_id, channel_id) VALUES ($1, $2)", viewer_id, TEST_CHANNEL_API_1
        )

        # Seed 10 packets well within the refresh window per architecture §3.1.
        # The telemetry_1s refresh policy has start_offset=5s, so data must be
        # older than 5 seconds to be safely within a refreshed aggregate bucket.
        # Seeds at NOW()-10s / NOW()-11s to avoid any boundary timing issues.
        # direction=0 → IN (packets_in), direction=1 → OUT (packets_out)
        await conn.execute(
            """
            INSERT INTO packet_flows (time, channel_id, direction, src_ip, dst_ip, src_port, dst_port, protocol)
            VALUES (NOW() - INTERVAL '10 seconds', $1, 0, '192.168.1.10', '8.8.8.8', 12345, 80, 'TCP'),
                   (NOW() - INTERVAL '10 seconds', $1, 0, '192.168.1.10', '8.8.8.8', 12345, 80, 'TCP'),
                   (NOW() - INTERVAL '10 seconds', $1, 0, '192.168.1.10', '8.8.8.8', 12345, 80, 'TCP'),
                   (NOW() - INTERVAL '10 seconds', $1, 0, '192.168.1.10', '8.8.8.8', 12345, 80, 'TCP'),
                   (NOW() - INTERVAL '10 seconds', $1, 0, '192.168.1.10', '8.8.8.8', 12345, 80, 'TCP'),
                   (NOW() - INTERVAL '11 seconds', $1, 1, '8.8.8.8', '192.168.1.10', 80, 12345, 'TCP'),
                   (NOW() - INTERVAL '11 seconds', $1, 1, '8.8.8.8', '192.168.1.10', 80, 12345, 'TCP'),
                   (NOW() - INTERVAL '11 seconds', $1, 1, '8.8.8.8', '192.168.1.10', 80, 12345, 'TCP'),
                   (NOW() - INTERVAL '11 seconds', $1, 1, '8.8.8.8', '192.168.1.10', 80, 12345, 'TCP'),
                   (NOW() - INTERVAL '11 seconds', $1, 1, '8.8.8.8', '192.168.1.10', 80, 12345, 'TCP')
            """,
            TEST_CHANNEL_API_1,
        )
        # Refresh the continuous aggregate. Per architecture §3.1, end_offset=1s
        # means the upper bound must be at least NOW()-1s to include 10s/11s old data.
        await refresh_telemetry_1s(conn)

    # Login as Viewer
    login_viewer = await api_client.post(
        "/api/v1/auth/login", json={"username": TEST_VIEWER_USERNAME, "password": TEST_PASSWORD}
    )
    viewer_token = login_viewer.json()["access_token"]
    headers = {"Authorization": f"Bearer {viewer_token}"}

    # Case 1: Valid History Query (Success 200)
    # Use period_sec=15 so data seeded at 10s/11s ago is within [NOW()-15s, NOW()-1s].
    # Per architecture §3.1, telemetry_1s refresh start_offset=5s guarantees data
    # older than 5s is always in the aggregate — 10s/11s old data is safely included.
    resp = await api_client.get(f"/api/v1/channel/{TEST_CHANNEL_API_1}/history?period_sec=15", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["channel_id"] == TEST_CHANNEL_API_1
    assert data["period_sec"] == 15
    assert data["interval_sec"] == 1

    # Verify zero-filling: 15 x 1s buckets should be returned
    points = data["points"]
    assert len(points) >= 15

    active_points_in = [p for p in points if p["packets_in_per_sec"] > 0]
    active_points_out = [p for p in points if p["packets_out_per_sec"] > 0]
    assert len(active_points_in) > 0
    assert len(active_points_out) > 0
    # 5 packets in a 1s bucket → 5.0 per sec
    assert active_points_in[0]["packets_in_per_sec"] == 5.0
    assert active_points_out[0]["packets_out_per_sec"] == 5.0

    # Case 2: Validation Error - Future Start Time (400)
    # Format timezone as 'Z' to prevent url-decoding parsing issues (e.g. '+' interpreted as space)
    future_time = (
        (datetime.now(timezone.utc) + timedelta(hours=1)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )
    resp_err1 = await api_client.get(
        f"/api/v1/channel/{TEST_CHANNEL_API_1}/history?period_sec=5&start_time={future_time}", headers=headers
    )
    assert resp_err1.status_code == 400
    assert resp_err1.json()["error"] == "bad_request"

    # Case 3: Validation Error - Exceed retention cutoff (400)
    old_time = (
        (datetime.now(timezone.utc) - timedelta(days=50)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )
    resp_err2 = await api_client.get(
        f"/api/v1/channel/{TEST_CHANNEL_API_1}/history?period_sec=5&start_time={old_time}", headers=headers
    )
    assert resp_err2.status_code == 400
    assert resp_err2.json()["error"] == "bad_request"


async def test_api_host_history(redis_setup, db_pool_setup, api_client):
    """
    Architecture §2.4.3 & §3.1: Test GET /api/v1/channel/{channel_id}/hosts/{host_ip}/history.
    Verifies that per-host time-series are successfully queried from the raw packet_flows hypertable.
    """
    db_pool = db_pool_setup
    viewer_id = uuid.uuid4()
    host_ip = "192.168.1.100"

    # Seed user and active channel
    async with db_pool.acquire() as conn:
        pwd_hash = hash_password(TEST_PASSWORD)
        await conn.execute(
            "INSERT INTO users (id, username, password_hash, role) VALUES ($1, $2, $3, $4)",
            viewer_id,
            TEST_VIEWER_USERNAME,
            pwd_hash,
            "viewer",
        )
        await conn.execute("INSERT INTO channels (channel_id, is_active) VALUES ($1, $2)", TEST_CHANNEL_API_1, True)
        await conn.execute(
            "INSERT INTO user_channel_scopes (user_id, channel_id) VALUES ($1, $2)", viewer_id, TEST_CHANNEL_API_1
        )

        # Seed host traffic in raw packet_flows
        await conn.execute(
            """
            INSERT INTO packet_flows (time, channel_id, direction, src_ip, dst_ip, src_port, dst_port, protocol)
            VALUES (NOW() - INTERVAL '2 seconds', $1, 0, '8.8.8.8', $2, 443, 12345, 'TCP'),
                   (NOW() - INTERVAL '3 seconds', $1, 1, $2, '8.8.8.8', 12345, 443, 'TCP')
            """,
            TEST_CHANNEL_API_1,
            host_ip,
        )

    # Login as Viewer
    login_viewer = await api_client.post(
        "/api/v1/auth/login", json={"username": TEST_VIEWER_USERNAME, "password": TEST_PASSWORD}
    )
    viewer_token = login_viewer.json()["access_token"]
    headers = {"Authorization": f"Bearer {viewer_token}"}

    # Query host history
    resp = await api_client.get(
        f"/api/v1/channel/{TEST_CHANNEL_API_1}/hosts/{host_ip}/history?period_sec=5", headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["channel_id"] == TEST_CHANNEL_API_1
    assert data["host_ip"] == host_ip
    assert data["period_sec"] == 5
    assert data["interval_sec"] == 1

    points = data["points"]
    assert len(points) >= 5

    active_in = [p for p in points if p["packets_in_per_sec"] > 0]
    active_out = [p for p in points if p["packets_out_per_sec"] > 0]
    assert len(active_in) > 0
    assert len(active_out) > 0
    assert active_in[0]["packets_in_per_sec"] == 1.0
    assert active_out[0]["packets_out_per_sec"] == 1.0


async def test_api_health_check_healthy(redis_setup, db_pool_setup, api_client):
    """
    Architecture §2.4.1: Test that GET /api/v1/health returns 200 and 'healthy' status
    when all components (DB, Redis) are online and reachable.
    """
    db_pool = db_pool_setup
    viewer_id = uuid.uuid4()

    # Seed viewer
    async with db_pool.acquire() as conn:
        pwd_hash = hash_password(TEST_PASSWORD)
        await conn.execute(
            "INSERT INTO users (id, username, password_hash, role) VALUES ($1, $2, $3, $4)",
            viewer_id,
            TEST_VIEWER_USERNAME,
            pwd_hash,
            "viewer",
        )

    # Login
    login_response = await api_client.post(
        "/api/v1/auth/login", json={"username": TEST_VIEWER_USERNAME, "password": TEST_PASSWORD}
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Query health check
    response = await api_client.get("/api/v1/health", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["components"]["database"] == "active"
    assert data["components"]["redis"] == "active"
    assert "timestamp" in data


async def test_api_health_check_unhealthy(redis_setup, db_pool_setup, api_client):
    """
    Architecture §2.4.1: Test that GET /api/v1/health returns 503 (UnhealthyError)
    when one of the core components (e.g. database pool) encounters an error.
    """
    db_pool = db_pool_setup
    viewer_id = uuid.uuid4()

    # Seed viewer
    async with db_pool.acquire() as conn:
        pwd_hash = hash_password(TEST_PASSWORD)
        await conn.execute(
            "INSERT INTO users (id, username, password_hash, role) VALUES ($1, $2, $3, $4)",
            viewer_id,
            TEST_VIEWER_USERNAME,
            pwd_hash,
            "viewer",
        )

    # Login
    login_response = await api_client.post(
        "/api/v1/auth/login", json={"username": TEST_VIEWER_USERNAME, "password": TEST_PASSWORD}
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Mock db_ping to return False
    from unittest.mock import patch

    with patch("services.api.routes.health.db_ping", return_value=False):
        response = await api_client.get("/api/v1/health", headers=headers)
        assert response.status_code == 503
        data = response.json()
        assert data["error"] == "unhealthy"
        assert "error state" in data["message"].lower()


async def test_api_login_wrong_password(redis_setup, db_pool_setup, api_client):
    """
    Architecture §6.1: Validates that logging in with an existing user but
    incorrect password returns 401 status with 'invalid_credentials' JSON schema.
    """
    db_pool = db_pool_setup
    viewer_id = uuid.uuid4()

    # Seed test database
    async with db_pool.acquire() as conn:
        pwd_hash = hash_password(TEST_PASSWORD)
        await conn.execute(
            "INSERT INTO users (id, username, password_hash, role) VALUES ($1, $2, $3, $4)",
            viewer_id,
            TEST_VIEWER_USERNAME,
            pwd_hash,
            "viewer",
        )

    # Try logging in with incorrect password
    response = await api_client.post(
        "/api/v1/auth/login", json={"username": TEST_VIEWER_USERNAME, "password": "wrong-password"}
    )
    assert response.status_code == 401
    assert response.json() == {"error": "invalid_credentials", "message": "Invalid username or password."}


async def test_api_logout_malformed_cookie(redis_setup, db_pool_setup, api_client):
    """
    Architecture §5.3: Test that POST /api/v1/auth/logout succeeds (is idempotent)
    and clears cookies even if the refresh token cookie is malformed or invalid.
    """
    # Set a malformed refresh token cookie manually
    api_client.cookies.set("refresh_token", "malformed-jwt-token", path="/api/v1/auth/refresh")

    response = await api_client.post("/api/v1/auth/logout")
    assert response.status_code == 200
    assert response.json() == {"message": "Successfully logged out."}
    # Cookie should be cleared
    assert "refresh_token" not in response.cookies


async def test_api_health_check_redis_unhealthy(redis_setup, db_pool_setup, api_client):
    """
    Architecture §2.4.1: Test that GET /api/v1/health returns 503 (UnhealthyError)
    when Redis client ping throws an exception.
    """
    db_pool = db_pool_setup
    viewer_id = uuid.uuid4()

    # Seed viewer
    async with db_pool.acquire() as conn:
        pwd_hash = hash_password(TEST_PASSWORD)
        await conn.execute(
            "INSERT INTO users (id, username, password_hash, role) VALUES ($1, $2, $3, $4)",
            viewer_id,
            TEST_VIEWER_USERNAME,
            pwd_hash,
            "viewer",
        )

    # Login
    login_response = await api_client.post(
        "/api/v1/auth/login", json={"username": TEST_VIEWER_USERNAME, "password": TEST_PASSWORD}
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Mock get_redis_client to throw exception
    from unittest.mock import patch

    with patch("services.api.routes.health.get_redis_client") as mock_redis:
        # Mock client to raise exception on ping
        client_mock = mock_redis.return_value
        client_mock.ping.side_effect = Exception("Redis connection error")
        response = await api_client.get("/api/v1/health", headers=headers)
        assert response.status_code == 503
        data = response.json()
        assert data["error"] == "unhealthy"
