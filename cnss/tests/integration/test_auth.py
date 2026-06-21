import asyncio
from unittest.mock import patch
from datetime import datetime, timezone
from app.store.memory import InMemoryStateStore


class TestLoginEndpoint:
    def test_ac1_valid_credentials(self, client):
        """AC 1: Valid credentials return 200 with JWT and metadata."""
        response = client.post(
            "/api/v1/auth/login", json={"username": "admin", "password": "admin123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "Bearer"
        assert data["expires_in"] == 86400
        assert data["role"] == "admin"
        assert isinstance(data["scope"], list)

    def test_ac2_invalid_credentials(self, client):
        """AC 2: Invalid credentials return 401 with exact error format."""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "wrongpassword"},
        )
        assert response.status_code == 401
        assert response.json() == {
            "error": "invalid_credentials",
            "message": "Invalid username or password.",
        }

    def test_ac3_missing_fields(self, client):
        """AC 3: Missing fields return 400 with exact error format."""
        response = client.post("/api/v1/auth/login", json={"username": "admin"})
        assert response.status_code == 400
        assert response.json() == {
            "error": "bad_request",
            "message": "Fields 'username' and 'password' are required.",
        }

    def test_scope_intersection_viewer(self, client):
        """Viewer scope must be an intersection of configured and existing channels."""
        test_store = InMemoryStateStore()
        loop = asyncio.new_event_loop()
        # Add only one of the viewer's allowed channels to the store
        loop.run_until_complete(
            test_store.update_channel_activity(
                "bridge-berlin-01", 1, datetime.now(timezone.utc)
            )
        )
        loop.close()

        with patch("app.main.state_store", test_store):
            response = client.post(
                "/api/v1/auth/login",
                json={"username": "viewer", "password": "viewer123"},
            )

        assert response.status_code == 200
        data = response.json()
        # Viewer is configured with ["bridge-berlin-01", "bridge-prague-01"] in MOCK_USERS
        # But only "bridge-berlin-01" exists in the store
        assert data["scope"] == ["bridge-berlin-01"]
        assert "bridge-prague-01" not in data["scope"]

    def test_scope_intersection_admin(self, client):
        """Admin scope must contain ALL existing channels in the store."""
        test_store = InMemoryStateStore()
        loop = asyncio.new_event_loop()
        loop.run_until_complete(
            test_store.update_channel_activity(
                "new-ch-1", 1, datetime.now(timezone.utc)
            )
        )
        loop.run_until_complete(
            test_store.update_channel_activity(
                "new-ch-2", 1, datetime.now(timezone.utc)
            )
        )
        loop.close()

        with patch("app.main.state_store", test_store):
            response = client.post(
                "/api/v1/auth/login", json={"username": "admin", "password": "admin123"}
            )

        assert response.status_code == 200
        data = response.json()
        assert set(data["scope"]) == {"new-ch-1", "new-ch-2"}
