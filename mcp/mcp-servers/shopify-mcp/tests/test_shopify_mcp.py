import pytest
from fastapi.testclient import TestClient
from src.server import app
import os

client = TestClient(app)

@pytest.fixture
def shopify_credentials():
    """Mocked Shopify Credentials for testing."""
    os.environ["SHOPIFY_API_KEY"] = "test"
    os.environ["SHOPIFY_PASSWORD"] = "test"
    os.environ["SHOPIFY_STORE_NAME"] = "test"

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

def test_get_products(shopify_credentials):
    """Test the get_products tool."""
    response = client.post("/tools/call", json={
        "name": "get_products",
        "arguments": {}
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "products" in data

def test_get_orders(shopify_credentials):
    """Test the get_orders tool."""
    response = client.post("/tools/call", json={
        "name": "get_orders",
        "arguments": {}
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "orders" in data

def test_create_product(shopify_credentials):
    """Test the create_product tool."""
    response = client.post("/tools/call", json={
        "name": "create_product",
        "arguments": {
            "title": "Test Product"
        }
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "product" in data
