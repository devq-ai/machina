"""
MCP Tools Implementation
"""

from typing import Dict, Any, List
import mcp.types as types
from datetime import datetime

TASKS = {}


def get_tools() -> List[types.Tool]:
    """Define available tools"""
    return [
        types.Tool(
            name="create_task",
            description="Creates a new task.",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "The title of the task."
                    },
                    "description": {
                        "type": "string",
                        "description": "The description of the task."
                    }
                },
                "required": ["title"]
            }
        ),
        types.Tool(
            name="get_task",
            description="Gets a task by ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "The ID of the task to get."
                    }
                },
                "required": ["task_id"]
            }
        ),
        types.Tool(
            name="update_task",
            description="Updates a task.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "The ID of the task to update."
                    },
                    "title": {
                        "type": "string",
                        "description": "The new title of the task."
                    },
                    "description": {
                        "type": "string",
                        "description": "The new description of the task."
                    },
                    "status": {
                        "type": "string",
                        "description": "The new status of the task."
                    }
                },
                "required": ["task_id"]
            }
        ),
        types.Tool(
            name="delete_task",
            description="Deletes a task.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "The ID of the task to delete."
                    }
                },
                "required": ["task_id"]
            }
        ),
        types.Tool(
            name="list_tasks",
            description="Lists all tasks.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="health_check",
            description="Check server health",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]


async def handle_tool_call(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Handle tool execution"""
    if name == "create_task":
        task_id = str(datetime.now().timestamp())
        TASKS[task_id] = {
            "title": arguments["title"],
            "description": arguments.get("description", ""),
            "status": "open"
        }
        return {
            "status": "success",
            "task_id": task_id,
            "timestamp": str(datetime.now())
        }
    elif name == "get_task":
        task_id = arguments["task_id"]
        if task_id in TASKS:
            return {
                "status": "success",
                "task": TASKS[task_id],
                "timestamp": str(datetime.now())
            }
        else:
            return {
                "status": "error",
                "message": "Task not found.",
                "timestamp": str(datetime.now())
            }
    elif name == "update_task":
        task_id = arguments["task_id"]
        if task_id in TASKS:
            for key, value in arguments.items():
                if key != "task_id":
                    TASKS[task_id][key] = value
            return {
                "status": "success",
                "timestamp": str(datetime.now())
            }
        else:
            return {
                "status": "error",
                "message": "Task not found.",
                "timestamp": str(datetime.now())
            }
    elif name == "delete_task":
        task_id = arguments["task_id"]
        if task_id in TASKS:
            del TASKS[task_id]
            return {
                "status": "success",
                "timestamp": str(datetime.now())
            }
        else:
            return {
                "status": "error",
                "message": "Task not found.",
                "timestamp": str(datetime.now())
            }
    elif name == "list_tasks":
        return {
            "status": "success",
            "tasks": TASKS,
            "timestamp": str(datetime.now())
        }
    elif name == "health_check":
        return {
            "status": "healthy",
            "service": "task-master",
            "timestamp": str(datetime.now())
        }
    else:
        return {"error": f"Unknown tool: {name}"}
