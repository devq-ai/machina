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

def test_solve_model():
    """Test the solve_model tool."""
    # 1. Create a model
    model_id = "test_model"
    client.post("/tools/call", json={
        "name": "add_clause",
        "arguments": {
            "model_id": model_id,
            "clause": [-1, 2]
        }
    })
    client.post("/tools/call", json={
        "name": "add_clause",
        "arguments": {
            "model_id": model_id,
            "clause": [-2, 3]
        }
    })

    # 2. Solve the model
    response = client.post("/tools/call", json={
        "name": "solve_model",
        "arguments": {
            "model_id": model_id
        }
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["result"] == "SAT"
    assert "model" in data
