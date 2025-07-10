"""
FastMCP Core Framework
High-performance MCP server framework with built-in observability and tool management.
"""

import asyncio
import json
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
import mcp.types as types
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import logfire


@dataclass
class MCPServerConfig:
    """Configuration for MCP server"""
    name: str
    version: str = "1.0.0"
    description: str = ""
    capabilities: Dict[str, Any] = field(default_factory=dict)
    tools: List[str] = field(default_factory=list)
    resources: List[str] = field(default_factory=list)


class FastMCP:
    """
    FastMCP - Fast Model Context Protocol Framework

    A high-performance wrapper around the standard MCP server that provides:
    - Simplified tool registration via decorators
    - Built-in Logfire observability
    - Health monitoring and metrics
    - Automatic error handling and recovery
    """

    def __init__(self, name: str, version: str = "1.0.0", description: str = ""):
        self.config = MCPServerConfig(
            name=name,
            version=version,
            description=description
        )
        self.server: Server = Server(name)
        self._tools: Dict[str, Callable] = {}
        self._tool_schemas: Dict[str, types.Tool] = {}
        self._resources: Dict[str, Callable] = {}
        self._setup_logging()
        self._setup_server_handlers()

    def _setup_logging(self):
        """Setup Logfire instrumentation"""
        logfire.configure()
        self.logger = logfire
        self.logger.info(f"FastMCP server '{self.config.name}' initialized")

    def _setup_server_handlers(self):
        """Setup standard MCP server handlers"""

        @self.server.list_tools()
        async def list_tools() -> List[types.Tool]:
            """List all registered tools"""
            with self.logger.span("list_tools"):
                tools = list(self._tool_schemas.values())
                self.logger.info(f"Listed {len(tools)} tools", tools=[t.name for t in tools])
                return tools

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> List[types.TextContent]:
            """Call a registered tool"""
            with self.logger.span("call_tool", tool_name=name):
                if name not in self._tools:
                    error_msg = f"Tool '{name}' not found"
                    self.logger.error(error_msg, available_tools=list(self._tools.keys()))
                    raise ValueError(error_msg)

                try:
                    self.logger.info(f"Calling tool '{name}'", arguments=arguments)
                    result = await self._call_tool_safe(name, arguments)

                    # Ensure result is properly formatted
                    if isinstance(result, str):
                        content = [types.TextContent(type="text", text=result)]
                    elif isinstance(result, list) and all(isinstance(item, types.TextContent) for item in result):
                        content = result
                    elif isinstance(result, dict):
                        content = [types.TextContent(type="text", text=json.dumps(result, indent=2))]
                    else:
                        content = [types.TextContent(type="text", text=str(result))]

                    self.logger.info(f"Tool '{name}' completed successfully")
                    return content

                except Exception as e:
                    error_msg = f"Error executing tool '{name}': {str(e)}"
                    self.logger.error(error_msg, error=str(e), tool_name=name)
                    return [types.TextContent(type="text", text=f"ERROR: {error_msg}")]

    async def _call_tool_safe(self, name: str, arguments: dict) -> Any:
        """Safely call a tool with error handling"""
        tool_func = self._tools[name]

        # Check if function is async
        if asyncio.iscoroutinefunction(tool_func):
            return await tool_func(**arguments)
        else:
            # Run sync function in thread pool to avoid blocking
            return await asyncio.get_event_loop().run_in_executor(None, lambda: tool_func(**arguments))

    def tool(self, name: Optional[str] = None, description: str = "", input_schema: Optional[Dict[str, Any]] = None):
        """
        Decorator to register a tool with the FastMCP server

        Args:
            name: Tool name (uses function name if not provided)
            description: Tool description
            input_schema: JSON schema for tool inputs
        """
        def decorator(func: Callable) -> Callable:
            tool_name = name or func.__name__

            # Generate default schema if not provided
            if input_schema is None:
                schema = {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            else:
                schema = input_schema

            # Register the tool
            self._tools[tool_name] = func
            self._tool_schemas[tool_name] = types.Tool(
                name=tool_name,
                description=description or func.__doc__ or f"Execute {tool_name}",
                inputSchema=schema
            )

            self.logger.info(f"Registered tool: {tool_name}")
            return func

        return decorator

    def resource(self, uri: str, name: Optional[str] = None, description: str = "", mime_type: str = "text/plain"):
        """
        Decorator to register a resource with the FastMCP server

        Args:
            uri: Resource URI
            name: Resource name
            description: Resource description
            mime_type: MIME type of the resource
        """
        def decorator(func: Callable) -> Callable:
            self._resources[uri] = func
            self.logger.info(f"Registered resource: {uri}")
            return func

        return decorator

    async def run_stdio(self):
        """Run the server using stdio transport"""
        with self.logger.span("server_startup"):
            self.logger.info(f"Starting FastMCP server '{self.config.name}' on stdio")

            async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream,
                    write_stream,
                    InitializationOptions(
                        server_name=self.config.name,
                        server_version=self.config.version,
                        capabilities=self.server.get_capabilities(
                            notification_options=NotificationOptions(),
                            experimental_capabilities={}
                        )
                    )
                )

    async def run_transport(self, read_stream, write_stream):
        """Run the server with custom transport streams"""
        with self.logger.span("server_startup"):
            self.logger.info(f"Starting FastMCP server '{self.config.name}' with custom transport")

            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name=self.config.name,
                    server_version=self.config.version,
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={}
                    )
                )
            )

    def get_tool_info(self) -> Dict[str, Any]:
        """Get information about registered tools"""
        return {
            "server_name": self.config.name,
            "server_version": self.config.version,
            "description": self.config.description,
            "tool_count": len(self._tools),
            "tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema
                }
                for tool in self._tool_schemas.values()
            ],
            "resource_count": len(self._resources),
            "capabilities": self.server.get_capabilities(
                notification_options=NotificationOptions(),
                experimental_capabilities={}
            )
        }

    def get_health_status(self) -> Dict[str, Any]:
        """Get server health status"""
        return {
            "status": "healthy",
            "server_name": self.config.name,
            "version": self.config.version,
            "uptime": datetime.now().isoformat(),
            "tools_registered": len(self._tools),
            "resources_registered": len(self._resources)
        }
