import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime, timezone

class TestHistoryEndpoint:
    @pytest.mark.asyncio
    async def test_valid_history_request(self, client, admin_headers):
        """Valid request returns 200 with dynamically calculated interval and points."""
        mock_points = [
            {"timestamp": "2026-06-17T12:00:00Z", "packets_in_per_sec": 10.0, "packets_out_per_sec": 20.0, "is_active": True}
        ]
        with patch("app.main.get_channel_history", new_callable=AsyncMock, return_value=(60, mock_points)), \
             patch("app.main.get_channel_status_from_db", new_callable=AsyncMock, return_value={"channel_id": "bridge-berlin-01", "last_activity_timestamp": datetime.now(timezone.utc)}):
            response = client.get("/api/v1/channel/bridge-berlin-01/history?period=24h", headers=admin_headers)
            assert response.status_code == 200
            data = response.json()
            assert data["channel_id"] == "bridge-berlin-01"
            assert data["period"] == "24h"
            assert data["interval_sec"] == 60
            assert len(data["points"]) == 1
            assert data["points"][0]["packets_in_per_sec"] == 10.0

    @pytest.mark.asyncio
    async def test_invalid_period_returns_400(self, client, admin_headers):
        """Invalid period enum returns 400 bad_request."""
        with patch("app.main.get_channel_status_from_db", new_callable=AsyncMock, return_value={"channel_id": "bridge-berlin-01", "last_activity_timestamp": datetime.now(timezone.utc)}):
            response = client.get("/api/v1/channel/bridge-berlin-01/history?period=2d", headers=admin_headers)
            assert response.status_code == 400
            assert response.json()["error"] == "bad_request"

    @pytest.mark.asyncio
    async def test_channel_not_found_returns_404(self, client, admin_headers):
        """Non-existent channel returns 404 not_found."""
        with patch("app.main.get_channel_status_from_db", new_callable=AsyncMock, return_value=None):
            response = client.get("/api/v1/channel/non-existent/history?period=24h", headers=admin_headers)
            assert response.status_code == 404
            assert response.json()["error"] == "not_found"

    @pytest.mark.asyncio
    async def test_viewer_forbidden_returns_403(self, client, viewer_headers):
        """Viewer accessing out-of-scope channel returns 403 forbidden."""
        # viewer scope is ["bridge-berlin-01", "bridge-prague-01"]
        response = client.get("/api/v1/channel/bridge-rome-01/history?period=24h", headers=viewer_headers)
        assert response.status_code == 403
        assert response.json()["error"] == "forbidden"