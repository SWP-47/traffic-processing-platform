import pytest
from unittest.mock import patch, AsyncMock


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_endpoint_returns_200(self, client, admin_headers):
        with patch(
            "app.main.is_db_healthy", new_callable=AsyncMock, return_value=True
        ), patch(
            "app.main.get_health_metrics_from_db",
            new_callable=AsyncMock,
            return_value={"channels_total": 2, "channels_active": 1},
        ):
            response = client.get("/api/v1/health", headers=admin_headers)
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_health_response_structure(self, client, admin_headers):
        with patch(
            "app.main.is_db_healthy", new_callable=AsyncMock, return_value=True
        ), patch(
            "app.main.get_health_metrics_from_db",
            new_callable=AsyncMock,
            return_value={"channels_total": 2, "channels_active": 1},
        ):
            response = client.get("/api/v1/health", headers=admin_headers)
            data = response.json()
            assert "status" in data
            assert "components" in data
            assert "cnss" in data["components"]
            assert "channels_active" in data
            assert "channels_total" in data
            assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_health_status_is_healthy(self, client, admin_headers):
        with patch(
            "app.main.is_db_healthy", new_callable=AsyncMock, return_value=True
        ), patch(
            "app.main.get_health_metrics_from_db",
            new_callable=AsyncMock,
            return_value={"channels_total": 2, "channels_active": 1},
        ):
            response = client.get("/api/v1/health", headers=admin_headers)
            data = response.json()
            assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_components_structure(self, client, admin_headers):
        with patch(
            "app.main.is_db_healthy", new_callable=AsyncMock, return_value=True
        ), patch(
            "app.main.get_health_metrics_from_db",
            new_callable=AsyncMock,
            return_value={"channels_total": 2, "channels_active": 1},
        ):
            response = client.get("/api/v1/health", headers=admin_headers)
            data = response.json()
            assert data["components"]["cnss"] == "active"

    @pytest.mark.asyncio
    async def test_health_channels_metrics_are_integers(self, client, admin_headers):
        with patch(
            "app.main.is_db_healthy", new_callable=AsyncMock, return_value=True
        ), patch(
            "app.main.get_health_metrics_from_db",
            new_callable=AsyncMock,
            return_value={"channels_total": 2, "channels_active": 1},
        ):
            response = client.get("/api/v1/health", headers=admin_headers)
            data = response.json()
            assert isinstance(data["channels_active"], int)
            assert isinstance(data["channels_total"], int)
            assert data["channels_active"] <= data["channels_total"]

    @pytest.mark.asyncio
    async def test_health_timestamp_is_iso8601(self, client, admin_headers):
        with patch(
            "app.main.is_db_healthy", new_callable=AsyncMock, return_value=True
        ), patch(
            "app.main.get_health_metrics_from_db",
            new_callable=AsyncMock,
            return_value={"channels_total": 2, "channels_active": 1},
        ):
            response = client.get("/api/v1/health", headers=admin_headers)
            data = response.json()
            timestamp = data["timestamp"]
            assert "T" in timestamp and (timestamp.endswith("Z") or "+" in timestamp)

    def test_health_unauthenticated_returns_401(self, client):
        response = client.get("/api/v1/health")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_health_returns_503_when_db_unhealthy(self, client, admin_headers):
        with patch(
            "app.main.is_db_healthy", new_callable=AsyncMock, return_value=False
        ), patch(
            "app.main.get_health_metrics_from_db",
            new_callable=AsyncMock,
            return_value={"channels_total": 0, "channels_active": 0},
        ):
            response = client.get("/api/v1/health", headers=admin_headers)
            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "unhealthy"
            assert data["components"]["cnss"] == "error"
