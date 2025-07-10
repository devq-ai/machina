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

@pytest.mark.asyncio
async def test_puppeteer_navigate():
    """Test the puppeteer_navigate tool."""
    response = client.post("/tools/call", json={
        "name": "puppeteer_navigate",
        "arguments": {
            "url": "https://www.google.com"
        }
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
