"""
MCP Handlers for FastAPI Integration

This module provides MCP (Model Context Protocol) handlers that integrate
with the FastAPI application, allowing dual protocol support - both HTTP REST
and MCP protocol access to the same underlying services.

Features:
- FastAPI integration with MCP protocol support
- Middleware for MCP request handling
- Route handlers for MCP endpoints
- Integration with existing TaskMaster services
- Error handling and logging for MCP operations
"""

import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

import logfire
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from ..services.taskmaster_service import TaskMasterService
from ..core.cache import get_cache_service
from ..core.config import settings
from .server import MCPServer


class MCPHandlers:
    """
    MCP handlers for FastAPI integration.

    Provides endpoints and middleware to handle MCP protocol requests
    alongside standard HTTP REST API requests.
    """

    def __init__(self, app: FastAPI):
        """Initialize MCP handlers with FastAPI app."""
        self.app = app
        self.logger = logging.getLogger(__name__)
        self._mcp_server: Optional[MCPServer] = None
        self._taskmaster_service: Optional[TaskMasterService] = None

    async def get_mcp_server(self) -> MCPServer:
        """Get or create MCP server instance."""
        if self._mcp_server is None:
            from .server import create_mcp_server
            self._mcp_server = create_mcp_server()
        return self._mcp_server

    async def get_taskmaster_service(self) -> TaskMasterService:
        """Get or create TaskMaster service instance."""
        if self._taskmaster_service is None:
            cache_service = await get_cache_service()
            self._taskmaster_service = TaskMasterService(cache_service)
        return self._taskmaster_service

    def register_routes(self):
        """Register MCP-specific routes with the FastAPI app."""

        @self.app.get("/mcp/tools", tags=["MCP"])
        async def list_mcp_tools():
            """List all available MCP tools."""
            try:
                mcp_server = await self.get_mcp_server()

                # Get tools from MCP server
                tools = await mcp_server._setup_tools()

                tools_info = [
                    {
                        "name": "get_tasks",
                        "description": "Get all tasks with optional filtering and pagination",
                        "category": "task_management"
                    },
                    {
                        "name": "get_task",
                        "description": "Get detailed information about a specific task",
                        "category": "task_management"
                    },
                    {
                        "name": "create_task",
                        "description": "Create a new task with comprehensive details",
                        "category": "task_management"
                    },
                    {
                        "name": "update_task_status",
                        "description": "Update the status of a task",
                        "category": "task_management"
                    },
                    {
                        "name": "update_task_progress",
                        "description": "Update the progress percentage of a task",
                        "category": "task_management"
                    },
                    {
                        "name": "add_task_dependency",
                        "description": "Add a dependency relationship between tasks",
                        "category": "task_management"
                    },
                    {
                        "name": "analyze_task_complexity",
                        "description": "Analyze the complexity of a task and get recommendations",
                        "category": "analysis"
                    },
                    {
                        "name": "get_task_statistics",
                        "description": "Get comprehensive task statistics and analytics",
                        "category": "analytics"
                    },
                    {
                        "name": "search_tasks",
                        "description": "Search tasks using text query and filters",
                        "category": "search"
                    },
                    {
                        "name": "get_service_health",
                        "description": "Get comprehensive health status of all services",
                        "category": "monitoring"
                    }
                ]

                return {
                    "mcp_enabled": settings.MCP_TOOLS_ENABLED,
                    "tools_count": len(tools_info),
                    "tools": tools_info,
                    "categories": ["task_management", "analysis", "analytics", "search", "monitoring"]
                }

            except Exception as e:
                logfire.error("Failed to list MCP tools", error=str(e))
                return JSONResponse(
                    status_code=500,
                    content={"error": "Failed to retrieve MCP tools", "details": str(e)}
                )

        @self.app.post("/mcp/execute", tags=["MCP"])
        async def execute_mcp_tool(request: Request):
            """Execute an MCP tool via HTTP endpoint."""
            try:
                body = await request.json()
                tool_name = body.get("tool")
                arguments = body.get("arguments", {})

                if not tool_name:
                    raise HTTPException(status_code=400, detail="Tool name is required")

                with logfire.span(f"MCP HTTP Tool: {tool_name}", tool_arguments=arguments):
                    mcp_server = await self.get_mcp_server()
                    result = await mcp_server._execute_tool(tool_name, arguments)

                    logfire.info(f"MCP HTTP tool {tool_name} executed successfully")

                    return {
                        "success": True,
                        "tool": tool_name,
                        "result": result,
                        "executed_at": datetime.utcnow().isoformat()
                    }

            except HTTPException:
                raise
            except Exception as e:
                logfire.error(f"MCP HTTP tool execution failed", tool=tool_name, error=str(e))
                return JSONResponse(
                    status_code=500,
                    content={
                        "success": False,
                        "error": str(e),
                        "tool": tool_name,
                        "executed_at": datetime.utcnow().isoformat()
                    }
                )

        @self.app.get("/mcp/health", tags=["MCP"])
        async def mcp_health_check():
            """Health check specifically for MCP functionality."""
            try:
                # Test TaskMaster service connection
                taskmaster = await self.get_taskmaster_service()

                # Test basic functionality
                test_stats = await taskmaster.get_task_statistics({})

                return {
                    "mcp_status": "healthy",
                    "services": {
                        "taskmaster": "connected",
                        "cache": "operational",
                        "mcp_server": "ready"
                    },
                    "capabilities": {
                        "task_management": True,
                        "complexity_analysis": True,
                        "statistics": True,
                        "search": True,
                        "health_monitoring": True
                    },
                    "test_results": {
                        "statistics_query": "passed",
                        "service_connection": "passed"
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }

            except Exception as e:
                logfire.error("MCP health check failed", error=str(e))
                return JSONResponse(
                    status_code=503,
                    content={
                        "mcp_status": "unhealthy",
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )

        @self.app.get("/mcp/schema", tags=["MCP"])
        async def get_mcp_schema():
            """Get MCP tool schemas for client integration."""
            return {
                "protocol_version": "2024-11-05",
                "server_info": {
                    "name": "machina-registry",
                    "version": settings.VERSION,
                    "description": "DevQ.ai MCP Registry & Management Platform"
                },
                "tools": {
                    "get_tasks": {
                        "description": "Get all tasks with optional filtering and pagination",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "status": {"type": "string", "enum": ["pending", "in_progress", "done", "deferred", "cancelled"]},
                                "priority": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                                "task_type": {"type": "string", "enum": ["feature", "bug", "refactor", "documentation", "testing", "maintenance"]},
                                "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 10},
                                "offset": {"type": "integer", "minimum": 0, "default": 0}
                            }
                        }
                    },
                    "get_task": {
                        "description": "Get detailed information about a specific task",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "task_id": {"type": "integer", "description": "ID of the task to retrieve"}
                            },
                            "required": ["task_id"]
                        }
                    },
                    "create_task": {
                        "description": "Create a new task with comprehensive details",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string", "minLength": 1, "maxLength": 200},
                                "description": {"type": "string"},
                                "task_type": {"type": "string", "enum": ["feature", "bug", "refactor", "documentation", "testing", "maintenance"]},
                                "priority": {"type": "string", "enum": ["low", "medium", "high", "critical"], "default": "medium"},
                                "estimated_hours": {"type": "number", "minimum": 0.1},
                                "tags": {"type": "array", "items": {"type": "string"}},
                                "assigned_to": {"type": "string"}
                            },
                            "required": ["title", "task_type"]
                        }
                    },
                    "update_task_status": {
                        "description": "Update the status of a task",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "task_id": {"type": "integer"},
                                "status": {"type": "string", "enum": ["pending", "in_progress", "done", "deferred", "cancelled"]},
                                "notes": {"type": "string"}
                            },
                            "required": ["task_id", "status"]
                        }
                    },
                    "update_task_progress": {
                        "description": "Update the progress percentage of a task",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "task_id": {"type": "integer"},
                                "progress": {"type": "number", "minimum": 0, "maximum": 100},
                                "notes": {"type": "string"}
                            },
                            "required": ["task_id", "progress"]
                        }
                    },
                    "add_task_dependency": {
                        "description": "Add a dependency relationship between tasks",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "task_id": {"type": "integer"},
                                "depends_on_id": {"type": "integer"},
                                "dependency_type": {"type": "string", "enum": ["blocks", "requires", "related"], "default": "blocks"}
                            },
                            "required": ["task_id", "depends_on_id"]
                        }
                    },
                    "analyze_task_complexity": {
                        "description": "Analyze the complexity of a task and get recommendations",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "task_id": {"type": "integer"},
                                "recalculate": {"type": "boolean", "default": False}
                            },
                            "required": ["task_id"]
                        }
                    },
                    "get_task_statistics": {
                        "description": "Get comprehensive task statistics and analytics",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "date_range": {"type": "string", "enum": ["last_7_days", "last_30_days", "last_90_days", "all_time"], "default": "all_time"},
                                "group_by": {"type": "string", "enum": ["status", "priority", "type", "assigned_to"], "default": "status"}
                            }
                        }
                    },
                    "search_tasks": {
                        "description": "Search tasks using text query and filters",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string"},
                                "filters": {
                                    "type": "object",
                                    "properties": {
                                        "status": {"type": "string"},
                                        "priority": {"type": "string"},
                                        "task_type": {"type": "string"},
                                        "assigned_to": {"type": "string"}
                                    }
                                },
                                "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10}
                            }
                        }
                    },
                    "get_service_health": {
                        "description": "Get comprehensive health status of all services",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "include_details": {"type": "boolean", "default": True}
                            }
                        }
                    }
                }
            }

    def add_mcp_middleware(self):
        """Add middleware for MCP request handling."""

        @self.app.middleware("http")
        async def mcp_middleware(request: Request, call_next):
            """Middleware to handle MCP-specific request processing."""

            # Check if this is an MCP-related request
            is_mcp_request = (
                request.url.path.startswith("/mcp/") or
                request.headers.get("x-mcp-request") == "true"
            )

            if is_mcp_request:
                with logfire.span("MCP Request", path=request.url.path, method=request.method):
                    # Add MCP-specific headers
                    response = await call_next(request)
                    response.headers["x-mcp-server"] = "machina-registry"
                    response.headers["x-mcp-version"] = settings.VERSION
                    return response

            return await call_next(request)


def register_mcp_handlers(app: FastAPI) -> MCPHandlers:
    """
    Register MCP handlers with the FastAPI application.

    Args:
        app: FastAPI application instance

    Returns:
        MCPHandlers instance for further configuration
    """
    handlers = MCPHandlers(app)

    # Register routes and middleware if MCP is enabled
    if settings.MCP_TOOLS_ENABLED:
        handlers.register_routes()
        handlers.add_mcp_middleware()

        logfire.info("MCP handlers registered successfully")
    else:
        logfire.info("MCP tools disabled, handlers not registered")

    return handlers


# Utility functions for MCP integration
async def get_mcp_capabilities() -> Dict[str, Any]:
    """Get MCP server capabilities."""
    return {
        "protocol_version": "2024-11-05",
        "tools": {
            "task_management": ["get_tasks", "get_task", "create_task", "update_task_status", "update_task_progress"],
            "dependencies": ["add_task_dependency"],
            "analysis": ["analyze_task_complexity"],
            "analytics": ["get_task_statistics"],
            "search": ["search_tasks"],
            "monitoring": ["get_service_health"]
        },
        "features": {
            "dual_protocol": True,
            "http_fallback": True,
            "real_time_updates": True,
            "caching": True,
            "observability": True
        },
        "transports": ["stdio", "http"]
    }


async def validate_mcp_tool_call(tool_name: str, arguments: Dict[str, Any]) -> bool:
    """Validate MCP tool call arguments."""
    # Basic validation - could be extended with JSON schema validation
    valid_tools = [
        "get_tasks", "get_task", "create_task", "update_task_status",
        "update_task_progress", "add_task_dependency", "analyze_task_complexity",
        "get_task_statistics", "search_tasks", "get_service_health"
    ]

    if tool_name not in valid_tools:
        return False

    # Tool-specific validation
    if tool_name in ["get_task", "update_task_status", "update_task_progress", "analyze_task_complexity"]:
        return "task_id" in arguments and isinstance(arguments["task_id"], int)

    if tool_name == "create_task":
        return "title" in arguments and "task_type" in arguments

    if tool_name == "add_task_dependency":
        return "task_id" in arguments and "depends_on_id" in arguments

    return True
