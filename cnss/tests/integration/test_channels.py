import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime, timezone


class TestChannelsEndpoint:
    @pytest.mark.asyncio
    async def test_admin_sees_all_channels(self, client, admin_headers):
        mock_db_data = [
            {
                "channel_id": "ch-admin-1",
                "last_activity_timestamp": datetime.now(timezone.utc),
            },
            {
                "channel_id": "ch-admin-2",
                "last_activity_timestamp": datetime.now(timezone.utc),
            },
        ]
        with patch(
            "app.main.get_all_channels_from_db",
            new_callable=AsyncMock,
            return_value=mock_db_data,
        ):
            response = client.get("/api/v1/channels", headers=admin_headers)
            assert response.status_code == 200
            data = response.json()
            ids = {ch["channel_id"] for ch in data["channels"]}
            assert ids == {"ch-admin-1", "ch-admin-2"}

    @pytest.mark.asyncio
    async def test_viewer_sees_only_scoped_channels(self, client, viewer_headers):
        mock_db_data = [
            {
                "channel_id": "bridge-berlin-01",
                "last_activity_timestamp": datetime.now(timezone.utc),
            },
            {
                "channel_id": "bridge-prague-01",
                "last_activity_timestamp": datetime.now(timezone.utc),
            },
        ]
        with patch(
            "app.main.get_all_channels_from_db",
            new_callable=AsyncMock,
            return_value=mock_db_data,
        ):
            response = client.get("/api/v1/channels", headers=viewer_headers)
            assert response.status_code == 200
            data = response.json()
            ids = {ch["channel_id"] for ch in data["channels"]}
            assert ids == {"bridge-berlin-01"}
            assert "bridge-prague-01" not in ids

    def test_unauthenticated_returns_401(self, client):
        response = client.get("/api/v1/channels")
        assert response.status_code == 401


class TestChannelStatusEndpoint:
    @pytest.mark.asyncio
    async def test_ac4_admin_gets_existing_channel(self, client, admin_headers):
        mock_db_data = {
            "channel_id": "bridge-berlin-01",
            "last_activity_timestamp": datetime.now(timezone.utc),
        }
        with patch(
            "app.main.get_channel_status_from_db",
            new_callable=AsyncMock,
            return_value=mock_db_data,
        ):
            response = client.get(
                "/api/v1/channel/bridge-berlin-01/status", headers=admin_headers
            )
            assert response.status_code == 200
            data = response.json()
            assert data["channel_id"] == "bridge-berlin-01"
            assert data["is_active"] is True
            assert "last_activity_timestamp" in data

    @pytest.mark.asyncio
    async def test_ac4_viewer_gets_scoped_channel(self, client, viewer_headers):
        mock_db_data = {
            "channel_id": "bridge-berlin-01",
            "last_activity_timestamp": datetime.now(timezone.utc),
        }
        with patch(
            "app.main.get_channel_status_from_db",
            new_callable=AsyncMock,
            return_value=mock_db_data,
        ):
            response = client.get(
                "/api/v1/channel/bridge-berlin-01/status", headers=viewer_headers
            )
            assert response.status_code == 200

    def test_viewer_gets_forbidden_on_unscoped_channel(self, client, viewer_headers):
        # Scope check happens before DB lookup, so no DB mock needed
        response = client.get(
            "/api/v1/channel/bridge-prague-01/status", headers=viewer_headers
        )
        assert response.status_code == 403
        assert response.json()["error"] == "forbidden"

    @pytest.mark.asyncio
    async def test_ac5_non_existent_channel_returns_404(self, client, admin_headers):
        with patch(
            "app.main.get_channel_status_from_db",
            new_callable=AsyncMock,
            return_value=None,
        ):
            response = client.get(
                "/api/v1/channel/non-existent/status", headers=admin_headers
            )
            assert response.status_code == 404
            assert response.json() == {
                "error": "not_found",
                "message": "Channel not found.",
            }

    def test_unauthenticated_returns_401(self, client):
        response = client.get("/api/v1/channel/bridge-berlin-01/status")
        assert response.status_code == 401
