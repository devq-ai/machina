import pytest
from fastapi.testclient import TestClient
from src.server import app
import os

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

def test_pulumi_workflow():
    """Test the full Pulumi workflow: preview, up, and stack_output."""
    workDir = os.path.abspath(os.path.join(os.path.dirname(__file__), "pulumi_project"))
    # 1. Preview the stack
    response = client.post("/tools/call", json={
        "name": "preview",
        "arguments": {
            "workDir": workDir
        }
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "preview" in data

    # 2. Update the stack
    response = client.post("/tools/call", json={
        "name": "up",
        "arguments": {
            "workDir": workDir
        }
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "up" in data

    # 3. Get the stack output
    response = client.post("/tools/call", json={
        "name": "stack_output",
        "arguments": {
            "workDir": workDir
        }
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "output" in data
    assert data["output"]["foo"] == "bar"
