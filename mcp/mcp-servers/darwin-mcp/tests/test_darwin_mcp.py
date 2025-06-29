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

def test_evolve():
    """Test the evolve tool."""
    response = client.post("/tools/call", json={
        "name": "evolve",
        "arguments": {
            "fitness_function": "sphere",
            "genome_size": 10,
            "population_size": 50,
            "generations": 10
        }
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "best_individual" in data
    assert "best_fitness" in data
