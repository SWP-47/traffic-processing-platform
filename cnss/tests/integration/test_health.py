# tests/integration/test_health.py
"""
Integration tests for the /health endpoint.
Verifies that the server responds correctly and matches the MVP v1 API specification.
"""


class TestHealthEndpoint:
    """Integration tests for GET /health."""

    def test_health_endpoint_returns_200(self, client):
        """Server must return HTTP 200 on /health."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_response_structure(self, client):
        """
        Response must contain required MVP v1 fields:
        status, components, channels_active, channels_total, timestamp.
        """
        response = client.get("/health")
        data = response.json()

        assert "status" in data
        assert "components" in data
        assert "cnss" in data["components"]
        assert "channels_active" in data
        assert "channels_total" in data
        assert "timestamp" in data

    def test_health_status_is_healthy(self, client):
        """Server status must be 'healthy' upon successful startup."""
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "healthy"

    def test_health_components_structure(self, client):
        """Components field must correctly report CnSS status as 'active'."""
        response = client.get("/health")
        data = response.json()
        assert isinstance(data["components"], dict)
        assert data["components"]["cnss"] == "active"

    def test_health_channels_metrics_are_integers(self, client):
        """Channel metrics must be non-negative integers."""
        response = client.get("/health")
        data = response.json()

        assert isinstance(data["channels_active"], int)
        assert isinstance(data["channels_total"], int)
        assert data["channels_active"] >= 0
        assert data["channels_total"] >= 0
        # Active channels cannot exceed total channels
        assert data["channels_active"] <= data["channels_total"]

    def test_health_timestamp_is_iso8601(self, client):
        """
        Timestamp field must be in ISO 8601 format (contains 'T' and 'Z').
        """
        response = client.get("/health")
        data = response.json()
        timestamp = data["timestamp"]

        assert isinstance(timestamp, str)
        assert "T" in timestamp
        # Check that timestamp ends with 'Z' (UTC) or contains a tz offset
        assert timestamp.endswith("Z") or "+" in timestamp

    def test_health_endpoint_is_idempotent(self, client):
        """Repeated calls to /health must return the same status."""
        response1 = client.get("/health")
        response2 = client.get("/health")

        assert response1.status_code == response2.status_code
        assert response1.json()["status"] == response2.json()["status"]
