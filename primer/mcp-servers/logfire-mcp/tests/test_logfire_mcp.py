import pytest
from fastapi.testclient import TestClient
from src.server import app
import os

client = TestClient(app)

@pytest.fixture
def logfire_credentials():
    """Mocked Logfire Credentials for testing."""
    os.environ["LOGFIRE_TOKEN"] = os.environ.get("LOGFIRE_WRITE_TOKEN")

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

def test_send_log(logfire_credentials):
    """Test the send_log tool."""
    response = client.post("/tools/call", json={
        "name": "send_log",
        "arguments": {
            "message": "test message",
            "level": "info"
        }
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
