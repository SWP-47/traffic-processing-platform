import jwt
import time
from datetime import datetime, timezone
from .config import settings

# MVP v1 Mock User Store
# In future iterations, this will be replaced by a secure database lookup.
MOCK_USERS = {
    "admin": {
        "password": "admin123",
        "role": "admin",
        "scope": []  # Admin scope is dynamically populated at login
    },
    "viewer": {
        "password": "viewer123",
        "role": "viewer",
        "scope": ["bridge-berlin-01", "bridge-prague-01"]
    }
}

def authenticate_user(username: str, password: str) -> dict | None:
    """Validates credentials against the mock store."""
    user = MOCK_USERS.get(username)
    if not user or user["password"] != password:
        return None
    return user

def create_access_token(username: str, role: str, scope: list[str]) -> tuple[str, int, str]:
    """
    Generates an HS256 signed JWT (AC 4 & AC 5).
    Returns: (token_string, expires_in_seconds, issued_at_iso_string)
    """
    now_ts = int(time.time())
    exp_ts = now_ts + settings.jwt_expiration_seconds
    
    payload = {
        "sub": username,
        "iat": now_ts,
        "exp": exp_ts,
        "role": role,
        "scope": scope
    }
    
    token = jwt.encode(
        payload, 
        settings.jwt_secret_key, 
        algorithm=settings.jwt_algorithm
    )
    
    # Format issued_at as ISO 8601
    issued_at_iso = datetime.fromtimestamp(now_ts, tz=timezone.utc).isoformat().replace("+00:00", "Z")
    
    return token, settings.jwt_expiration_seconds, issued_at_iso