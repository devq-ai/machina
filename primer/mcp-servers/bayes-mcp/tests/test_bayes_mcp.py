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

def test_mcmc_sample():
    """Test the mcmc_sample tool."""
    response = client.post("/tools/call", json={
        "name": "mcmc_sample",
        "arguments": {
            "model_type": "linear_regression",
            "data": {
                "x": [1, 2, 3, 4, 5],
                "y": [2, 4, 5, 4, 5]
            },
            "draws": 1000,
            "tune": 1000
        }
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "summary" in data
