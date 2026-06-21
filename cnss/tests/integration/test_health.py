"""
Integration tests for the /api/v1/health endpoint.
"""


class TestHealthEndpoint:
    """Integration tests for GET /api/v1/health."""

    def test_health_endpoint_returns_200(self, client, admin_headers):
        response = client.get("/api/v1/health", headers=admin_headers)
        assert response.status_code == 200

    def test_health_response_structure(self, client, admin_headers):
        response = client.get("/api/v1/health", headers=admin_headers)
        data = response.json()
        assert "status" in data
        assert "components" in data
        assert "cnss" in data["components"]
        assert "channels_active" in data
        assert "channels_total" in data
        assert "timestamp" in data

    def test_health_status_is_healthy(self, client, admin_headers):
        response = client.get("/api/v1/health", headers=admin_headers)
        data = response.json()
        assert data["status"] == "healthy"

    def test_health_components_structure(self, client, admin_headers):
        response = client.get("/api/v1/health", headers=admin_headers)
        data = response.json()
        assert data["components"]["cnss"] == "active"

    def test_health_channels_metrics_are_integers(self, client, admin_headers):
        response = client.get("/api/v1/health", headers=admin_headers)
        data = response.json()
        assert isinstance(data["channels_active"], int)
        assert isinstance(data["channels_total"], int)
        assert data["channels_active"] <= data["channels_total"]

    def test_health_timestamp_is_iso8601(self, client, admin_headers):
        response = client.get("/api/v1/health", headers=admin_headers)
        data = response.json()
        timestamp = data["timestamp"]
        assert "T" in timestamp and (timestamp.endswith("Z") or "+" in timestamp)

    def test_health_unauthenticated_returns_401(self, client):
        """Ensure auth middleware is correctly applied."""
        response = client.get("/api/v1/health")
        assert response.status_code == 401
