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

def test_solve_constraint_problem():
    """Test the solve_constraint_problem tool."""
    response = client.post("/tools/call", json={
        "name": "solve_constraint_problem",
        "arguments": {
            "problem": {
                "variables": [
                    {"name": "x", "type": "integer"},
                    {"name": "y", "type": "integer"}
                ],
                "constraints": [
                    {"expression": "x + y == 10"},
                    {"expression": "x >= 0"},
                    {"expression": "y >= 0"}
                ]
            }
        }
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["result"] == "SAT"
    assert "model" in data
