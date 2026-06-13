"""
Integration tests for the /health endpoint.

Verifies that:
1. The server responds to requests.
2. The correct HTTP status is returned.
3. The JSON response structure matches the specification.
"""


class TestHealthEndpoint:
    """Integration tests for GET /health."""

    def test_health_endpoint_returns_200(self, client):
        """Server must return HTTP 200 on /health."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_response_structure(self, client):
        """
        Response must contain required fields:
        status, message, timestamp.
        """
        response = client.get("/health")
        data = response.json()

        assert "status" in data
        assert "message" in data
        assert "timestamp" in data

    def test_health_status_is_healthy(self, client):
        """Server status must be 'healthy' upon successful startup."""
        response = client.get("/health")
        data = response.json()

        assert data["status"] == "healthy"

    def test_health_message_is_not_empty(self, client):
        """Message field must be a non-empty string."""
        response = client.get("/health")
        data = response.json()

        assert isinstance(data["message"], str)
        assert len(data["message"]) > 0

    def test_health_timestamp_is_iso8601(self, client):
        """
        Timestamp field must be in ISO 8601
        format (contains 'T' and 'Z').
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
