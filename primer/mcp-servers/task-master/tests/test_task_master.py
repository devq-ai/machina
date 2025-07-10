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

def test_task_workflow():
    """Test the full task workflow: create, get, update, list, and delete."""
    # 1. Create a task
    create_response = client.post("/tools/call", json={
        "name": "create_task",
        "arguments": {
            "title": "Test Task",
            "description": "This is a test task."
        }
    })
    assert create_response.status_code == 200
    create_data = create_response.json()
    assert create_data["status"] == "success"
    assert "task_id" in create_data
    task_id = create_data["task_id"]

    # 2. Get the task
    get_response = client.post("/tools/call", json={
        "name": "get_task",
        "arguments": {
            "task_id": task_id
        }
    })
    assert get_response.status_code == 200
    get_data = get_response.json()
    assert get_data["status"] == "success"
    assert get_data["task"]["title"] == "Test Task"

    # 3. Update the task
    update_response = client.post("/tools/call", json={
        "name": "update_task",
        "arguments": {
            "task_id": task_id,
            "status": "in_progress"
        }
    })
    assert update_response.status_code == 200
    update_data = update_response.json()
    assert update_data["status"] == "success"

    # 4. List the tasks
    list_response = client.post("/tools/call", json={
        "name": "list_tasks",
        "arguments": {}
    })
    assert list_response.status_code == 200
    list_data = list_response.json()
    assert list_data["status"] == "success"
    assert "tasks" in list_data
    assert task_id in list_data["tasks"]

    # 5. Delete the task
    delete_response = client.post("/tools/call", json={
        "name": "delete_task",
        "arguments": {
            "task_id": task_id
        }
    })
    assert delete_response.status_code == 200
    delete_data = delete_response.json()
    assert delete_data["status"] == "success"

    # 6. Verify that the task is gone
    get_response = client.post("/tools/call", json={
        "name": "get_task",
        "arguments": {
            "task_id": task_id
        }
    })
    assert get_response.status_code == 200
    get_data = get_response.json()
    assert get_data["status"] == "error"
    assert get_data["message"] == "Task not found."
