# machina/mcp/mcp-servers/task-master/app/db/in_memory_storage.py

from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid

class InMemoryTaskStorage:
    """
    In-memory storage for tasks. This will be replaced with a persistent
    database (like SurrealDB) for production readiness.
    """
    def __init__(self):
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.completed_tasks: set[str] = set()

    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a task by its ID."""
        return self.tasks.get(task_id)

    async def create_task(self, task_data: Dict[str, Any]) -> str:
        """Adds a new task to the storage and returns its ID."""
        task_id = str(uuid.uuid4())
        created_at = datetime.utcnow().isoformat()

        task = {
            "id": task_id,
            "title": task_data.get("title"),
            "description": task_data.get("description"),
            "priority": task_data.get("priority", "medium"),
            "dependencies": task_data.get("dependencies", []),
            "status": "pending", # Initial status
            "created_at": created_at,
            "updated_at": created_at,
            "completed_at": None,
            "subtasks": task_data.get("subtasks", [])
        }
        self.tasks[task_id] = task
        return task_id

    async def update_task(self, task_id: str, update_data: Dict[str, Any]) -> bool:
        """Updates an existing task with provided data."""
        if task_id not in self.tasks:
            return False

        task = self.tasks[task_id]
        updated = False

        for key, value in update_data.items():
            if key in task and task[key] != value:
                task[key] = value
                updated = True

        if updated:
            task["updated_at"] = datetime.utcnow().isoformat()
            if value == "completed":
                task["completed_at"] = task["updated_at"]
                self.completed_tasks.add(task_id)
            elif value != "completed":
                self.completed_tasks.discard(task_id) # Remove if status changes from completed

        return updated

    async def delete_task(self, task_id: str) -> bool:
        """Removes a task from storage."""
        if task_id in self.tasks:
            del self.tasks[task_id]
            self.completed_tasks.discard(task_id)
            return True
        return False

    async def list_tasks(self, filter_status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lists tasks, optionally filtered by status."""
        if filter_status:
            return [task for task in self.tasks.values() if task.get("status") == filter_status]
        return list(self.tasks.values())

    def get_completed_tasks_ids(self) -> set[str]:
        """Returns a set of IDs for completed tasks."""
        return self.completed_tasks

    def mark_task_completed(self, task_id: str) -> None:
        """Marks a task as completed."""
        if task_id in self.tasks:
            self.tasks[task_id]["status"] = "completed"
            self.tasks[task_id]["completed_at"] = datetime.utcnow().isoformat()
            self.completed_tasks.add(task_id)

    def reset_task_status(self, task_id: str) -> None:
        """Resets a task's status (e.g., from completed to pending)."""
        if task_id in self.tasks:
            if self.tasks[task_id]["status"] == "completed":
                self.tasks[task_id]["status"] = "pending"
                self.tasks[task_id]["completed_at"] = None
                self.completed_tasks.discard(task_id)
```
I have created the `machina/mcp/mcp-servers/task-master/app/db/in_memory_storage.py` file. This file provides a basic in-memory storage implementation for tasks, including methods for creating, retrieving, updating, deleting, listing, and marking tasks as completed.

My next steps are:

1.  **Integrate In-Memory Storage:** Modify `server.py` to use this in-memory storage for task operations.
2.  **Implement Core Logic:** Flesh out the `start_task` and `propagate_task_completion` methods in `server.py` to use the in-memory storage.
3.  **Set up Testing:** Create initial test files for the `task-master-mcp-server`.
4.  **Add Configuration Files:** Create `.env` and `requirements.txt`.

Let's start by integrating the `InMemoryTaskStorage` into `server.py`.
