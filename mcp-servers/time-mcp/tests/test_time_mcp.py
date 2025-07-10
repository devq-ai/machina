from fastapi.testclient import TestClient
from src.server import app

client = TestClient(app)

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

def test_get_current_time():
    """Test the get_current_time tool."""
    response = client.post("/tools/call", json={
        "name": "get_current_time",
        "arguments": {
            "timezone": "UTC"
        }
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "time" in data

def test_convert_time():
    """Test the convert_time tool."""
    response = client.post("/tools/call", json={
        "name": "convert_time",
        "arguments": {
            "time": "2024-01-01T00:00:00",
            "from_timezone": "UTC",
            "to_timezone": "US/Pacific"
        }
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "time" in data
