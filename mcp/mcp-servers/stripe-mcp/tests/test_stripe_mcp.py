import pytest
from fastapi.testclient import TestClient
from src.server import app
import os

client = TestClient(app)

@pytest.fixture
def stripe_credentials():
    """Mocked Stripe Credentials for testing."""
    os.environ["STRIPE_TOKEN"] = os.environ.get("STRIPE_TOKEN")

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

def test_create_payment_intent(stripe_credentials):
    """Test the create_payment_intent tool."""
    response = client.post("/tools/call", json={
        "name": "create_payment_intent",
        "arguments": {
            "amount": 1000,
            "currency": "usd"
        }
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "payment_intent" in data
