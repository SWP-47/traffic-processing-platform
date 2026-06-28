import pytest
import jwt
import time
from fastapi import HTTPException
from app.auth import authenticate_user, create_access_token, decode_token
from app.config import settings


class TestAuthenticateUser:
    def test_valid_credentials(self):
        user = authenticate_user("admin", "admin123")
        assert user is not None
        assert user["role"] == "admin"

    def test_invalid_password(self):
        assert authenticate_user("admin", "wrongpassword") is None

    def test_invalid_username(self):
        assert authenticate_user("nonexistent", "admin123") is None


class TestJWTGeneration:
    def test_create_token_claims(self):
        """AC 4: Token payload contains all required claims."""
        token, expires_in, issued_at = create_access_token(
            "testuser", "viewer", ["ch-1"]
        )

        # Decode without verification to inspect payload
        payload = jwt.decode(token, options={"verify_signature": False})

        assert payload["sub"] == "testuser"
        assert payload["role"] == "viewer"
        assert payload["scope"] == ["ch-1"]
        assert payload["exp"] - payload["iat"] == settings.jwt_expiration_seconds

    def test_create_token_signature(self):
        """AC 5: Token is signed with HS256 and SECRET_KEY."""
        token, _, _ = create_access_token("testuser", "admin", [])

        # Should not raise an exception if signature and algorithm are correct
        decoded = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        assert decoded["sub"] == "testuser"


class TestDecodeToken:
    def test_valid_token(self):
        token, _, _ = create_access_token("user1", "viewer", ["ch-1"])
        payload = decode_token(token)

        assert payload.sub == "user1"
        assert payload.role == "viewer"
        assert payload.scope == ["ch-1"]

    def test_expired_token(self):
        """Token with exp in the past must raise 401."""
        now_ts = int(time.time())
        payload = {
            "sub": "user",
            "iat": now_ts,
            "exp": now_ts - 10,
            "role": "viewer",
            "scope": [],
        }
        token = jwt.encode(
            payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
        )

        with pytest.raises(HTTPException) as excinfo:
            decode_token(token)
        assert excinfo.value.status_code == 401

    def test_invalid_signature(self):
        """Token signed with wrong key must raise 401."""
        payload = {
            "sub": "user",
            "iat": 1,
            "exp": 9999999999,
            "role": "admin",
            "scope": [],
        }
        token = jwt.encode(
            payload, "wrong-secret-key-that-is-long-enough", algorithm="HS256"
        )

        with pytest.raises(HTTPException) as excinfo:
            decode_token(token)
        assert excinfo.value.status_code == 401
