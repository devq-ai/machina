import pytest
from fastapi.testclient import TestClient
from src.server import app
import os

client = TestClient(app)

@pytest.fixture
def brightdata_credentials():
    """Mocked BrightData Credentials for testing."""
    os.environ["BRIGHTDATA_API_KEY"] = os.environ.get("EXA_API_KEY")

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

def test_web_search(brightdata_credentials):
    """Test the web_search tool."""
    response = client.post("/tools/call", json={
        "name": "web_search",
        "arguments": {
            "query": "what is the capital of france"
        }
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "results" in data
