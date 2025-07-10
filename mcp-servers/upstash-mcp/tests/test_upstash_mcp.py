import pytest
from fastapi.testclient import TestClient
from src.server import app
import os

client = TestClient(app)

@pytest.fixture
def upstash_credentials():
    """Mocked Upstash Credentials for testing."""
    os.environ["UPSTASH_REDIS_REST_URL"] = os.environ.get("UPSTASH_REDIS_REST_URL")
    os.environ["UPSTASH_REDIS_REST_TOKEN"] = os.environ.get("UPSTASH_REDIS_REST_TOKEN")

def test_health_check():
    """Test the health check endpoint."""
    response = client.post("/tools/call", json={
        "name": "health_check",
        "arguments": {}
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "service" in data
    assert "timestamp" in data

def test_redis_workflow(upstash_credentials):
    """Test the full redis workflow: set and get."""
    # 1. Set a value
    response = client.post("/tools/call", json={
        "name": "redis_set",
        "arguments": {
            "key": "test_key",
            "value": "test_value"
        }
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"

    # 2. Get the value
    response = client.post("/tools/call", json={
        "name": "redis_get",
        "arguments": {
            "key": "test_key"
        }
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["value"] == "test_value"

def test_create_embedding():
    """Test the create_embedding tool."""
    response = client.post("/tools/call", json={
        "name": "create_embedding",
        "arguments": {
            "text": "hello world"
        }
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "embedding" in data
