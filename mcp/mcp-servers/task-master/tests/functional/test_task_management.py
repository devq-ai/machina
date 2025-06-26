# machina/mcp/mcp-servers/task-master/tests/functional/test_task_management.py

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock

# Assuming TaskMasterServer and InMemoryTaskStorage are accessible
# In a real scenario, you might need to adjust import paths or mock dependencies
# For now, we'll assume they are importable, or mock them if not directly available during test setup
from ...server import TaskMasterServer
from ...app.db.in_memory_storage import InMemoryTaskStorage

# Helper to get a time string similar to datetime.utcnow().isoformat()
def get_current_time_str():
    return datetime.utcnow().isoformat()

# --- Fixtures ---

@pytest.fixture
async def server():
    """Provides a TaskMasterServer instance with in-memory storage for tests."""
    # Mocking the server's internal storage to ensure isolation and control
    mock_storage = InMemoryTaskStorage()
    server_instance = TaskMasterServer()

    # Replace the actual storage with our mock/instance for isolated testing
    server_instance.task_storage = mock_storage

    # Mock log_event for cleaner test output
    server_instance.log_event = AsyncMock()

    yield server_instance

@pytest.fixture
async def mock_storage(server):
    """Provides direct access to the server's mocked storage."""
    return server.task_storage

# --- Test Cases ---

# Test create_task
@pytest.mark.asyncio
async def test_create_task(server, mock_storage):
    """Tests the creation of a new task."""
    response = await server.create_task(
        title="Test Task Creation",
        description="This is a test task.",
        priority="high"
    )
    assert response["status"] == "created"
    task_id = response["task_id"]
    assert task_id is not None

    # Verify task was stored
    stored_task = await mock_storage.get_task(task_id)
    assert stored_task is not None
    assert stored_task["title"] == "Test Task Creation"
    assert stored_task["description"] == "This is a test task."
    assert stored_task["priority"] == "high"
    assert stored_task["status"] == "pending" # Should be pending initially
    assert stored_task["dependencies"] == []
    assert stored_task["created_at"] is not None
    assert stored_task["updated_at"] is not None

    # Test task creation with dependencies
    response_with_dep = await server.create_task(
        title="Task with Dependency",
        description="This task depends on the first one.",
        dependencies=[task_id]
    )
    assert response_with_dep["status"] == "created"
    task_with_dep_id = response_with_dep["task_id"]
    stored_task_with_dep = await mock_storage.get_task(task_with_dep_id)
    assert stored_task_with_dep["dependencies"] == [task_id]

    # Test invalid priority
    response_invalid_priority = await server.create_task(
        title="Invalid Priority Task",
        description="This task has an invalid priority.",
        priority="extreme"
    )
    assert "error" in response_invalid_priority
    assert "Invalid priority 'extreme'" in response_invalid_priority["error"]

# Test get_task_status
@pytest.mark.asyncio
async def test_get_task_status(server, mock_storage):
    """Tests retrieving the status of an existing task."""
    # Create a task first
    create_response = await server.create_task(title="Get Status Task", description="Task for status check")
    task_id = create_response["task_id"]

    # Get its status
    status_response = await server.get_task_status(task_id)
    assert status_response is not None
    assert status_response["id"] == task_id
    assert status_response["status"] == "pending"

    # Test getting status for a non-existent task
    non_existent_response = await server.get_task_status("non-existent-id")
    assert "error" in non_existent_response
    assert "not found" in non_existent_response["error"]

# Test list_tasks (no filter)
@pytest.mark.asyncio
async def test_list_tasks_all(server, mock_storage):
    """Tests listing all tasks."""
    await server.create_task(title="Task A", description="First task")
    await server.create_task(title="Task B", description="Second task")

    all_tasks = await server.list_tasks()
    assert len(all_tasks) >= 2 # Ensure we have at least the two tasks we created

# Test list_tasks (with status filter)
@pytest.mark.asyncio
async def test_list_tasks_filtered(server, mock_storage):
    """Tests listing tasks filtered by status."""
    # Create tasks
    await server.create_task(title="Pending Task", description="Should be pending", status="pending")
    await server.create_task(title="Running Task", description="Should be running", status="running")
    # Mark one as completed
    completed_task_data = await mock_storage.get_task("pending-task-id") # Placeholder, will be actual ID
    if completed_task_data: # This check is necessary because get_task is async
        await mock_storage.mark_task_completed("pending-task-id") # Assuming task_id is 'pending-task-id' for this test
    else: # If task not found, create it and mark completed
        pending_task_id = (await server.create_task(title="Pending Task", description="Should be pending", status="pending"))["task_id"]
        await mock_storage.mark_task_completed(pending_task_id) # Mark it as completed

    # Need to create tasks with known IDs for filtering tests or retrieve them.
    # Let's re-create with explicit IDs for easier testing.
    # Re-init server to ensure a clean state for this specific test's setup
    server_for_filter = TaskMasterServer()
    server_for_filter.task_storage = InMemoryTaskStorage()
    server_for_filter.log_event = AsyncMock()

    task_p_id = (await server_for_filter.create_task(title="Pending Task", description="Should be pending", status="pending"))["task_id"]
    task_r_id = (await server_for_filter.create_task(title="Running Task", description="Should be running", status="running"))["task_id"]
    task_c_id = (await server_for_filter.create_task(title="Completed Task", description="Should be completed", status="completed"))["task_id"]
    # Ensure the completed task is marked in storage
    await server_for_filter.task_storage.mark_task_completed(task_c_id)

    # List pending tasks
    pending_tasks = await server_for_filter.list_tasks(status="pending")
    assert len(pending_tasks) == 1
    assert pending_tasks[0]["id"] == task_p_id

    # List running tasks
    running_tasks = await server_for_filter.list_tasks(status="running")
    assert len(running_tasks) == 1
    assert running_tasks[0]["id"] == task_r_id

    # List completed tasks
    completed_tasks = await server_for_filter.list_tasks(status="completed")
    assert len(completed_tasks) == 1
    assert completed_tasks[0]["id"] == task_c_id

    # List non-existent status
    non_existent_status_tasks = await server_for_filter.list_tasks(status="nonexistent")
    assert len(non_existent_status_tasks) == 0

# Test cancel_task
@pytest.mark.asyncio
async def test_cancel_task(server, mock_storage):
    """Tests cancelling a task."""
    # Create a task
    create_response = await server.create_task(title="Cancel Task", description="Task to be cancelled")
    task_id = create_response["task_id"]

    # Cancel the task
    cancel_response = await server.cancel_task(task_id)
    assert cancel_response["status"] == "cancelled"
    assert cancel_response["task_id"] == task_id

    # Verify status change in storage
    updated_task = await mock_storage.get_task(task_id)
    assert updated_task is not None
    assert updated_task["status"] == "cancelled"

    # Test cancelling a non-existent task
    cancel_non_existent = await server.cancel_task("non-existent-id")
    assert "error" in cancel_non_existent
    assert "not found" in cancel_non_existent["error"]

    # Test cancelling a task that is already completed (should fail)
    # Create and complete a task
    completed_task_create = await server.create_task(title="Completed Task for Cancel Test", description="This task will be completed.")
    completed_task_id = completed_task_create["task_id"]
    await mock_storage.mark_task_completed(completed_task_id) # Manually mark as completed for test setup
    server.completed_tasks.add(completed_task_id) # Add to memory set for is_task_completed check if needed immediately

    cancel_completed = await server.cancel_task(completed_task_id)
    assert "error" in cancel_completed
    assert "cannot be cancelled" in cancel_completed["error"]

# Test update_task (title, description, priority, dependencies)
@pytest.mark.asyncio
async def test_update_task_basic(server, mock_storage):
    \"\"\"Tests updating task title, description, priority, and dependencies.\"\"\"\
    # Create a task
    create_response = await server.create_task(title=\"Initial Task\", description=\"Initial desc\", priority=\"low\")
    task_id = create_response[\"task_id\"]

    # Update title, description, priority
    update_response = await server.update_task(
        task_id=task_id,
        title=\"Updated Task Title\",
        description=\"Updated description.\",
        priority=\"high\"
    )
    assert update_response[\"status\"] == \"updated\"

    # Verify updates in storage
    task = await mock_storage.get_task(task_id)
    assert task[\"title\"] == \"Updated Task Title\"
    assert task[\"description\"] == \"Updated description.\"
    assert task[\"priority\"] == \"high\"

    # Test updating dependencies
    # Create another task to be a dependency
    dep_create_response = await server.create_task(title=\"Dependency Task\", description=\"This is a dependency\")
    dep_task_id = dep_create_response[\"task_id\"]

    update_deps_response = await server.update_task(
        task_id=task_id,
        dependencies=[dep_task_id]
    )
    assert update_deps_response[\"status\"] == \"updated\"
    task_after_deps_update = await mock_storage.get_task(task_id)
    assert task_after_deps_update[\"dependencies\"] == [dep_task_id]

    # Test invalid priority update
    invalid_priority_update = await server.update_task(task_id=task_id, priority=\"extreme\")
    assert \"error\" in invalid_priority_update

# Test update_task (status)
@pytest.mark.asyncio
async def test_update_task_status(server, mock_storage):
    \"\"\"Tests updating a task\'s status and its side effects.\"\"\"\
    # Create a task\n    create_response = await server.create_task(title=\"Status Update Task\", description=\"Task for status tests\")\n    task_id = create_response[\"task_id\"]\n\n    # Create a dependency task that will be completed later\n    dep_create_response = await server.create_task(title=\"Dependency for Status\", description=\"This will be completed\")\n    dep_task_id = dep_create_response[\"task_id\"]\n\n    # Update status to running (should not affect completed_tasks)\n    update_running = await server.update_task(task_id=task_id, status=\"running\")\n    assert update_running[\"status\"] == \"updated\"\n    task_running = await mock_storage.get_task(task_id)\n    assert task_running[\"status\"] == \"running\"\n    # Ensure it\'s not marked as completed in the server\'s memory set\n    assert task_id not in server.completed_tasks\n\n    # Update status to completed\n    update_completed = await server.update_task(task_id=task_id, status=\"completed\")\n    assert update_completed[\"status\"] == \"updated\"\n    task_completed = await mock_storage.get_task(task_id)\n    assert task_completed[\"status\"] == \"completed\"\n    # Check if added to completed_tasks set in server memory (should be managed by storage implicitly, but good to verify)\n    # The `mark_task_completed` in storage should handle this, and `is_task_completed` uses storage.\n    # However, `propagate_task_completion` directly uses `is_task_completed` which uses storage.\n    # The server\'s internal `self.completed_tasks` set might be redundant if storage handles it.\n    # For now, we rely on `is_task_completed` using storage. If `update_task` calls `mark_task_completed` properly, this is covered.\n\n    # Test updating status from completed back to pending\n    update_pending = await server.update_task(task_id=task_id, status=\"pending\")\n    assert update_pending[\"status\"] == \"updated\"\n    task_pending = await mock_storage.get_task(task_id)\n    assert task_pending[\"status\"] == \"pending\"\n    # After resetting status, it should not be considered completed\n    assert task_id not in server.completed_tasks\n\n    # Test updating status to failed\n    update_failed = await server.update_task(task_id=task_id, status=\"failed\")\n    assert update_failed[\"status\"] == \"updated\"\n    task_failed = await mock_storage.get_task(task_id)\n    assert task_failed[\"status\"] == \"failed\"\n    assert task_id not in server.completed_tasks\n\n    # Test updating status to cancelled\n    update_cancelled = await server.update_task(task_id=task_id, status=\"cancelled\")\n    assert update_cancelled[\"status\"] == \"updated\"\n    task_cancelled = await mock_storage.get_task(task_id)\n    assert task_cancelled[\"status\"] == \"cancelled\"\n    assert task_id not in server.completed_tasks\n\n    # Test invalid status update\n    invalid_status_update = await server.update_task(task_id=task_id, status=\"unknown\")\n    assert \"error\" in invalid_status_update\n

# Test start_task (internal method, indirectly tested via create_task and update_task)
@pytest.mark.asyncio
async def test_start_task_behavior(server, mock_storage):
    """Tests the internal start_task logic triggered by dependency resolution."""
    # Create a task with a dependency
    dep_task_create = await server.create_task(title="Dependency Task", description="This task will be completed")
    dep_task_id = dep_task_create["task_id"]

    task_id = (await server.create_task(
        title="Task with Dependency",
        description="This task depends on dep_task_id",
        dependencies=[dep_task_id]
    ))["task_id"]

    # Initially, task should be pending
    task_initial = await mock_storage.get_task(task_id)
    assert task_initial["status"] == "pending"

    # Complete the dependency task
    await mock_storage.mark_task_completed(dep_task_id)
    server.completed_tasks.add(dep_task_id) # Add to memory set for is_task_completed to work immediately in this test

    # After completing dependency, start_task should be triggered by `propagate_task_completion`
    # which is called by `update_task` when status is set to 'completed'.
    # However, `create_task` calls `start_task` if dependencies are initially met.
    # Let's test the `create_task` initial start behavior.
    # If the dependency was already met (which it isn't initially), it would start.
    # The crucial test is when a dependency is completed *after* the task is created.
    # This is tested implicitly by `propagate_task_completion` in `update_task` tests.
    # Let's add a direct check here for `start_task` call if needed.

    # To directly test start_task, we need to call it after marking dependency complete
    # The `propagate_task_completion` is called when a task is updated to 'completed'.
    # Let's simulate that scenario to ensure `start_task` is correctly invoked.
    # For explicit test of start_task directly:
    await server.start_task(task_id) # This call itself should check dependencies if task is pending
    task_after_start_attempt = await mock_storage.get_task(task_id)
    assert task_after_start_attempt["status"] == "pending" # Still pending because dependency wasn't met *at time of start_task call*

    # Now, let's test propagate_task_completion more directly through an update
    # Complete the dependency task
    await server.update_task(task_id=dep_task_id, status="completed") # This should trigger propagate_task_completion

    # Check if the dependent task has now started
    task_after_propagation = await mock_storage.get_task(task_id)
    assert task_after_propagation["status"] == "running"

# Test propagate_task_completion (indirectly tested by status updates)
# This is implicitly tested when a task with dependencies is updated to 'completed'
# and its dependent tasks transition from 'pending' to 'running'.

# Test is_task_completed
@pytest.mark.asyncio
async def test_is_task_completed(server, mock_storage):
    """Tests the is_task_completed check."""
    # Create a task
    create_response = await server.create_task(title="Completion Check Task", description="Task for completion check")
    task_id = create_response["task_id"]

    # Initially, it should not be completed
    assert not server.is_task_completed(task_id)

    # Mark as completed
    await mock_storage.mark_task_completed(task_id)
    server.completed_tasks.add(task_id) # Ensure memory set is updated too for is_task_completed to work

    # Now it should be completed
    assert server.is_task_completed(task_id)

    # Test for a non-existent task
    assert not server.is_task_completed("non-existent-id")

# Test list_completed_tasks
@pytest.mark.asyncio
async def test_list_completed_tasks(server, mock_storage):
    """Tests listing only completed tasks."""
    # Create tasks
    task1_create = await server.create_task(title="Task 1", description="First task")
    task1_id = task1_create["task_id"]
    task2_create = await server.create_task(title="Task 2", description="Second task")
    task2_id = task2_create["task_id"]
    task3_create = await server.create_task(title="Task 3", description="Third task")
    task3_id = task3_create["task_id"]

    # Mark task 2 and 3 as completed
    await mock_storage.mark_task_completed(task2_id)
    server.completed_tasks.add(task2_id)
    await mock_storage.mark_task_completed(task3_id)
    server.completed_tasks.add(task3_id)

    # List completed tasks
    completed_tasks = await server.list_completed_tasks()
    assert len(completed_tasks) == 2
    completed_ids = {t["id"] for t in completed_tasks}
    assert task2_id in completed_ids
    assert task3_id in completed_ids
    assert task1_id not in completed_ids

    # Test with no completed tasks
    empty_server = TaskMasterServer()
    empty_server.task_storage = InMemoryTaskStorage()
    empty_server.log_event = AsyncMock()
    assert await empty_server.list_completed_tasks() == []
