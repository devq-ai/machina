#!/usr/bin/env python3
"""
Registry MCP Server
Official MCP server registry with discovery and installation tools using FastMCP framework.
"""

import asyncio
import json
import os
import subprocess
import hashlib
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add parent directory to path for FastMCP imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastmcp import FastMCP
import logfire

try:
    import httpx
    from pydantic import BaseModel, Field, HttpUrl
    REGISTRY_DEPS_AVAILABLE = True
except ImportError:
    REGISTRY_DEPS_AVAILABLE = False
    httpx = None
    BaseModel = object
    def Field(*args, **kwargs):
        return None
    HttpUrl = str


class MCPServerEntry(BaseModel if REGISTRY_DEPS_AVAILABLE else object):
    """MCP Server registry entry model"""
    name: str = Field(..., description="Server name")
    description: str = Field(..., description="Server description")
    repository_url: str = Field(..., description="Repository URL")
    version: str = Field(..., description="Server version")
    author: str = Field(..., description="Author name")
    tools: List[str] = Field(default_factory=list, description="Available tools")
    dependencies: List[str] = Field(default_factory=list, description="Dependencies")
    installation_command: str = Field(..., description="Installation command")
    verified: bool = Field(False, description="Verification status")
    downloads: int = Field(0, description="Download count")
    rating: float = Field(0.0, description="Average rating")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")


class RegistryMCP:
    """
    Registry MCP Server using FastMCP framework

    Provides comprehensive MCP server registry operations including:
    - Server discovery and search
    - Server installation and management
    - Registry publishing and updates
    - Server verification and validation
    - Community ratings and reviews
    - Dependency management
    - Version control and updates
    """

    def __init__(self):
        self.mcp = FastMCP("registry-mcp", version="1.0.0",
                          description="Official MCP server registry with discovery and installation tools")
        self.registry_url = os.getenv("MCP_REGISTRY_URL", "https://registry.modelcontextprotocol.io")
        self.local_registry_path = os.getenv("MCP_LOCAL_REGISTRY", "./mcp_registry.json")
        self.installed_servers: Dict[str, MCPServerEntry] = {}
        self.registry_cache: Dict[str, MCPServerEntry] = {}
        self.http_client: Optional[httpx.AsyncClient] = None
        self._setup_tools()
        self._initialize_client()

    def _initialize_client(self):
        """Initialize Registry HTTP client"""
        if not REGISTRY_DEPS_AVAILABLE:
            logfire.warning("Registry dependencies not available. Install with: pip install httpx pydantic")
            return

        try:
            self.http_client = httpx.AsyncClient(
                timeout=30.0,
                headers={"User-Agent": "Registry-MCP/1.0"}
            )

            # Load local registry cache
            self._load_local_registry()
            logfire.info("Registry MCP client initialized successfully")
        except Exception as e:
            logfire.error(f"Failed to initialize Registry client: {str(e)}")

    def _load_local_registry(self):
        """Load local registry cache"""
        try:
            if os.path.exists(self.local_registry_path):
                with open(self.local_registry_path, 'r') as f:
                    data = json.load(f)
                    for server_name, server_data in data.items():
                        if REGISTRY_DEPS_AVAILABLE:
                            self.registry_cache[server_name] = MCPServerEntry(**server_data)
                        else:
                            self.registry_cache[server_name] = server_data
        except Exception as e:
            logfire.error(f"Failed to load local registry: {str(e)}")

    def _save_local_registry(self):
        """Save local registry cache"""
        try:
            data = {}
            for server_name, server_entry in self.registry_cache.items():
                if REGISTRY_DEPS_AVAILABLE and hasattr(server_entry, 'dict'):
                    data[server_name] = server_entry.dict()
                else:
                    data[server_name] = server_entry

            with open(self.local_registry_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logfire.error(f"Failed to save local registry: {str(e)}")

    def _setup_tools(self):
        """Setup Registry MCP tools"""

        @self.mcp.tool(
            name="search_servers",
            description="Search for MCP servers in the registry",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "category": {"type": "string", "description": "Server category filter"},
                    "verified_only": {"type": "boolean", "description": "Show only verified servers", "default": False},
                    "limit": {"type": "integer", "description": "Maximum results", "default": 20}
                }
            }
        )
        async def search_servers(query: str = None, category: str = None, verified_only: bool = False,
                               limit: int = 20) -> Dict[str, Any]:
            """Search for MCP servers in the registry"""
            try:
                if not self._check_client():
                    return self._search_local_registry(query, category, verified_only, limit)

                # Build search parameters
                params = {"limit": limit}
                if query:
                    params["q"] = query
                if category:
                    params["category"] = category
                if verified_only:
                    params["verified"] = "true"

                # Search remote registry
                try:
                    response = await self.http_client.get(f"{self.registry_url}/api/search", params=params)
                    response.raise_for_status()

                    data = response.json()
                    servers = data.get("servers", [])

                    return {
                        "status": "success",
                        "source": "remote",
                        "total_found": len(servers),
                        "query": query,
                        "servers": servers
                    }
                except Exception as e:
                    logfire.warning(f"Remote registry search failed: {str(e)}, falling back to local")
                    return self._search_local_registry(query, category, verified_only, limit)

            except Exception as e:
                logfire.error(f"Failed to search servers: {str(e)}")
                return {"error": f"Server search failed: {str(e)}"}

        @self.mcp.tool(
            name="get_server_info",
            description="Get detailed information about a specific server",
            input_schema={
                "type": "object",
                "properties": {
                    "server_name": {"type": "string", "description": "Server name"}
                },
                "required": ["server_name"]
            }
        )
        async def get_server_info(server_name: str) -> Dict[str, Any]:
            """Get detailed server information"""
            try:
                # Check local cache first
                if server_name in self.registry_cache:
                    server_entry = self.registry_cache[server_name]
                    if REGISTRY_DEPS_AVAILABLE and hasattr(server_entry, 'dict'):
                        return {"status": "found", "source": "local", **server_entry.dict()}
                    else:
                        return {"status": "found", "source": "local", **server_entry}

                # Try remote registry
                if self._check_client():
                    try:
                        response = await self.http_client.get(f"{self.registry_url}/api/servers/{server_name}")
                        response.raise_for_status()

                        server_data = response.json()
                        return {"status": "found", "source": "remote", **server_data}
                    except httpx.HTTPStatusError as e:
                        if e.response.status_code == 404:
                            return {"error": f"Server '{server_name}' not found in registry"}
                        raise

                return {"error": f"Server '{server_name}' not found"}

            except Exception as e:
                logfire.error(f"Failed to get server info: {str(e)}")
                return {"error": f"Server info retrieval failed: {str(e)}"}

        @self.mcp.tool(
            name="install_server",
            description="Install an MCP server from the registry",
            input_schema={
                "type": "object",
                "properties": {
                    "server_name": {"type": "string", "description": "Server name to install"},
                    "version": {"type": "string", "description": "Specific version to install"},
                    "force": {"type": "boolean", "description": "Force reinstall", "default": False}
                },
                "required": ["server_name"]
            }
        )
        async def install_server(server_name: str, version: str = None, force: bool = False) -> Dict[str, Any]:
            """Install an MCP server"""
            try:
                # Get server info
                server_info = await get_server_info(server_name)
                if "error" in server_info:
                    return server_info

                # Check if already installed
                if server_name in self.installed_servers and not force:
                    return {"error": f"Server '{server_name}' is already installed. Use force=true to reinstall."}

                # Get installation command
                install_cmd = server_info.get("installation_command")
                if not install_cmd:
                    return {"error": f"No installation command available for '{server_name}'"}

                # Execute installation
                if version:
                    install_cmd = install_cmd.replace("@latest", f"@{version}")

                result = subprocess.run(
                    install_cmd.split(),
                    capture_output=True,
                    text=True
                )

                if result.returncode == 0:
                    # Mark as installed
                    if REGISTRY_DEPS_AVAILABLE:
                        self.installed_servers[server_name] = MCPServerEntry(**server_info)
                    else:
                        self.installed_servers[server_name] = server_info

                    return {
                        "status": "installed",
                        "server_name": server_name,
                        "version": version or "latest",
                        "installation_output": result.stdout
                    }
                else:
                    return {
                        "status": "failed",
                        "server_name": server_name,
                        "error": result.stderr,
                        "exit_code": result.returncode
                    }

            except Exception as e:
                logfire.error(f"Failed to install server: {str(e)}")
                return {"error": f"Server installation failed: {str(e)}"}

        @self.mcp.tool(
            name="list_installed_servers",
            description="List all installed MCP servers",
            input_schema={
                "type": "object",
                "properties": {}
            }
        )
        async def list_installed_servers() -> Dict[str, Any]:
            """List installed MCP servers"""
            try:
                servers_list = []
                for server_name, server_entry in self.installed_servers.items():
                    if REGISTRY_DEPS_AVAILABLE and hasattr(server_entry, 'dict'):
                        servers_list.append(server_entry.dict())
                    else:
                        servers_list.append(server_entry)

                return {
                    "total_installed": len(servers_list),
                    "servers": servers_list
                }

            except Exception as e:
                logfire.error(f"Failed to list installed servers: {str(e)}")
                return {"error": f"Installed servers listing failed: {str(e)}"}

        @self.mcp.tool(
            name="update_registry_cache",
            description="Update local registry cache from remote",
            input_schema={
                "type": "object",
                "properties": {}
            }
        )
        async def update_registry_cache() -> Dict[str, Any]:
            """Update local registry cache"""
            try:
                if not self._check_client():
                    return {"error": "Registry client not available"}

                # Fetch latest registry data
                response = await self.http_client.get(f"{self.registry_url}/api/servers")
                response.raise_for_status()

                registry_data = response.json()
                servers = registry_data.get("servers", [])

                # Update cache
                updated_count = 0
                for server_data in servers:
                    server_name = server_data.get("name")
                    if server_name:
                        if REGISTRY_DEPS_AVAILABLE:
                            self.registry_cache[server_name] = MCPServerEntry(**server_data)
                        else:
                            self.registry_cache[server_name] = server_data
                        updated_count += 1

                # Save to disk
                self._save_local_registry()

                return {
                    "status": "updated",
                    "servers_updated": updated_count,
                    "cache_path": self.local_registry_path,
                    "last_updated": datetime.utcnow().isoformat()
                }

            except Exception as e:
                logfire.error(f"Failed to update registry cache: {str(e)}")
                return {"error": f"Registry cache update failed: {str(e)}"}

        @self.mcp.tool(
            name="publish_server",
            description="Publish a new server to the registry",
            input_schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Server name"},
                    "description": {"type": "string", "description": "Server description"},
                    "repository_url": {"type": "string", "description": "Repository URL"},
                    "version": {"type": "string", "description": "Server version"},
                    "author": {"type": "string", "description": "Author name"},
                    "tools": {"type": "array", "items": {"type": "string"}, "description": "Available tools"},
                    "installation_command": {"type": "string", "description": "Installation command"}
                },
                "required": ["name", "description", "repository_url", "version", "author", "installation_command"]
            }
        )
        async def publish_server(name: str, description: str, repository_url: str, version: str,
                               author: str, tools: List[str] = None, installation_command: str = None) -> Dict[str, Any]:
            """Publish a server to the registry"""
            try:
                if not self._check_client():
                    return {"error": "Registry client not available"}

                server_data = {
                    "name": name,
                    "description": description,
                    "repository_url": repository_url,
                    "version": version,
                    "author": author,
                    "tools": tools or [],
                    "dependencies": [],
                    "installation_command": installation_command,
                    "verified": False,
                    "downloads": 0,
                    "rating": 0.0,
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                }

                # Submit to registry
                response = await self.http_client.post(
                    f"{self.registry_url}/api/servers",
                    json=server_data
                )
                response.raise_for_status()

                result = response.json()

                return {
                    "status": "published",
                    "server_name": name,
                    "submission_id": result.get("id"),
                    "verification_pending": True
                }

            except Exception as e:
                logfire.error(f"Failed to publish server: {str(e)}")
                return {"error": f"Server publishing failed: {str(e)}"}

        @self.mcp.tool(
            name="get_registry_stats",
            description="Get registry statistics and information",
            input_schema={
                "type": "object",
                "properties": {}
            }
        )
        async def get_registry_stats() -> Dict[str, Any]:
            """Get registry statistics"""
            try:
                local_cache_size = len(self.registry_cache)
                installed_count = len(self.installed_servers)

                # Get remote stats if available
                remote_stats = None
                if self._check_client():
                    try:
                        response = await self.http_client.get(f"{self.registry_url}/api/stats")
                        if response.status_code == 200:
                            remote_stats = response.json()
                    except Exception:
                        pass

                return {
                    "local_cache_size": local_cache_size,
                    "installed_servers": installed_count,
                    "registry_url": self.registry_url,
                    "local_registry_path": self.local_registry_path,
                    "remote_stats": remote_stats,
                    "dependencies_available": REGISTRY_DEPS_AVAILABLE
                }

            except Exception as e:
                logfire.error(f"Failed to get registry stats: {str(e)}")
                return {"error": f"Registry stats query failed: {str(e)}"}

    def _search_local_registry(self, query: str, category: str, verified_only: bool, limit: int) -> Dict[str, Any]:
        """Search local registry cache"""
        try:
            results = []
            query_lower = query.lower() if query else ""

            for server_name, server_entry in self.registry_cache.items():
                # Extract data based on type
                if REGISTRY_DEPS_AVAILABLE and hasattr(server_entry, 'name'):
                    name = server_entry.name
                    description = server_entry.description
                    verified = server_entry.verified
                    server_data = server_entry.dict()
                else:
                    name = server_entry.get('name', '')
                    description = server_entry.get('description', '')
                    verified = server_entry.get('verified', False)
                    server_data = server_entry

                # Apply filters
                if query and query_lower not in name.lower() and query_lower not in description.lower():
                    continue

                if verified_only and not verified:
                    continue

                results.append(server_data)

                if len(results) >= limit:
                    break

            return {
                "status": "success",
                "source": "local",
                "total_found": len(results),
                "query": query,
                "servers": results
            }

        except Exception as e:
            return {"error": f"Local search failed: {str(e)}"}

    def _check_client(self) -> bool:
        """Check if registry client is available"""
        return REGISTRY_DEPS_AVAILABLE and self.http_client is not None

    async def run(self):
        """Run the Registry MCP server"""
        try:
            await self.mcp.run_stdio()
        finally:
            if self.http_client:
                await self.http_client.aclose()


async def main():
    """Main entry point"""
    server = RegistryMCP()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
