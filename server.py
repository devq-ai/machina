# machina/mcp/mcp-servers/task-master/server.py

from fastmcp import MCPServer, Tool, ToolParameter
from typing import Dict, List, Any, Optional
import asyncio
from datetime import datetime

from app.db.in_memory_storage import InMemoryTaskStorage # Import the in-memory storage
import uuid # Ensure uuid is imported if not already

class TaskMasterServer(MCPServer):
    """
    MCP Server for managing tasks and orchestrating development workflows.
    Provides tools for task creation, status tracking, dependency management,
    and execution monitoring.
    """
    def __init__(self):
        super().__init__(
            name="task-master",
            version="1.0.0",
            description="Task management and orchestration server for MCP ecosystem",
            build_priority="high" # As per sprint plan
        )
        # Initialize the in-memory task storage
        self.task_storage = InMemoryTaskStorage()

        # Register MCP tools
        self.register_tool(self.create_task)
        self.register_tool(self.get_task_status)
        self.register_tool(self.list_tasks)
        self.register_tool(self.cancel_task)
        self.register_tool(self.update_task)
        self.register_tool(self.list_completed_tasks)
        self.register_tool(self.is_task_completed)

    @Tool(
        name="create_task",
        description="Create a new task with the specified parameters.",
        parameters=[
            ToolParameter(name="title", description="Task title", type="string", required=True),
            ToolParameter(name="description", description="Task description", type="string", required=True),
            ToolParameter(name="priority", description="Task priority (low, medium, high)", type="string", required=False, default="medium"),
            ToolParameter(name="dependencies", description="List of task IDs this task depends on", type="array", required=False, items={"type": "string"})
        ]
    )
    async def create_task(self, title: str, description: str, priority: str = \"medium\", dependencies: List[str] = None) -> Dict[str, Any]:
        \"\"\"Creates a new task and optionally starts it if dependencies are met.\"\"\"
        task_data = {
            \"title\": title,
            \"description\": description,
            \"priority\": priority,
            \"dependencies\": dependencies or [],
            \"subtasks\": [] # Initialize empty subtasks list
        }
        task_id = await self.task_storage.create_task(task_data)

        # Log task creation
        await self.log_event(f\"Task created: {task_id} - \'{title}\'\")

        # Check if task can be started immediately based on dependencies
        # Note: is_task_completed needs to access the storage
        if not dependencies or all(self.is_task_completed(dep) for dep in dependencies):
            await self.start_task(task_id)

        return {"task_id": task_id, "status": "created"}

    @Tool(
        name="get_task_status",
        description="Get the current status and details of a specific task.",
        parameters=[
            ToolParameter(name="task_id", description="ID of the task to retrieve", type="string", required=True)
        ]
    )
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        \"\"\"Retrieves the status and details of a given task.\"\"\"
        task = await self.task_storage.get_task(task_id)
        if not task:
            return {"error": f"Task with ID '{task_id}' not found."}
        return task

    @Tool(
        name="list_tasks",
        description="List all tasks, optionally filtered by status.",
        parameters=[
            ToolParameter(name="status", description="Filter tasks by status (pending, running, completed, failed, deferred)", type="string", required=False)
        ]
    )
    async def list_tasks(self, status: str = None) -> List[Dict[str, Any]]:
        \"\"\"Lists all tasks, with optional filtering by status.\"\"\"
        # Use the storage's list_tasks method
        return await self.task_storage.list_tasks(filter_status=status.lower() if status else None)

    @Tool(
        name="cancel_task",
        description="Cancel a task that is currently running or pending.",
        parameters=[
            ToolParameter(name="task_id", description="ID of the task to cancel", type="string", required=True)
        ]
    )
    async def cancel_task(self, task_id: str) -> Dict[str, Any]:
        \"\"\"Cancels a task.\"\"\"
        if task_id not in self.tasks: # This check might need adjustment if storage handles not found
            return {"error": f"Task with ID '{task_id}' not found."}

        task = self.tasks[task_id] # Get task from in-memory dict for now
        current_status = task.get("status")

        if current_status in ["pending", "running"]:
            update_data = {"status": "cancelled"}
            await self.task_storage.update_task(task_id, update_data) # Update via storage

            # Remove from completed_tasks set if it was there (e.g., if somehow marked completed before cancellation)
            self.completed_tasks.discard(task_id)

            await self.log_event(f"Task cancelled: {task_id} - '{task.get('title')}'")
            return {"task_id": task_id, "status": "cancelled"}
        else:
            return {"error": f"Task '{task_id}' cannot be cancelled as its status is '{current_status}'."}

    @Tool(
        name="update_task",
        description="Update an existing task's details, status, or subtasks.",
        parameters=[
            ToolParameter(name="task_id", description="ID of the task to update", type="string", required=True),
            ToolParameter(name="title", description="New title for the task", type="string", required=False),
            ToolParameter(name="description", description="New description for the task", type="string", required=False),
            ToolParameter(name="status", description="New status for the task (pending, running, completed, failed, deferred, cancelled)", type="string", required=False),
            ToolParameter(name="priority", description="New priority for the task", type="string", required=False),
            ToolParameter(name="dependencies", description="New list of dependency task IDs", type="array", required=False, items={"type": "string"}),
            ToolParameter(name="subtasks", description="New list of subtasks for the task", type="array", required=False, items={"type": "object"}) # Expecting list of task dicts
        ]
    )
    async def update_task(self, task_id: str, title: Optional[str] = None, description: Optional[str] = None, status: Optional[str] = None, priority: Optional[str] = None, dependencies: Optional[List[str]] = None, subtasks: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        \"\"\"Updates an existing task\'s properties.\"\"\"
        # The get_task method from storage should be used here
        task = await self.task_storage.get_task(task_id)
        if not task:
            return {"error": f"Task with ID '{task_id}' not found."}

        update_data = {}

        if title is not None and task.get("title") != title:
            update_data["title"] = title
        if description is not None and task.get("description") != description:
            update_data["description"] = description
        if priority is not None:
    # machina/mcp/mcp-servers/task-master/server.py

    from fastmcp import MCPServer, Tool, ToolParameter
    from typing import Dict, List, Any, Optional
    import asyncio
    from datetime import datetime

    from app.db.in_memory_storage import InMemoryTaskStorage # Import the in-memory storage
    import uuid # Ensure uuid is imported if not already

    class TaskMasterServer(MCPServer):
        """
        MCP Server for managing tasks and orchestrating development workflows.
        Provides tools for task creation, status tracking, dependency management,
        and execution monitoring.
        """
        def __init__(self):
            super().__init__(
                name="task-master",
                version="1.0.0",
                description="Task management and orchestration server for MCP ecosystem",
                build_priority="high" # As per sprint plan
            )
            # Initialize the in-memory task storage
            self.task_storage = InMemoryTaskStorage()

            # Register MCP tools
            self.register_tool(self.create_task)
            self.register_tool(self.get_task_status)
            self.register_tool(self.list_tasks)
            self.register_tool(self.cancel_task)
            self.register_tool(self.update_task)
            self.register_tool(self.list_completed_tasks)
            self.register_tool(self.is_task_completed)

        @Tool(
            name="create_task",
            description="Create a new task with the specified parameters.",
            parameters=[
                ToolParameter(name="title", description="Task title", type="string", required=True),
                ToolParameter(name="description", description="Task description", type="string", required=True),
                ToolParameter(name="priority", description="Task priority (low, medium, high)", type="string", required=False, default="medium"),
                ToolParameter(name="dependencies", description="List of task IDs this task depends on", type="array", required=False, items={"type": "string"})
            ]
        )
        async def create_task(self, title: str, description: str, priority: str = "medium", dependencies: List[str] = None) -> Dict[str, Any]:
            """Creates a new task and optionally starts it if dependencies are met."""
            task_data = {
                "title": title,
                "description": description,
                "priority": priority,
                "dependencies": dependencies or [],
                "subtasks": [] # Initialize empty subtasks list
            }
            task_id = await self.task_storage.create_task(task_data)

            # Log task creation
            await self.log_event(f"Task created: {task_id} - \'{title}\'")

            # Check if task can be started immediately based on dependencies
            # Note: is_task_completed needs to access the storage
            if not dependencies or all(self.is_task_completed(dep) for dep in dependencies):
                await self.start_task(task_id)

            return {"task_id": task_id, "status": "created"}

        @Tool(
            name="get_task_status",
            description="Get the current status and details of a specific task.",
            parameters=[
                ToolParameter(name="task_id", description="ID of the task to retrieve", type="string", required=True)
            ]
        )
        async def get_task_status(self, task_id: str) -> Dict[str, Any]:
            """Retrieves the status and details of a given task."""
            task = await self.task_storage.get_task(task_id)
            if not task:
                return {"error": f"Task with ID \'{task_id}' not found."}
            return task

        @Tool(
            name="list_tasks",
            description="List all tasks, optionally filtered by status.",
            parameters=[
                ToolParameter(name="status", description="Filter tasks by status (pending, running, completed, failed, deferred)", type="string", required=False)
            ]
        )
        async def list_tasks(self, status: str = None) -> List[Dict[str, Any]]:
            """Lists all tasks, with optional filtering by status."""
            # Use the storage's list_tasks method
            return await self.task_storage.list_tasks(filter_status=status.lower() if status else None)

        @Tool(
            name="cancel_task",
            description="Cancel a task that is currently running or pending.",
            parameters=[
                ToolParameter(name="task_id", description="ID of the task to cancel", type="string", required=True)
            ]
        )
        async def cancel_task(self, task_id: str) -> Dict[str, Any]:
            """Cancels a task."""
            task = await self.task_storage.get_task(task_id) # Use storage to get task
            if not task:
                return {"error": f"Task with ID \'{task_id}' not found."}

            current_status = task.get("status")

            if current_status in ["pending", "running"]:
                update_data = {"status": "cancelled"}
                await self.task_storage.update_task(task_id, update_data) # Update via storage

                # Remove from completed_tasks set if it was there (e.g., if somehow marked completed before cancellation)
                self.completed_tasks.discard(task_id)

                await self.log_event(f"Task cancelled: {task_id} - '{task.get('title')}'")
                return {"task_id": task_id, "status": "cancelled"}
            else:
                return {"error": f"Task \'{task_id}' cannot be cancelled as its status is \'{current_status}'.'"}

        @Tool(
            name="update_task",
            description="Update an existing task's details, status, or subtasks.",
            parameters=[
                ToolParameter(name="task_id", description="ID of the task to update", type="string", required=True),
                ToolParameter(name="title", description="New title for the task", type="string", required=False),
                ToolParameter(name="description", description="New description for the task", type="string", required=False),
                ToolParameter(name="status", description="New status for the task (pending, running, completed, failed, deferred, cancelled)", type="string", required=False),
                ToolParameter(name="priority", description="New priority for the task", type="string", required=False),
                ToolParameter(name="dependencies", description="New list of dependency task IDs", type="array", required=False, items={"type": "string"}),
                ToolParameter(name="subtasks", description="New list of subtasks for the task", type="array", required=False, items={"type": "object"}) # Expecting list of task dicts
            ]
        )
        async def update_task(self, task_id: str, title: Optional[str] = None, description: Optional[str] = None, status: Optional[str] = None, priority: Optional[str] = None, dependencies: Optional[List[str]] = None, subtasks: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
            """Updates an existing task's properties."""
            # The get_task method from storage should be used here
            task = await self.task_storage.get_task(task_id)
            if not task:
                return {"error": f"Task with ID \'{task_id}' not found."}

            update_data = {}

            if title is not None and task.get("title") != title:
                update_data["title"] = title
            if description is not None and task.get("description") != description:
                update_data["description"] = description
            if priority is not None:
                valid_priorities = ["low", "medium", "high"]
                if priority.lower() not in valid_priorities:
                    return {"error": f"Invalid priority \'{priority}'. Must be one of {valid_priorities}."}
                if task.get("priority") != priority.lower():
                    update_data["priority"] = priority.lower()
            if dependencies is not None and task.get("dependencies") != dependencies:
                update_data["dependencies"] = dependencies
            if subtasks is not None and task.get(\"subtasks\") != subtasks:
                update_data[\"subtasks\"] = subtasks

            # Handle status update separately as it has side effects (completed_tasks, starting tasks)
            if status is not None:
                new_status = status.lower()
                valid_statuses = ["pending", "running", "completed", "failed", "deferred", "cancelled"]
                if new_status not in valid_statuses:
                    return {"error": f"Invalid status \'{status}'. Must be one of {valid_statuses}."}

                old_status = task.get("status")
                if old_status != new_status:
                    update_data["status"] = new_status
                    if new_status == "completed":
                        # Mark as completed in storage and update completed_tasks set
                        await self.task_storage.mark_task_completed(task_id)
                        # Propagate completion if status changed to completed
                        await self.propagate_task_completion(task_id)
                    else:
                        # If status changes from completed, remove from completed_tasks set
                        self.completed_tasks.discard(task_id)
                        if new_status == "running" and old_status == "pending":
                            # If status changes to running, ensure it's not marked as completed
                            task["status"] = "running" # Reflect in memory immediately for subsequent checks within the same call.
                            # Note: The storage update will be handled below.
                            # We might need to ensure reset_task_status is called if it means changing *from* completed.
                            # For now, we assume update_task handles the state correctly.

                    await self.log_event(f"Task updated: {task_id} - Status changed from \'{old_status}\' to \'{new_status}\'")

            if not update_data and status is None: # No updates provided other than status
                 return {"message": f"No updates provided for task {task_id}."}

            # Perform the update using the storage layer
            success = await self.task_storage.update_task(task_id, update_data)

            if success:
                # Re-evaluate starting task if dependencies were updated and task is pending
                if "dependencies" in update_data and task.get("status") == "pending":
                    # Fetch the potentially updated task to check dependencies
                    current_task_state = await self.task_storage.get_task(task_id)
                    if current_task_state and all(self.is_task_completed(dep) for dep in current_task_state.get("dependencies", [])):
                        await self.start_task(task_id)

                task_title = task.get("title", "Untitled Task") # Get title for logging
                await self.log_event(f"Task updated: {task_id} - \'{task_title}\'")
                return {"task_id": task_id, "status": "updated"}
            else:
                return {"error": f"Failed to update task {task_id}."}

        async def start_task(self, task_id: str) -> None:
            """Internal method to start a task if it's pending and dependencies are met."""
            task = await self.task_storage.get_task(task_id) # Use storage to get task
            if not task:
                await self.log_event(f"Warning: Attempted to start non-existent task {task_id}")
                return

            current_status = task.get("status")
            if current_status == "pending":
                # Check dependencies using the storage's completed task tracking
                task_dependencies = task.get("dependencies", [])
                if not task_dependencies or all(self.is_task_completed(dep) for dep in task_dependencies):
                    update_data = {"status": "running"}
                    await self.task_storage.update_task(task_id, update_data)
                    self.completed_tasks.discard(task_id) # Ensure it's not marked as completed if it transitions to running
                    await self.log_event(f"Task started: {task_id} - '{task.get('title')}'")
                else:
                    await self.log_event(f"Task {task_id} dependencies not met, remaining pending.")
            else:
                await self.log_event(f"Task {task_id} is not pending (current status: {current_status}), cannot start.")

        @Tool(
            name="list_completed_tasks",
            description="List all tasks that have been marked as completed.",
            parameters=[]
        )
        async def list_completed_tasks(self) -> List[Dict[str, Any]]:
            """Lists all tasks marked as completed."""
            completed_task_ids = self.task_storage.get_completed_tasks_ids()
            tasks_list = []
            for task_id in completed_task_ids:
                task = await self.task_storage.get_task(task_id)
                if task:
                    tasks_list.append(task)
            return tasks_list

        @Tool(
            name="is_task_completed",
            description="Check if a given task ID has been completed.",
            parameters=[
                ToolParameter(name="task_id", description="ID of the task to check", type="string", required=True)
            ]
        )
        def is_task_completed(self, task_id: str) -> bool:
            """Checks if a task has been marked as completed."""
            # This check should ideally use the storage's knowledge of completed tasks.
            # For now, it relies on the in-memory set managed by the server instance,
            # which is updated via mark_task_completed and reset_task_status.
            # In a persistent storage scenario, this would query the DB.
            return self.task_storage.is_task_completed(task_id) # Use storage method

        async def propagate_task_completion(self, completed_task_id: str) -> None:
            """
            When a task is marked as completed, check all dependent tasks
            to see if they can now start. Uses the storage for task data.
            """
            await self.log_event(f"Propagating completion for task: {completed_task_id}")
            all_tasks = await self.task_storage.list_tasks() # Get all tasks from storage

            for task in all_tasks:
                task_id = task.get("id")
                if task.get("status") == "pending" and completed_task_id in task.get("dependencies", []):
                    # Check if all dependencies for this task are now completed
                    if all(self.is_task_completed(dep) for dep in task.get("dependencies", [])):
                        await self.start_task(task_id) # Attempt to start the task

        async def log_event(self, message: str) -> None:
            """
            Logs an event using the MCP server's internal logging mechanism.
            In a production setup, this would integrate with Logfire.
            """
            # Placeholder for actual logging integration (e.g., with Logfire)
            # For now, we'll just print to console.
            print(f"[TASK_MASTER_MCP] [{datetime.utcnow().isoformat()}] {message}")

    # Example of how to run this server (usually managed by FastMCP or a process manager)
    # if __name__ == "__main__":
    #     server = TaskMasterServer()
    #     server.start()
