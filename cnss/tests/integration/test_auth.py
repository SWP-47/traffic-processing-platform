from unittest.mock import patch
from unittest.mock import AsyncMock


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
        """Viewer scope must be an intersection of configured and existing channels (from DB)."""
        with patch(
            "app.main.get_all_channel_ids_from_db",
            new_callable=AsyncMock,
            return_value=["bridge-berlin-01"],
        ):
            response = client.post(
                "/api/v1/auth/login",
                json={"username": "viewer", "password": "viewer123"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["scope"] == ["bridge-berlin-01"]
            assert "bridge-prague-01" not in data["scope"]

    def test_scope_intersection_admin(self, client):
        """Admin scope must contain ALL existing channels in the DB."""
        with patch(
            "app.main.get_all_channel_ids_from_db",
            new_callable=AsyncMock,
            return_value=["new-ch-1", "new-ch-2"],
        ):
            response = client.post(
                "/api/v1/auth/login", json={"username": "admin", "password": "admin123"}
            )
            assert response.status_code == 200
            data = response.json()
            assert set(data["scope"]) == {"new-ch-1", "new-ch-2"}
