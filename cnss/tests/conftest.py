import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.auth import create_access_token


@pytest.fixture(scope="module")
def client():
    """
    TestClient fixture for FastAPI integration testing.
    Created once per test module to save resources.
    """
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def admin_token():
    """Generates a valid JWT token for an admin user."""
    token, _, _ = create_access_token("admin", "admin", ["bridge-berlin-01"])
    return token


@pytest.fixture(scope="module")
def viewer_token():
    """Generates a valid JWT token for a viewer user with restricted scope."""
    token, _, _ = create_access_token("viewer", "viewer", ["bridge-berlin-01"])
    return token


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    """Formats the admin token into an HTTP Authorization header."""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="module")
def viewer_headers(viewer_token):
    """Formats the viewer token into an HTTP Authorization header."""
    return {"Authorization": f"Bearer {viewer_token}"}
