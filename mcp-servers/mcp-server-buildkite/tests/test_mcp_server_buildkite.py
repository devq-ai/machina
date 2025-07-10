import pytest
from fastapi.testclient import TestClient
from src.server import app
import os

client = TestClient(app)

@pytest.fixture
def buildkite_credentials():
    """Mocked Buildkite Credentials for testing."""
    os.environ["BUILDKITE_ACCESS_TOKEN"] = "testing"

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

def test_list_pipelines(buildkite_credentials):
    """Test the list_pipelines tool."""
    response = client.post("/tools/call", json={
        "name": "list_pipelines",
        "arguments": {
            "organization": "buildkite"
        }
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "pipelines" in data

def test_list_builds(buildkite_credentials):
    """Test the list_builds tool."""
    response = client.post("/tools/call", json={
        "name": "list_builds",
        "arguments": {
            "organization": "buildkite",
            "pipeline": "agent"
        }
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "builds" in data

def test_get_build(buildkite_credentials):
    """Test the get_build tool."""
    response = client.post("/tools/call", json={
        "name": "get_build",
        "arguments": {
            "organization": "buildkite",
            "pipeline": "agent",
            "build_number": 1
        }
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "build" in data
