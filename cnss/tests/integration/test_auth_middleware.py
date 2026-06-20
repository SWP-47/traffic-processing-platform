"""
Integration tests for Authorization Middleware.
"""
import pytest
import jwt
from datetime import datetime, timezone
from app.config import get_settings
from unittest.mock import patch, AsyncMock
from app.store.memory import InMemoryStateStore # FIX 1: Correct import path

class TestAuthMiddleware:
    
    # Fixtures/Helpers
    def _get_token(self, role, scope=None, expired=False):
        settings = get_settings()
        now = int(datetime.now(timezone.utc).timestamp())
        payload = {
            "sub": f"{role}_user",
            "iat": now,
            "exp": now - 10 if expired else now + 3600,
            "role": role,
            "scope": scope if scope is not None else []
        }
        return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    def _get_headers(self, token):
        return {"Authorization": f"Bearer {token}"}

    def test_missing_authorization_header_returns_401(self, client):
        """Given a request without the header, Then return 401 with specific JSON."""
        response = client.get("/api/v1/channels")
        assert response.status_code == 401
        data = response.json()
        assert data == {"error": "unauthorized", "message": "Invalid or expired token."}

    def test_expired_token_returns_401(self, client):
        """Given an expired token, Then return 401."""
        token = self._get_token("viewer", expired=True)
        response = client.get("/api/v1/channels", headers=self._get_headers(token))
        assert response.status_code == 401
        assert response.json()["error"] == "unauthorized"

    def test_invalid_signature_returns_401(self, client):
        """Given a token with wrong signature, Then return 401."""
        token = jwt.encode({"sub": "u", "exp": 9999999999}, "wrong-secret", algorithm="HS256")
        response = client.get("/api/v1/channels", headers=self._get_headers(token))
        assert response.status_code == 401
        assert response.json()["error"] == "unauthorized"

    def test_admin_has_unrestricted_access(self, client):
        """Given a request from admin, When checking channel access, Then access is allowed regardless of scope."""
        admin_token = self._get_token("admin", scope=[]) # Empty scope, but admin
        test_store = InMemoryStateStore()
        with patch("app.main.state_store", test_store):
            response = client.get("/api/v1/channels", headers=self._get_headers(admin_token))
            assert response.status_code == 200

    def test_viewer_allowed_in_scope(self, client):
        """Given viewer with scope=["bridge-berlin-01"], When accessing it, Then 200."""
        viewer_token = self._get_token("viewer", scope=["bridge-berlin-01"])
        
        # Use a real InMemoryStateStore to avoid MagicMock async issues
        test_store = InMemoryStateStore()
        with patch("app.main.state_store", test_store):
            response = client.get("/api/v1/channels", headers=self._get_headers(viewer_token))
            assert response.status_code == 200

    def test_viewer_forbidden_out_of_scope(self, client):
        """Given viewer with scope=["bridge-berlin-01"], When accessing bridge-prague, Then 403."""
        viewer_token = self._get_token("viewer", scope=["bridge-berlin-01"])
        
        class MockChannel:
            channel_id = "bridge-prague-01"
            is_active = False
            last_activity_timestamp = datetime.now(timezone.utc)

        mock_store = AsyncMock()
        mock_store.get_channel.return_value = MockChannel()
        
        with patch("app.main.state_store", mock_store):
            response = client.get(
                "/api/v1/channel/bridge-prague-01/status", 
                headers=self._get_headers(viewer_token)
            )
            
            assert response.status_code == 403
            data = response.json()
            assert data == {
                "error": "forbidden",
                "message": "You do not have access to this channel."
            }