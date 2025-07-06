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

def test_memory_workflow():
    """Test the full memory workflow: save, load, list, and delete."""
    # 1. Save a value
    save_response = client.post("/tools/call", json={
        "name": "save",
        "arguments": {
            "key": "test_key",
            "value": "test_value"
        }
    })
    assert save_response.status_code == 200
    save_data = save_response.json()
    assert save_data["status"] == "success"

    # 2. Load the value
    load_response = client.post("/tools/call", json={
        "name": "load",
        "arguments": {
            "key": "test_key"
        }
    })
    assert load_response.status_code == 200
    load_data = load_response.json()
    assert load_data["status"] == "success"
    assert load_data["value"] == "test_value"

    # 3. List the keys
    list_response = client.post("/tools/call", json={
        "name": "list",
        "arguments": {}
    })
    assert list_response.status_code == 200
    list_data = list_response.json()
    assert list_data["status"] == "success"
    assert "keys" in list_data
    assert "test_key" in list_data["keys"]

    # 4. Delete the value
    delete_response = client.post("/tools/call", json={
        "name": "delete",
        "arguments": {
            "key": "test_key"
        }
    })
    assert delete_response.status_code == 200
    delete_data = delete_response.json()
    assert delete_data["status"] == "success"

    # 5. Verify that the key is gone
    load_response = client.post("/tools/call", json={
        "name": "load",
        "arguments": {
            "key": "test_key"
        }
    })
    assert load_response.status_code == 200
    load_data = load_response.json()
    assert load_data["status"] == "error"
    assert load_data["message"] == "Key not found."
