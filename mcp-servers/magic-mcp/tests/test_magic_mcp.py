import pytest
from fastapi.testclient import TestClient
from src.server import app
import os

client = TestClient(app)

@pytest.fixture
def magic_credentials():
    """Mocked Magic Credentials for testing."""
    os.environ["21STDEV_API_KEY"] = os.environ.get("21STDEV_API_KEY")

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

def test_create_ui_component(magic_credentials):
    """Test the create_ui_component tool."""
    response = client.post("/tools/call", json={
        "name": "create_ui_component",
        "arguments": {
            "prompt": "a modern navigation bar with responsive design"
        }
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "result" in data
