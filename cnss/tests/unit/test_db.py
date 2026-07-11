# ==============================================================================
# CnSS Database Query Module Unit Tests
# Verifies the functions of core/db.py under various query conditions and mock pools.
# ==============================================================================

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from core.db import (
    db_ping,
    db_fetch_channel_counts,
    db_fetch_user_by_username,
    db_fetch_user_scopes,
    db_fetch_all_channels,
    db_fetch_channel_status,
    db_list_channels,
    db_channel_exists,
    db_fetch_channel_history,
    db_fetch_host_history,
    db_upsert_channel,
    db_deactivate_timed_out_channels,
    db_execute_fetch,
    db_execute_fetchrow,
    db_fetch_telemetry_data,
    db_fetch_hosts_table_data,
    db_fetch_host_top_destinations_data,
    db_fetch_host_details_data,
    db_fetch_host_top_ports_data,
)

@pytest.fixture
def mock_conn():
    conn = AsyncMock()
    return conn

@pytest.fixture
def mock_pool(mock_conn):
    pool = AsyncMock()
    pool.acquire = MagicMock(
        return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=mock_conn),
            __aexit__=AsyncMock()
        )
    )
    return pool

async def test_db_ping_success(mock_pool, mock_conn):
    mock_conn.fetchval = AsyncMock(return_value=1)
    assert await db_ping(pool=mock_pool) is True
    mock_conn.fetchval.assert_called_once_with("SELECT 1;")

async def test_db_ping_failure():
    mock_pool = MagicMock()
    mock_pool.acquire.side_effect = Exception("Database down")
    assert await db_ping(pool=mock_pool) is False

async def test_db_fetch_channel_counts(mock_pool, mock_conn):
    mock_conn.fetchrow = AsyncMock(return_value={"total": 10, "active": 3})
    total, active = await db_fetch_channel_counts(pool=mock_pool)
    assert total == 10
    assert active == 3

async def test_db_fetch_user_by_username(mock_pool, mock_conn):
    mock_conn.fetchrow = AsyncMock(return_value={"id": "user-uuid", "username": "admin", "password_hash": "hash", "role": "admin"})
    user = await db_fetch_user_by_username("admin", pool=mock_pool)
    assert user["username"] == "admin"
    assert user["role"] == "admin"

async def test_db_fetch_user_scopes(mock_pool, mock_conn):
    mock_conn.fetch = AsyncMock(return_value=[{"channel_id": "ch1"}, {"channel_id": "ch2"}])
    scopes = await db_fetch_user_scopes("user-uuid", pool=mock_pool)
    assert scopes == ["ch1", "ch2"]

async def test_db_fetch_all_channels(mock_pool, mock_conn):
    mock_conn.fetch = AsyncMock(return_value=[{"channel_id": "ch1"}, {"channel_id": "ch2"}])
    channels = await db_fetch_all_channels(pool=mock_pool)
    assert channels == ["ch1", "ch2"]

async def test_db_fetch_channel_status(mock_pool, mock_conn):
    mock_conn.fetchrow = AsyncMock(return_value={"channel_id": "ch1", "is_active": True, "last_activity_at": None})
    status = await db_fetch_channel_status("ch1", pool=mock_pool)
    assert status["channel_id"] == "ch1"
    assert status["is_active"] is True

async def test_db_list_channels_all(mock_pool, mock_conn):
    mock_conn.fetch = AsyncMock(return_value=[{"channel_id": "ch1", "is_active": True, "last_activity_at": None}])
    res = await db_list_channels(pool=mock_pool)
    assert len(res) == 1
    assert res[0]["channel_id"] == "ch1"

async def test_db_list_channels_filtered(mock_pool, mock_conn):
    mock_conn.fetch = AsyncMock(return_value=[{"channel_id": "ch1", "is_active": True, "last_activity_at": None}])
    res = await db_list_channels(channel_ids=["ch1"], pool=mock_pool)
    assert len(res) == 1
    assert res[0]["channel_id"] == "ch1"
    mock_conn.fetch.assert_called_once_with(
        "SELECT channel_id, is_active, last_activity_at FROM channels WHERE channel_id = ANY($1)",
        ["ch1"]
    )

async def test_db_channel_exists(mock_pool, mock_conn):
    mock_conn.fetchrow = AsyncMock(return_value={"channel_id": "ch1"})
    assert await db_channel_exists("ch1", pool=mock_pool) is True

async def test_db_fetch_channel_history(mock_pool, mock_conn):
    mock_conn.fetch = AsyncMock(return_value=[{"timestamp": datetime.now(timezone.utc), "packets_in_per_sec": 1.0, "packets_out_per_sec": 2.0, "is_active": True}])
    history = await db_fetch_channel_history("ch1", datetime.now(timezone.utc), datetime.now(timezone.utc), 10, pool=mock_pool)
    assert len(history) == 1
    assert history[0]["packets_in_per_sec"] == 1.0

async def test_db_fetch_host_history(mock_pool, mock_conn):
    mock_conn.fetch = AsyncMock(return_value=[{"timestamp": datetime.now(timezone.utc), "packets_in_per_sec": 1.0, "packets_out_per_sec": 2.0}])
    history = await db_fetch_host_history("ch1", "192.168.1.1", datetime.now(timezone.utc), datetime.now(timezone.utc), 10, pool=mock_pool)
    assert len(history) == 1
    assert history[0]["packets_in_per_sec"] == 1.0

async def test_db_upsert_channel(mock_pool, mock_conn):
    mock_conn.execute = AsyncMock()
    await db_upsert_channel("ch1", True, 42, None, pool=mock_pool)
    mock_conn.execute.assert_called_once()

async def test_db_deactivate_timed_out_channels(mock_pool, mock_conn):
    mock_conn.execute = AsyncMock(return_value="UPDATE 5")
    cnt = await db_deactivate_timed_out_channels(5000, pool=mock_pool)
    assert cnt == 5

async def test_db_execute_fetch(mock_pool, mock_conn):
    mock_conn.fetch = AsyncMock(return_value=[{"col": "val"}])
    res = await db_execute_fetch("SELECT *", [], pool=mock_pool)
    assert res == [{"col": "val"}]

async def test_db_execute_fetchrow(mock_pool, mock_conn):
    mock_conn.fetchrow = AsyncMock(return_value={"col": "val"})
    res = await db_execute_fetchrow("SELECT *", [], pool=mock_pool)
    assert res == {"col": "val"}


async def test_db_fetch_telemetry_data(mock_pool, mock_conn):
    mock_conn.fetchrow = AsyncMock(return_value={"is_active": True, "dropped": 0, "total_in": 100, "total_out": 200, "bucket_count": 5, "latest_bucket": None})
    res = await db_fetch_telemetry_data("bridge-01", 5.0, pool=mock_pool)
    assert res["is_active"] is True
    assert res["total_in"] == 100

async def test_db_fetch_hosts_table_data(mock_pool, mock_conn):
    mock_conn.fetch = AsyncMock(return_value=[{"host_ip": "192.168.1.5", "total_count": 1}])
    res = await db_fetch_hosts_table_data("$1", "$2", 5.0, "", "", "", "", ["ch1", "5s"], pool=mock_pool)
    assert len(res) == 1
    assert res[0]["host_ip"] == "192.168.1.5"

async def test_db_fetch_host_top_destinations_data(mock_pool, mock_conn):
    mock_conn.fetch = AsyncMock(return_value=[{"remote_ip": "8.8.8.8", "total_count": 1}])
    res = await db_fetch_host_top_destinations_data("$1", "$2", "$3", 5.0, "", "", "", ["192.168.1.5", "ch1", "5s"], pool=mock_pool)
    assert len(res) == 1
    assert res[0]["remote_ip"] == "8.8.8.8"

async def test_db_fetch_host_details_data(mock_pool, mock_conn):
    mock_conn.fetchrow = AsyncMock(return_value={"tx_per_sec": 10.0, "rx_per_sec": 20.0})
    res = await db_fetch_host_details_data("$1", "$2", "$3", 5.0, ["192.168.1.5", "ch1", "5s"], pool=mock_pool)
    assert res["tx_per_sec"] == 10.0

async def test_db_fetch_host_top_ports_data(mock_pool, mock_conn):
    mock_conn.fetch = AsyncMock(return_value=[{"remote_port": 80, "total_count": 1}])
    res = await db_fetch_host_top_ports_data("$1", "$2", "$3", 5.0, "", "", "", ["192.168.1.5", "ch1", "5s"], pool=mock_pool)
    assert len(res) == 1
    assert res[0]["remote_port"] == 80
