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

def test_jupyter_workflow():
    """Test the full Jupyter workflow: start, execute, and stop."""
    # 1. Start a kernel
    start_response = client.post("/tools/call", json={
        "name": "start_kernel",
        "arguments": {}
    })
    assert start_response.status_code == 200
    start_data = start_response.json()
    assert start_data["status"] == "success"
    assert "kernel_id" in start_data
    kernel_id = start_data["kernel_id"]

    # 2. Run some code
    execute_response = client.post("/tools/call", json={
        "name": "execute_code",
        "arguments": {
            "kernel_id": kernel_id,
            "code": "print('hello world')"
        }
    })
    assert execute_response.status_code == 200
    execute_data = execute_response.json()
    assert execute_data["status"] == "success"
    assert "result" in execute_data
    assert "hello world" in execute_data["result"]

    # 3. Stop the kernel
    stop_response = client.post("/tools/call", json={
        "name": "stop_kernel",
        "arguments": {
            "kernel_id": kernel_id
        }
    })
    assert stop_response.status_code == 200
    stop_data = stop_response.json()
    assert stop_data["status"] == "success"
    assert stop_data["kernel_id"] == kernel_id
