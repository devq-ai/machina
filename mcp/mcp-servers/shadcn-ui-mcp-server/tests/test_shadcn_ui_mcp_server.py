import pytest
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

def test_get_component():
    """Test the get_component tool."""
    response = client.post("/tools/call", json={
        "name": "get_component",
        "arguments": {
            "component_name": "button"
        }
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "source_code" in data

def test_get_component_demo():
    """Test the get_component_demo tool."""
    response = client.post("/tools/call", json={
        "name": "get_component_demo",
        "arguments": {
            "component_name": "button"
        }
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "demo" in data
