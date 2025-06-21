"""
MCP Tools Definitions and Utilities

This module provides MCP (Model Context Protocol) tool definitions, utilities,
and helper functions for the Machina Registry Service. It defines the individual
MCP tools that expose TaskMaster AI functionality to MCP clients.

Features:
- Individual MCP tool definitions
- Tool metadata and schemas
- Utility functions for tool management
- Integration helpers for MCP server
- Tool validation and error handling
"""

from typing import Any, Dict, List, Optional, Callable, Awaitable
from datetime import datetime
from enum import Enum

import logfire
from mcp import types


class MCPToolCategory(str, Enum):
    """Categories for organizing MCP tools."""
    TASK_MANAGEMENT = "task_management"
    ANALYSIS = "analysis"
    ANALYTICS = "analytics"
    SEARCH = "search"
    MONITORING = "monitoring"
    DEPENDENCIES = "dependencies"


class MCPTool:
    """
    Represents a single MCP tool with metadata and execution handler.
    """

    def __init__(
        self,
        name: str,
        description: str,
        category: MCPToolCategory,
        input_schema: Dict[str, Any],
        handler: Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]],
        examples: Optional[List[Dict[str, Any]]] = None
    ):
        """
        Initialize an MCP tool.

        Args:
            name: Tool name (unique identifier)
            description: Human-readable description
            category: Tool category for organization
            input_schema: JSON schema for input validation
            handler: Async function to execute the tool
            examples: Optional usage examples
        """
        self.name = name
        self.description = description
        self.category = category
        self.input_schema = input_schema
        self.handler = handler
        self.examples = examples or []

    def to_mcp_tool(self) -> types.Tool:
        """Convert to MCP Tool type."""
        return types.Tool(
            name=self.name,
            description=self.description,
            inputSchema=self.input_schema
        )

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with given arguments."""
        try:
            with logfire.span(f"MCP Tool Execution: {self.name}", arguments=arguments):
                result = await self.handler(arguments)
                logfire.info(f"MCP tool {self.name} executed successfully")
                return result
        except Exception as e:
            logfire.error(f"MCP tool {self.name} execution failed", error=str(e))
            raise


def create_task_management_tools() -> List[MCPTool]:
    """Create task management MCP tools."""

    async def get_tasks_handler(args: Dict[str, Any]) -> Dict[str, Any]:
        """Handler for get_tasks tool."""
        # This will be injected with the actual TaskMaster service
        from ..services.taskmaster_service import TaskMasterService
        from ..core.cache import get_cache_service

        cache_service = await get_cache_service()
        taskmaster = TaskMasterService(cache_service)

        filters = {k: v for k, v in args.items() if k not in ["limit", "offset"] and v is not None}
        limit = args.get("limit", 10)
        offset = args.get("offset", 0)

        # Convert to TaskFilter if filters exist
        task_filter = None
        if filters:
            from ..models.task_models import TaskFilter
            task_filter = TaskFilter(**filters)

        # Use list_tasks method with pagination
        page = (offset // limit) + 1 if limit > 0 else 1
        page_size = limit

        tasks = await taskmaster.list_tasks(
            filters=task_filter,
            page=page,
            page_size=page_size
        )
        return {
            "tasks": tasks,
            "count": len(tasks),
            "filters_applied": filters,
            "pagination": {"limit": limit, "offset": offset, "page": page}
        }

    async def get_task_handler(args: Dict[str, Any]) -> Dict[str, Any]:
        """Handler for get_task tool."""
        from ..services.taskmaster_service import TaskMasterService
        from ..core.cache import get_cache_service

        cache_service = await get_cache_service()
        taskmaster = TaskMasterService(cache_service)

        task_id = str(args["task_id"])
        task = await taskmaster.get_task(task_id, raise_if_not_found=False)

        if not task:
            return {"error": f"Task {task_id} not found"}

        return {"task": task}

    async def create_task_handler(args: Dict[str, Any]) -> Dict[str, Any]:
        """Handler for create_task tool."""
        from ..services.taskmaster_service import TaskMasterService
        from ..core.cache import get_cache_service

        cache_service = await get_cache_service()
        taskmaster = TaskMasterService(cache_service)

        task_data = args.copy()
        task = await taskmaster.create_task(task_data)

        return {
            "message": "Task created successfully",
            "task": task
        }

    async def update_task_status_handler(args: Dict[str, Any]) -> Dict[str, Any]:
        """Handler for update_task_status tool."""
        from ..services.taskmaster_service import TaskMasterService
        from ..core.cache import get_cache_service
        from ..models.task_models import TaskStatus

        cache_service = await get_cache_service()
        taskmaster = TaskMasterService(cache_service)

        task_id = str(args["task_id"])
        status = TaskStatus(args["status"])
        notes = args.get("notes")

        try:
            updated_task = await taskmaster.update_task_status(task_id, status, notes)
            return {
                "message": f"Task {task_id} status updated to {status}",
                "task_id": task_id,
                "new_status": status,
                "notes": notes,
                "task": updated_task
            }
        except Exception as e:
            return {"error": f"Failed to update task {task_id} status: {str(e)}"}

    async def update_task_progress_handler(args: Dict[str, Any]) -> Dict[str, Any]:
        """Handler for update_task_progress tool."""
        from ..services.taskmaster_service import TaskMasterService
        from ..core.cache import get_cache_service

        cache_service = await get_cache_service()
        taskmaster = TaskMasterService(cache_service)

        task_id = str(args["task_id"])
        progress = float(args["progress"])
        notes = args.get("notes")

        try:
            updated_task = await taskmaster.update_task_progress(task_id, progress, notes)
            return {
                "message": f"Task {task_id} progress updated to {progress}%",
                "task_id": task_id,
                "progress": progress,
                "notes": notes,
                "task": updated_task
            }
        except Exception as e:
            return {"error": f"Failed to update task {task_id} progress: {str(e)}"}

    return [
        MCPTool(
            name="get_tasks",
            description="Get all tasks with optional filtering and pagination",
            category=MCPToolCategory.TASK_MANAGEMENT,
            input_schema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "Filter by task status",
                        "enum": ["pending", "in_progress", "done", "deferred", "cancelled"]
                    },
                    "priority": {
                        "type": "string",
                        "description": "Filter by task priority",
                        "enum": ["low", "medium", "high", "critical"]
                    },
                    "task_type": {
                        "type": "string",
                        "description": "Filter by task type",
                        "enum": ["feature", "bug", "refactor", "documentation", "testing", "maintenance"]
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of tasks to return",
                        "minimum": 1,
                        "maximum": 100,
                        "default": 10
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Number of tasks to skip",
                        "minimum": 0,
                        "default": 0
                    }
                }
            },
            handler=get_tasks_handler,
            examples=[
                {"status": "in_progress", "limit": 5},
                {"priority": "high", "task_type": "bug"},
                {"limit": 20, "offset": 10}
            ]
        ),
        MCPTool(
            name="get_task",
            description="Get detailed information about a specific task",
            category=MCPToolCategory.TASK_MANAGEMENT,
            input_schema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "integer",
                        "description": "ID of the task to retrieve"
                    }
                },
                "required": ["task_id"]
            },
            handler=get_task_handler,
            examples=[
                {"task_id": 1},
                {"task_id": 42}
            ]
        ),
        MCPTool(
            name="create_task",
            description="Create a new task with comprehensive details",
            category=MCPToolCategory.TASK_MANAGEMENT,
            input_schema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Task title",
                        "minLength": 1,
                        "maxLength": 200
                    },
                    "description": {
                        "type": "string",
                        "description": "Detailed task description"
                    },
                    "task_type": {
                        "type": "string",
                        "description": "Type of task",
                        "enum": ["feature", "bug", "refactor", "documentation", "testing", "maintenance"]
                    },
                    "priority": {
                        "type": "string",
                        "description": "Task priority",
                        "enum": ["low", "medium", "high", "critical"],
                        "default": "medium"
                    },
                    "estimated_hours": {
                        "type": "number",
                        "description": "Estimated hours to complete",
                        "minimum": 0.1
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Task tags for categorization"
                    },
                    "assigned_to": {
                        "type": "string",
                        "description": "Email of assigned developer"
                    }
                },
                "required": ["title", "task_type"]
            },
            handler=create_task_handler,
            examples=[
                {
                    "title": "Implement user authentication",
                    "task_type": "feature",
                    "priority": "high",
                    "estimated_hours": 8.0
                },
                {
                    "title": "Fix login bug",
                    "description": "Users cannot log in with special characters in password",
                    "task_type": "bug",
                    "priority": "critical"
                }
            ]
        ),
        MCPTool(
            name="update_task_status",
            description="Update the status of a task",
            category=MCPToolCategory.TASK_MANAGEMENT,
            input_schema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "integer",
                        "description": "ID of the task to update"
                    },
                    "status": {
                        "type": "string",
                        "description": "New task status",
                        "enum": ["pending", "in_progress", "done", "deferred", "cancelled"]
                    },
                    "notes": {
                        "type": "string",
                        "description": "Optional notes about the status change"
                    }
                },
                "required": ["task_id", "status"]
            },
            handler=update_task_status_handler,
            examples=[
                {"task_id": 1, "status": "in_progress"},
                {"task_id": 2, "status": "done", "notes": "Completed successfully"}
            ]
        ),
        MCPTool(
            name="update_task_progress",
            description="Update the progress percentage of a task",
            category=MCPToolCategory.TASK_MANAGEMENT,
            input_schema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "integer",
                        "description": "ID of the task to update"
                    },
                    "progress": {
                        "type": "number",
                        "description": "Progress percentage (0-100)",
                        "minimum": 0,
                        "maximum": 100
                    },
                    "notes": {
                        "type": "string",
                        "description": "Optional notes about the progress update"
                    }
                },
                "required": ["task_id", "progress"]
            },
            handler=update_task_progress_handler,
            examples=[
                {"task_id": 1, "progress": 50.0},
                {"task_id": 2, "progress": 100.0, "notes": "Task completed"}
            ]
        )
    ]


def create_dependency_tools() -> List[MCPTool]:
    """Create dependency management MCP tools."""

    async def add_task_dependency_handler(args: Dict[str, Any]) -> Dict[str, Any]:
        """Handler for add_task_dependency tool."""
        from ..services.taskmaster_service import TaskMasterService
        from ..core.cache import get_cache_service

        cache_service = await get_cache_service()
        taskmaster = TaskMasterService(cache_service)

        task_id = str(args["task_id"])
        depends_on_id = str(args["depends_on_id"])
        dependency_type = args.get("dependency_type", "blocks")

        try:
            success = await taskmaster.add_task_dependency(task_id, depends_on_id, dependency_type)
            if not success:
                return {"error": f"Failed to add dependency between tasks {task_id} and {depends_on_id}"}

            return {
                "message": f"Added dependency: Task {task_id} {dependency_type} Task {depends_on_id}",
                "task_id": task_id,
                "depends_on_id": depends_on_id,
                "dependency_type": dependency_type
            }
        except Exception as e:
            return {"error": f"Failed to add dependency: {str(e)}"}

    return [
        MCPTool(
            name="add_task_dependency",
            description="Add a dependency relationship between tasks",
            category=MCPToolCategory.DEPENDENCIES,
            input_schema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "integer",
                        "description": "ID of the task that depends on another"
                    },
                    "depends_on_id": {
                        "type": "integer",
                        "description": "ID of the task that is depended upon"
                    },
                    "dependency_type": {
                        "type": "string",
                        "description": "Type of dependency relationship",
                        "enum": ["blocks", "requires", "related"],
                        "default": "blocks"
                    }
                },
                "required": ["task_id", "depends_on_id"]
            },
            handler=add_task_dependency_handler,
            examples=[
                {"task_id": 2, "depends_on_id": 1, "dependency_type": "blocks"},
                {"task_id": 3, "depends_on_id": 1, "dependency_type": "requires"}
            ]
        )
    ]


def create_analysis_tools() -> List[MCPTool]:
    """Create analysis MCP tools."""

    async def analyze_task_complexity_handler(args: Dict[str, Any]) -> Dict[str, Any]:
        """Handler for analyze_task_complexity tool."""
        from ..services.taskmaster_service import TaskMasterService
        from ..core.cache import get_cache_service

        cache_service = await get_cache_service()
        taskmaster = TaskMasterService(cache_service)

        task_id = str(args["task_id"])
        recalculate = args.get("recalculate", False)

        try:
            analysis = await taskmaster.analyze_task_complexity(task_id, recalculate)
            if not analysis:
                return {"error": f"Failed to analyze complexity for task {task_id}"}

            return {
                "task_id": task_id,
                "complexity_analysis": analysis
            }
        except Exception as e:
            return {"error": f"Failed to analyze complexity: {str(e)}"}

    return [
        MCPTool(
            name="analyze_task_complexity",
            description="Analyze the complexity of a task and get recommendations",
            category=MCPToolCategory.ANALYSIS,
            input_schema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "integer",
                        "description": "ID of the task to analyze"
                    },
                    "recalculate": {
                        "type": "boolean",
                        "description": "Force recalculation even if cached",
                        "default": False
                    }
                },
                "required": ["task_id"]
            },
            handler=analyze_task_complexity_handler,
            examples=[
                {"task_id": 1},
                {"task_id": 2, "recalculate": True}
            ]
        )
    ]


def create_analytics_tools() -> List[MCPTool]:
    """Create analytics MCP tools."""

    async def get_task_statistics_handler(args: Dict[str, Any]) -> Dict[str, Any]:
        """Handler for get_task_statistics tool."""
        from ..services.taskmaster_service import TaskMasterService
        from ..core.cache import get_cache_service

        cache_service = await get_cache_service()
        taskmaster = TaskMasterService(cache_service)

        date_range = args.get("date_range", "all_time")
        group_by = args.get("group_by", "status")

        # Convert to TaskFilter if needed
        task_filter = None
        if date_range != "all_time":
            # In production, you'd implement date range filtering in TaskFilter
            pass

        stats = await taskmaster.get_task_statistics(filters=task_filter)

        return {
            "statistics": stats,
            "date_range": date_range,
            "grouped_by": group_by,
            "generated_at": datetime.utcnow().isoformat()
        }

    return [
        MCPTool(
            name="get_task_statistics",
            description="Get comprehensive task statistics and analytics",
            category=MCPToolCategory.ANALYTICS,
            input_schema={
                "type": "object",
                "properties": {
                    "date_range": {
                        "type": "string",
                        "description": "Date range filter",
                        "enum": ["last_7_days", "last_30_days", "last_90_days", "all_time"],
                        "default": "all_time"
                    },
                    "group_by": {
                        "type": "string",
                        "description": "Group statistics by field",
                        "enum": ["status", "priority", "type", "assigned_to"],
                        "default": "status"
                    }
                }
            },
            handler=get_task_statistics_handler,
            examples=[
                {"date_range": "last_30_days", "group_by": "priority"},
                {"date_range": "all_time", "group_by": "status"}
            ]
        )
    ]


def create_search_tools() -> List[MCPTool]:
    """Create search MCP tools."""

    async def search_tasks_handler(args: Dict[str, Any]) -> Dict[str, Any]:
        """Handler for search_tasks tool."""
        from ..services.taskmaster_service import TaskMasterService
        from ..core.cache import get_cache_service

        cache_service = await get_cache_service()
        taskmaster = TaskMasterService(cache_service)

        query = args.get("query", "")
        filters = args.get("filters", {})
        limit = args.get("limit", 10)

        # Clean up filters
        filters = {k: v for k, v in filters.items() if v is not None}

        # Convert to TaskFilter if filters exist
        task_filter = None
        if filters:
            from ..models.task_models import TaskFilter
            task_filter = TaskFilter(**filters)

        tasks = await taskmaster.search_tasks(query, filters=task_filter, limit=limit)

        return {
            "query": query,
            "filters": filters,
            "results": tasks,
            "count": len(tasks)
        }

    return [
        MCPTool(
            name="search_tasks",
            description="Search tasks using text query and filters",
            category=MCPToolCategory.SEARCH,
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Text search query (searches title and description)"
                    },
                    "filters": {
                        "type": "object",
                        "description": "Additional filters",
                        "properties": {
                            "status": {"type": "string"},
                            "priority": {"type": "string"},
                            "task_type": {"type": "string"},
                            "assigned_to": {"type": "string"}
                        }
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum results to return",
                        "minimum": 1,
                        "maximum": 50,
                        "default": 10
                    }
                }
            },
            handler=search_tasks_handler,
            examples=[
                {"query": "authentication", "limit": 5},
                {"query": "bug", "filters": {"priority": "high"}},
                {"filters": {"status": "in_progress", "assigned_to": "dev@devq.ai"}}
            ]
        )
    ]


def create_monitoring_tools() -> List[MCPTool]:
    """Create monitoring MCP tools."""

    async def get_service_health_handler(args: Dict[str, Any]) -> Dict[str, Any]:
        """Handler for get_service_health tool."""
        include_details = args.get("include_details", True)

        # Import here to avoid circular imports
        from ..core.initialization import get_application_health

        health_data = await get_application_health()

        if not include_details:
            # Return simplified health info
            return {
                "overall_status": health_data["overall_status"],
                "healthy_services": health_data["summary"]["healthy_services"],
                "unhealthy_services": health_data["summary"]["unhealthy_services"],
                "timestamp": health_data["timestamp"]
            }

        return health_data

    return [
        MCPTool(
            name="get_service_health",
            description="Get comprehensive health status of all services",
            category=MCPToolCategory.MONITORING,
            input_schema={
                "type": "object",
                "properties": {
                    "include_details": {
                        "type": "boolean",
                        "description": "Include detailed service information",
                        "default": True
                    }
                }
            },
            handler=get_service_health_handler,
            examples=[
                {"include_details": True},
                {"include_details": False}
            ]
        )
    ]


def get_all_mcp_tools() -> List[MCPTool]:
    """Get all available MCP tools."""
    tools = []
    tools.extend(create_task_management_tools())
    tools.extend(create_dependency_tools())
    tools.extend(create_analysis_tools())
    tools.extend(create_analytics_tools())
    tools.extend(create_search_tools())
    tools.extend(create_monitoring_tools())
    return tools


def get_mcp_tools() -> Dict[str, MCPTool]:
    """Get all MCP tools as a name-indexed dictionary."""
    tools = get_all_mcp_tools()
    return {tool.name: tool for tool in tools}


def get_tools_by_category(category: MCPToolCategory) -> List[MCPTool]:
    """Get MCP tools filtered by category."""
    tools = get_all_mcp_tools()
    return [tool for tool in tools if tool.category == category]


def get_tool_schemas() -> Dict[str, Dict[str, Any]]:
    """Get input schemas for all MCP tools."""
    tools = get_all_mcp_tools()
    return {tool.name: tool.input_schema for tool in tools}


def validate_tool_arguments(tool_name: str, arguments: Dict[str, Any]) -> bool:
    """
    Validate tool arguments against the tool's schema.

    Args:
        tool_name: Name of the tool
        arguments: Arguments to validate

    Returns:
        True if valid, False otherwise
    """
    tools = get_mcp_tools()

    if tool_name not in tools:
        return False

    tool = tools[tool_name]
    schema = tool.input_schema

    # Basic validation - could be extended with jsonschema
    required_fields = schema.get("required", [])
    properties = schema.get("properties", {})

    # Check required fields
    for field in required_fields:
        if field not in arguments:
            return False

    # Check field types (basic validation)
    for field, value in arguments.items():
        if field in properties:
            expected_type = properties[field].get("type")
            if expected_type == "string" and not isinstance(value, str):
                return False
            elif expected_type == "integer" and not isinstance(value, int):
                return False
            elif expected_type == "number" and not isinstance(value, (int, float)):
                return False
            elif expected_type == "boolean" and not isinstance(value, bool):
                return False
            elif expected_type == "array" and not isinstance(value, list):
                return False
            elif expected_type == "object" and not isinstance(value, dict):
                return False

    return True


def get_tool_examples(tool_name: str) -> List[Dict[str, Any]]:
    """Get usage examples for a specific tool."""
    tools = get_mcp_tools()

    if tool_name not in tools:
        return []

    return tools[tool_name].examples


def get_tools_summary() -> Dict[str, Any]:
    """Get a summary of all available MCP tools."""
    tools = get_all_mcp_tools()

    categories = {}
    for tool in tools:
        category = tool.category.value
        if category not in categories:
            categories[category] = []
        categories[category].append({
            "name": tool.name,
            "description": tool.description,
            "example_count": len(tool.examples)
        })

    return {
        "total_tools": len(tools),
        "categories": categories,
        "tool_names": [tool.name for tool in tools]
    }
