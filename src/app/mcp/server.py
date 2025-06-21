"""
MCP Server Implementation for Machina Registry Service

This module provides the MCP (Model Context Protocol) server implementation
that exposes TaskMaster AI functionality and registry services as MCP tools
for integration with AI development environments like Zed IDE.

Features:
- MCP protocol compliance with tool definitions
- Integration with existing TaskMaster service
- Async tool execution with proper error handling
- Service registry and health monitoring tools
- Real-time task management capabilities
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Sequence
from datetime import datetime

import logfire
from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from ..services.taskmaster_service import TaskMasterService
from ..core.cache import get_cache_service
from ..core.config import settings


class MCPServer:
    """
    MCP Server for Machina Registry Service.

    Provides MCP protocol implementation that exposes TaskMaster AI
    functionality and registry services as standardized MCP tools.
    """

    def __init__(self):
        """Initialize the MCP server with tool definitions."""
        self.server = Server("machina-registry")
        self.logger = logging.getLogger(__name__)
        self._taskmaster_service: Optional[TaskMasterService] = None
        self._setup_tools()

    async def get_taskmaster_service(self) -> TaskMasterService:
        """Get or create TaskMaster service instance."""
        if self._taskmaster_service is None:
            cache_service = await get_cache_service()
            self._taskmaster_service = TaskMasterService(cache_service)
        return self._taskmaster_service

    def _setup_tools(self):
        """Set up all MCP tools and their handlers."""

        # Task Management Tools
        @self.server.list_tools()
        async def list_tools() -> List[types.Tool]:
            """List all available MCP tools."""
            return [
                types.Tool(
                    name="get_tasks",
                    description="Get all tasks with optional filtering and pagination",
                    inputSchema={
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
                    }
                ),
                types.Tool(
                    name="get_task",
                    description="Get detailed information about a specific task",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "task_id": {
                                "type": "integer",
                                "description": "ID of the task to retrieve"
                            }
                        },
                        "required": ["task_id"]
                    }
                ),
                types.Tool(
                    name="create_task",
                    description="Create a new task with comprehensive details",
                    inputSchema={
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
                    }
                ),
                types.Tool(
                    name="update_task_status",
                    description="Update the status of a task",
                    inputSchema={
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
                    }
                ),
                types.Tool(
                    name="update_task_progress",
                    description="Update the progress percentage of a task",
                    inputSchema={
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
                    }
                ),
                types.Tool(
                    name="add_task_dependency",
                    description="Add a dependency relationship between tasks",
                    inputSchema={
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
                    }
                ),
                types.Tool(
                    name="analyze_task_complexity",
                    description="Analyze the complexity of a task and get recommendations",
                    inputSchema={
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
                    }
                ),
                types.Tool(
                    name="get_task_statistics",
                    description="Get comprehensive task statistics and analytics",
                    inputSchema={
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
                    }
                ),
                types.Tool(
                    name="search_tasks",
                    description="Search tasks using text query and filters",
                    inputSchema={
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
                    }
                ),
                types.Tool(
                    name="get_service_health",
                    description="Get comprehensive health status of all services",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "include_details": {
                                "type": "boolean",
                                "description": "Include detailed service information",
                                "default": True
                            }
                        }
                    }
                )
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
            """Handle MCP tool calls."""
            try:
                with logfire.span(f"MCP Tool: {name}", tool_arguments=arguments):
                    result = await self._execute_tool(name, arguments)

                    # Format result as JSON string for MCP response
                    content = json.dumps(result, indent=2, default=str)

                    logfire.info(f"MCP tool {name} executed successfully")
                    return [types.TextContent(type="text", text=content)]

            except Exception as e:
                error_msg = f"Error executing tool {name}: {str(e)}"
                logfire.error(error_msg, tool_name=name, arguments=arguments, error=str(e))

                error_response = {
                    "error": True,
                    "message": error_msg,
                    "tool": name,
                    "timestamp": datetime.utcnow().isoformat()
                }

                return [types.TextContent(type="text", text=json.dumps(error_response, indent=2))]

    async def _execute_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the specified MCP tool with given arguments."""
        taskmaster = await self.get_taskmaster_service()

        if name == "get_tasks":
            filters = {k: v for k, v in arguments.items() if k not in ["limit", "offset"] and v is not None}
            limit = arguments.get("limit", 10)
            offset = arguments.get("offset", 0)

            # Convert to TaskFilter if filters exist, otherwise None
            task_filter = None
            if filters:
                # Create a simple filter object - in production you'd use proper TaskFilter
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

        elif name == "get_task":
            task_id = arguments["task_id"]
            task = await taskmaster.get_task(task_id)

            if not task:
                return {"error": f"Task {task_id} not found"}

            return {"task": task}

        elif name == "create_task":
            task_data = arguments.copy()
            task = await taskmaster.create_task(task_data)

            return {
                "message": "Task created successfully",
                "task": task
            }

        elif name == "update_task_status":
            task_id = arguments["task_id"]
            status = arguments["status"]
            notes = arguments.get("notes")

            success = await taskmaster.update_task_status(task_id, status, notes)

            if not success:
                return {"error": f"Failed to update task {task_id} status"}

            return {
                "message": f"Task {task_id} status updated to {status}",
                "task_id": task_id,
                "new_status": status,
                "notes": notes
            }

        elif name == "update_task_progress":
            task_id = arguments["task_id"]
            progress = arguments["progress"]
            notes = arguments.get("notes")

            success = await taskmaster.update_task_progress(task_id, progress, notes)

            if not success:
                return {"error": f"Failed to update task {task_id} progress"}

            return {
                "message": f"Task {task_id} progress updated to {progress}%",
                "task_id": task_id,
                "progress": progress,
                "notes": notes
            }

        elif name == "add_task_dependency":
            task_id = arguments["task_id"]
            depends_on_id = arguments["depends_on_id"]
            dependency_type = arguments.get("dependency_type", "blocks")

            success = await taskmaster.add_task_dependency(task_id, depends_on_id, dependency_type)

            if not success:
                return {"error": f"Failed to add dependency between tasks {task_id} and {depends_on_id}"}

            return {
                "message": f"Added dependency: Task {task_id} {dependency_type} Task {depends_on_id}",
                "task_id": task_id,
                "depends_on_id": depends_on_id,
                "dependency_type": dependency_type
            }

        elif name == "analyze_task_complexity":
            task_id = arguments["task_id"]
            recalculate = arguments.get("recalculate", False)

            analysis = await taskmaster.analyze_task_complexity(task_id, recalculate)

            if not analysis:
                return {"error": f"Failed to analyze complexity for task {task_id}"}

            return {
                "task_id": task_id,
                "complexity_analysis": analysis
            }

        elif name == "get_task_statistics":
            date_range = arguments.get("date_range", "all_time")
            group_by = arguments.get("group_by", "status")

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

        elif name == "search_tasks":
            query = arguments.get("query", "")
            filters = arguments.get("filters", {})
            limit = arguments.get("limit", 10)

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

        elif name == "get_service_health":
            include_details = arguments.get("include_details", True)

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

        else:
            return {"error": f"Unknown tool: {name}"}

    async def run_stdio(self):
        """Run the MCP server using stdio transport."""
        logfire.info("Starting MCP server with stdio transport")

        try:
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream,
                    write_stream,
                    self.server.create_initialization_options()
                )
        except Exception as e:
            logfire.error(f"MCP server error: {e}")
            raise

    async def run_sse(self, host: str = "localhost", port: int = 8001):
        """Run the MCP server using SSE transport (for future web integration)."""
        logfire.info(f"MCP SSE server not yet implemented")
        # This would be implemented for web-based MCP clients
        raise NotImplementedError("SSE transport not yet implemented")


# Factory function for creating MCP server instance
def create_mcp_server() -> MCPServer:
    """Create and return a configured MCP server instance."""
    return MCPServer()


# CLI entry point for standalone MCP server
async def main():
    """Main entry point for running the MCP server standalone."""
    logging.basicConfig(level=logging.INFO)

    server = create_mcp_server()

    try:
        await server.run_stdio()
    except KeyboardInterrupt:
        logfire.info("MCP server shutdown requested")
    except Exception as e:
        logfire.error(f"MCP server failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
