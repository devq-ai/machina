"""
FastMCP Registry Module
Provides registry functionality for managing MCP servers and tools.
"""

import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import logfire

from .core import FastMCP
from .health import HealthMonitor


@dataclass
class MCPServerInfo:
    """Information about a registered MCP server"""
    name: str
    endpoint: str
    tools: List[str]
    status: str = "unknown"
    last_health_check: Optional[datetime] = None
    registered_at: datetime = field(default_factory=datetime.now)
    version: str = "1.0.0"
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    health_check_failures: int = 0
    last_seen: Optional[datetime] = None


@dataclass
class ToolInfo:
    """Information about a tool provided by MCP servers"""
    name: str
    server_name: str
    description: str
    input_schema: Dict[str, Any]
    last_used: Optional[datetime] = None
    use_count: int = 0
    error_count: int = 0


class MCPRegistry:
    """
    MCP Server Registry

    Manages registration, discovery, and health monitoring of MCP servers.
    Provides a centralized registry for agentical workflows to discover and use MCP tools.
    """

    def __init__(self, registry_name: str = "mcp-registry", storage_path: Optional[str] = None):
        self.fastmcp = FastMCP(registry_name, version="1.0.0", description="MCP Server Registry")
        self.health_monitor = HealthMonitor(registry_name)

        # Registry data
        self.servers: Dict[str, MCPServerInfo] = {}
        self.tools: Dict[str, ToolInfo] = {}
        self.storage_path = Path(storage_path) if storage_path else Path("mcp_status.json")

        # Configuration
        self.health_check_interval = 30  # seconds
        self.server_timeout = 300  # seconds before marking server as stale
        self.max_health_failures = 3

        self.logger = logfire
        self._setup_registry_tools()
        self._load_registry_data()

    def _setup_registry_tools(self):
        """Setup registry management tools"""

        @self.fastmcp.tool(
            name="register_server",
            description="Register a new MCP server with the registry",
            input_schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Server name"},
                    "endpoint": {"type": "string", "description": "Server endpoint URL or address"},
                    "tools": {"type": "array", "items": {"type": "string"}, "description": "List of tool names"},
                    "version": {"type": "string", "description": "Server version", "default": "1.0.0"},
                    "description": {"type": "string", "description": "Server description", "default": ""}
                },
                "required": ["name", "endpoint", "tools"]
            }
        )
        async def register_server(name: str, endpoint: str, tools: List[str],
                                version: str = "1.0.0", description: str = "") -> Dict[str, Any]:
            """Register a new MCP server"""
            with self.logger.span("register_server", server_name=name):
                try:
                    server_info = MCPServerInfo(
                        name=name,
                        endpoint=endpoint,
                        tools=tools,
                        version=version,
                        description=description,
                        status="registered"
                    )

                    self.servers[name] = server_info

                    # Register tools
                    for tool_name in tools:
                        self.tools[f"{name}.{tool_name}"] = ToolInfo(
                            name=tool_name,
                            server_name=name,
                            description=f"Tool {tool_name} from {name}",
                            input_schema={"type": "object", "properties": {}}
                        )

                    await self._save_registry_data()

                    self.logger.info(f"Registered server: {name}", endpoint=endpoint, tools=tools)

                    return {
                        "status": "success",
                        "message": f"Server '{name}' registered successfully",
                        "server_name": name,
                        "tools_count": len(tools),
                        "registered_at": server_info.registered_at.isoformat()
                    }

                except Exception as e:
                    self.logger.error(f"Failed to register server: {name}", error=str(e))
                    return {
                        "status": "error",
                        "message": f"Failed to register server: {str(e)}"
                    }

        @self.fastmcp.tool(
            name="unregister_server",
            description="Unregister an MCP server from the registry",
            input_schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Server name to unregister"}
                },
                "required": ["name"]
            }
        )
        async def unregister_server(name: str) -> Dict[str, Any]:
            """Unregister an MCP server"""
            with self.logger.span("unregister_server", server_name=name):
                if name not in self.servers:
                    return {
                        "status": "error",
                        "message": f"Server '{name}' not found in registry"
                    }

                # Remove server and its tools
                del self.servers[name]

                # Remove tools associated with this server
                tools_to_remove = [tool_key for tool_key in self.tools.keys()
                                 if tool_key.startswith(f"{name}.")]
                for tool_key in tools_to_remove:
                    del self.tools[tool_key]

                await self._save_registry_data()

                self.logger.info(f"Unregistered server: {name}")

                return {
                    "status": "success",
                    "message": f"Server '{name}' unregistered successfully",
                    "tools_removed": len(tools_to_remove)
                }

        @self.fastmcp.tool(
            name="list_servers",
            description="List all registered MCP servers",
            input_schema={
                "type": "object",
                "properties": {
                    "status_filter": {"type": "string", "description": "Filter by status", "default": "all"}
                }
            }
        )
        async def list_servers(status_filter: str = "all") -> Dict[str, Any]:
            """List all registered servers"""
            with self.logger.span("list_servers"):
                servers_list = []

                for server_info in self.servers.values():
                    if status_filter != "all" and server_info.status != status_filter:
                        continue

                    servers_list.append({
                        "name": server_info.name,
                        "endpoint": server_info.endpoint,
                        "status": server_info.status,
                        "tools_count": len(server_info.tools),
                        "tools": server_info.tools,
                        "version": server_info.version,
                        "description": server_info.description,
                        "registered_at": server_info.registered_at.isoformat(),
                        "last_health_check": server_info.last_health_check.isoformat() if server_info.last_health_check else None,
                        "health_failures": server_info.health_check_failures
                    })

                return {
                    "status": "success",
                    "total_servers": len(servers_list),
                    "servers": servers_list
                }

        @self.fastmcp.tool(
            name="get_server_info",
            description="Get detailed information about a specific server",
            input_schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Server name"}
                },
                "required": ["name"]
            }
        )
        async def get_server_info(name: str) -> Dict[str, Any]:
            """Get detailed server information"""
            with self.logger.span("get_server_info", server_name=name):
                if name not in self.servers:
                    return {
                        "status": "error",
                        "message": f"Server '{name}' not found"
                    }

                server_info = self.servers[name]
                server_tools = [tool for tool_key, tool in self.tools.items()
                              if tool.server_name == name]

                return {
                    "status": "success",
                    "server": {
                        "name": server_info.name,
                        "endpoint": server_info.endpoint,
                        "status": server_info.status,
                        "version": server_info.version,
                        "description": server_info.description,
                        "registered_at": server_info.registered_at.isoformat(),
                        "last_health_check": server_info.last_health_check.isoformat() if server_info.last_health_check else None,
                        "last_seen": server_info.last_seen.isoformat() if server_info.last_seen else None,
                        "health_failures": server_info.health_check_failures,
                        "metadata": server_info.metadata,
                        "tools": [
                            {
                                "name": tool.name,
                                "description": tool.description,
                                "use_count": tool.use_count,
                                "error_count": tool.error_count,
                                "last_used": tool.last_used.isoformat() if tool.last_used else None
                            }
                            for tool in server_tools
                        ]
                    }
                }

        @self.fastmcp.tool(
            name="discover_tools",
            description="Discover available tools across all registered servers",
            input_schema={
                "type": "object",
                "properties": {
                    "server_filter": {"type": "string", "description": "Filter by server name", "default": ""},
                    "search_term": {"type": "string", "description": "Search in tool names/descriptions", "default": ""}
                }
            }
        )
        async def discover_tools(server_filter: str = "", search_term: str = "") -> Dict[str, Any]:
            """Discover available tools"""
            with self.logger.span("discover_tools"):
                discovered_tools = []

                for tool_key, tool_info in self.tools.items():
                    # Apply server filter
                    if server_filter and tool_info.server_name != server_filter:
                        continue

                    # Apply search filter
                    if search_term and (search_term.lower() not in tool_info.name.lower() and
                                      search_term.lower() not in tool_info.description.lower()):
                        continue

                    server_info = self.servers.get(tool_info.server_name)

                    discovered_tools.append({
                        "name": tool_info.name,
                        "full_name": tool_key,
                        "server_name": tool_info.server_name,
                        "server_status": server_info.status if server_info else "unknown",
                        "description": tool_info.description,
                        "input_schema": tool_info.input_schema,
                        "use_count": tool_info.use_count,
                        "error_count": tool_info.error_count,
                        "last_used": tool_info.last_used.isoformat() if tool_info.last_used else None
                    })

                return {
                    "status": "success",
                    "total_tools": len(discovered_tools),
                    "tools": discovered_tools
                }

        @self.fastmcp.tool(
            name="health_check",
            description="Perform health check on all or specific servers",
            input_schema={
                "type": "object",
                "properties": {
                    "server_name": {"type": "string", "description": "Specific server to check (optional)"}
                }
            }
        )
        async def health_check(server_name: str = "") -> Dict[str, Any]:
            """Perform health check"""
            with self.logger.span("health_check"):
                if server_name:
                    # Check specific server
                    if server_name not in self.servers:
                        return {
                            "status": "error",
                            "message": f"Server '{server_name}' not found"
                        }

                    result = await self._check_server_health(self.servers[server_name])
                    return {
                        "status": "success",
                        "server": server_name,
                        "health_status": result["status"],
                        "details": result
                    }
                else:
                    # Check all servers
                    results = {}
                    for name, server_info in self.servers.items():
                        results[name] = await self._check_server_health(server_info)

                    healthy_count = sum(1 for r in results.values() if r["status"] == "healthy")

                    return {
                        "status": "success",
                        "total_servers": len(results),
                        "healthy_servers": healthy_count,
                        "unhealthy_servers": len(results) - healthy_count,
                        "results": results
                    }

        @self.fastmcp.tool(
            name="get_registry_status",
            description="Get overall registry status and statistics",
            input_schema={"type": "object", "properties": {}}
        )
        async def get_registry_status() -> Dict[str, Any]:
            """Get registry status"""
            with self.logger.span("get_registry_status"):
                total_servers = len(self.servers)
                healthy_servers = sum(1 for s in self.servers.values() if s.status == "healthy")
                total_tools = len(self.tools)

                return {
                    "status": "success",
                    "registry_name": self.fastmcp.config.name,
                    "version": self.fastmcp.config.version,
                    "timestamp": datetime.now().isoformat(),
                    "servers": {
                        "total": total_servers,
                        "healthy": healthy_servers,
                        "unhealthy": total_servers - healthy_servers
                    },
                    "tools": {
                        "total": total_tools,
                        "total_uses": sum(t.use_count for t in self.tools.values()),
                        "total_errors": sum(t.error_count for t in self.tools.values())
                    },
                    "health_monitor": self.health_monitor.get_simple_status()
                }

    async def _check_server_health(self, server_info: MCPServerInfo) -> Dict[str, Any]:
        """Check health of a specific server"""
        try:
            # Basic connectivity check (simplified for now)
            # In a real implementation, this would attempt to connect to the server
            server_info.last_health_check = datetime.now()

            # Simulate health check logic
            if server_info.health_check_failures < self.max_health_failures:
                server_info.status = "healthy"
                server_info.last_seen = datetime.now()
                return {
                    "status": "healthy",
                    "timestamp": datetime.now().isoformat(),
                    "response_time": 0.1,  # Simulated
                    "endpoint": server_info.endpoint
                }
            else:
                server_info.status = "unhealthy"
                return {
                    "status": "unhealthy",
                    "timestamp": datetime.now().isoformat(),
                    "error": "Too many health check failures",
                    "failure_count": server_info.health_check_failures
                }

        except Exception as e:
            server_info.health_check_failures += 1
            server_info.status = "unhealthy"
            return {
                "status": "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "failure_count": server_info.health_check_failures
            }

    def _load_registry_data(self):
        """Load registry data from storage"""
        try:
            if self.storage_path.exists():
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)

                # Load servers
                for server_data in data.get("servers", []):
                    server_info = MCPServerInfo(
                        name=server_data["name"],
                        endpoint=server_data["endpoint"],
                        tools=server_data["tools"],
                        status=server_data.get("status", "unknown"),
                        version=server_data.get("version", "1.0.0"),
                        description=server_data.get("description", ""),
                        metadata=server_data.get("metadata", {}),
                        health_check_failures=server_data.get("health_check_failures", 0)
                    )

                    if "registered_at" in server_data:
                        server_info.registered_at = datetime.fromisoformat(server_data["registered_at"])
                    if "last_health_check" in server_data and server_data["last_health_check"]:
                        server_info.last_health_check = datetime.fromisoformat(server_data["last_health_check"])
                    if "last_seen" in server_data and server_data["last_seen"]:
                        server_info.last_seen = datetime.fromisoformat(server_data["last_seen"])

                    self.servers[server_info.name] = server_info

                # Load tools
                for tool_data in data.get("tools", []):
                    tool_info = ToolInfo(
                        name=tool_data["name"],
                        server_name=tool_data["server_name"],
                        description=tool_data["description"],
                        input_schema=tool_data.get("input_schema", {}),
                        use_count=tool_data.get("use_count", 0),
                        error_count=tool_data.get("error_count", 0)
                    )

                    if "last_used" in tool_data and tool_data["last_used"]:
                        tool_info.last_used = datetime.fromisoformat(tool_data["last_used"])

                    tool_key = f"{tool_info.server_name}.{tool_info.name}"
                    self.tools[tool_key] = tool_info

                self.logger.info(f"Loaded registry data: {len(self.servers)} servers, {len(self.tools)} tools")

        except Exception as e:
            self.logger.warning(f"Failed to load registry data: {str(e)}")

    async def _save_registry_data(self):
        """Save registry data to storage"""
        try:
            data = {
                "version": "1.0.0",
                "timestamp": datetime.now().isoformat(),
                "servers": [
                    {
                        "name": server.name,
                        "endpoint": server.endpoint,
                        "tools": server.tools,
                        "status": server.status,
                        "version": server.version,
                        "description": server.description,
                        "metadata": server.metadata,
                        "registered_at": server.registered_at.isoformat(),
                        "last_health_check": server.last_health_check.isoformat() if server.last_health_check else None,
                        "last_seen": server.last_seen.isoformat() if server.last_seen else None,
                        "health_check_failures": server.health_check_failures
                    }
                    for server in self.servers.values()
                ],
                "tools": [
                    {
                        "name": tool.name,
                        "server_name": tool.server_name,
                        "description": tool.description,
                        "input_schema": tool.input_schema,
                        "use_count": tool.use_count,
                        "error_count": tool.error_count,
                        "last_used": tool.last_used.isoformat() if tool.last_used else None
                    }
                    for tool in self.tools.values()
                ]
            }

            # Ensure directory exists
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)

            self.logger.info("Registry data saved successfully")

        except Exception as e:
            self.logger.error(f"Failed to save registry data: {str(e)}")

    async def start_monitoring(self):
        """Start health monitoring"""
        await self.health_monitor.start_monitoring()

    async def stop_monitoring(self):
        """Stop health monitoring"""
        await self.health_monitor.stop_monitoring()

    async def run(self):
        """Run the registry server"""
        await self.start_monitoring()
        await self.fastmcp.run_stdio()
