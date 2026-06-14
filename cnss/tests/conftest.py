import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(scope="module")
def client():
    """
    TestClient fixture for FastAPI integration testing.
    Created once per test module to save resources.
    """
    with TestClient(app) as c:
        yield c
