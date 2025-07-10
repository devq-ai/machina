#!/usr/bin/env python3
"""
Tests for FastMCP Registry Implementation
Tests the MCP server registry functionality following PRP-1 requirements.
"""

import json
import pytest
import tempfile
from pathlib import Path
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastmcp import MCPRegistry, FastMCP
from fastmcp.registry import MCPServerInfo, ToolInfo


class TestFastMCPFramework:
    """Test FastMCP framework functionality"""

    @pytest.fixture
    def fastmcp_server(self):
        """Create a FastMCP server for testing"""
        return FastMCP("test-server", version="1.0.0", description="Test server")

    def test_fastmcp_initialization(self, fastmcp_server):
        """Test FastMCP server initialization"""
        assert fastmcp_server.config.name == "test-server"
        assert fastmcp_server.config.version == "1.0.0"
        assert fastmcp_server.config.description == "Test server"
        assert len(fastmcp_server._tools) == 0
        assert len(fastmcp_server._tool_schemas) == 0

    def test_tool_registration(self, fastmcp_server):
        """Test tool registration via decorator"""

        @fastmcp_server.tool(
            name="test_tool",
            description="A test tool",
            input_schema={
                "type": "object",
                "properties": {
                    "param1": {"type": "string"},
                    "param2": {"type": "integer"}
                },
                "required": ["param1"]
            }
        )
        def test_tool(param1: str, param2: int = 42) -> str:
            return f"Called with {param1} and {param2}"

        assert "test_tool" in fastmcp_server._tools
        assert "test_tool" in fastmcp_server._tool_schemas

        tool_schema = fastmcp_server._tool_schemas["test_tool"]
        assert tool_schema.name == "test_tool"
        assert tool_schema.description == "A test tool"
        assert "param1" in tool_schema.inputSchema["properties"]

    @pytest.mark.asyncio
    async def test_tool_execution(self, fastmcp_server):
        """Test tool execution"""

        @fastmcp_server.tool(name="echo_tool")
        async def echo_tool(message: str) -> str:
            return f"Echo: {message}"

        result = await fastmcp_server._call_tool_safe("echo_tool", {"message": "hello"})
        assert result == "Echo: hello"

    def test_health_status(self, fastmcp_server):
        """Test health status reporting"""
        health = fastmcp_server.get_health_status()

        assert health["status"] == "healthy"
        assert health["server_name"] == "test-server"
        assert health["version"] == "1.0.0"
        assert "uptime" in health
        assert health["tools_registered"] == 0


class TestMCPRegistry:
    """Test MCP Registry functionality"""

    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage file"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name
        yield temp_path
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    @pytest.fixture
    def registry(self, temp_storage):
        """Create registry instance for testing"""
        return MCPRegistry(
            registry_name="test-registry",
            storage_path=temp_storage
        )

    def test_registry_initialization(self, registry):
        """Test registry initialization"""
        assert registry.fastmcp.config.name == "test-registry"
        assert len(registry.servers) == 0
        assert len(registry.tools) == 0
        assert registry.health_check_interval == 30
        assert registry.max_health_failures == 3

    @pytest.mark.asyncio
    async def test_server_registration(self, registry):
        """Test server registration functionality"""

        # Register a test server
        result = await registry.fastmcp._call_tool_safe(
            "register_server",
            {
                "name": "test-server",
                "endpoint": "stdio://test",
                "tools": ["tool1", "tool2"],
                "version": "1.0.0",
                "description": "Test server"
            }
        )

        assert result["status"] == "success"
        assert "test-server" in registry.servers

        server_info = registry.servers["test-server"]
        assert server_info.name == "test-server"
        assert server_info.endpoint == "stdio://test"
        assert server_info.tools == ["tool1", "tool2"]
        assert server_info.version == "1.0.0"
        assert server_info.status == "registered"

        # Check tools are registered
        assert "test-server.tool1" in registry.tools
        assert "test-server.tool2" in registry.tools

    @pytest.mark.asyncio
    async def test_server_unregistration(self, registry):
        """Test server unregistration"""

        # First register a server
        await registry.fastmcp._call_tool_safe(
            "register_server",
            {
                "name": "test-server",
                "endpoint": "stdio://test",
                "tools": ["tool1", "tool2"]
            }
        )

        # Then unregister it
        result = await registry.fastmcp._call_tool_safe(
            "unregister_server",
            {"name": "test-server"}
        )

        assert result["status"] == "success"
        assert "test-server" not in registry.servers
        assert "test-server.tool1" not in registry.tools
        assert "test-server.tool2" not in registry.tools

    @pytest.mark.asyncio
    async def test_list_servers(self, registry):
        """Test server listing functionality"""

        # Register multiple servers
        servers_data = [
            {"name": "server1", "endpoint": "stdio://server1", "tools": ["tool1"]},
            {"name": "server2", "endpoint": "stdio://server2", "tools": ["tool2"]}
        ]

        for server_data in servers_data:
            await registry.fastmcp._call_tool_safe("register_server", server_data)

        # List all servers
        result = await registry.fastmcp._call_tool_safe("list_servers", {})

        assert result["status"] == "success"
        assert result["total_servers"] == 2
        assert len(result["servers"]) == 2

        server_names = [s["name"] for s in result["servers"]]
        assert "server1" in server_names
        assert "server2" in server_names

    @pytest.mark.asyncio
    async def test_discover_tools(self, registry):
        """Test tool discovery functionality"""

        # Register servers with tools
        await registry.fastmcp._call_tool_safe(
            "register_server",
            {
                "name": "math-server",
                "endpoint": "stdio://math",
                "tools": ["add", "subtract", "multiply"]
            }
        )

        await registry.fastmcp._call_tool_safe(
            "register_server",
            {
                "name": "text-server",
                "endpoint": "stdio://text",
                "tools": ["uppercase", "lowercase"]
            }
        )

        # Discover all tools
        result = await registry.fastmcp._call_tool_safe("discover_tools", {})

        assert result["status"] == "success"
        assert result["total_tools"] == 5

        tool_names = [t["name"] for t in result["tools"]]
        assert "add" in tool_names
        assert "uppercase" in tool_names

        # Test server filtering
        result = await registry.fastmcp._call_tool_safe(
            "discover_tools",
            {"server_filter": "math-server"}
        )

        assert result["total_tools"] == 3
        math_tools = [t["name"] for t in result["tools"]]
        assert all(tool in ["add", "subtract", "multiply"] for tool in math_tools)

    @pytest.mark.asyncio
    async def test_health_check(self, registry):
        """Test health check functionality"""

        # Register a server
        await registry.fastmcp._call_tool_safe(
            "register_server",
            {
                "name": "test-server",
                "endpoint": "stdio://test",
                "tools": ["tool1"]
            }
        )

        # Perform health check
        result = await registry.fastmcp._call_tool_safe("health_check", {})

        assert result["status"] == "success"
        assert result["total_servers"] == 1
        assert "test-server" in result["results"]

        server_health = result["results"]["test-server"]
        assert "status" in server_health
        assert "timestamp" in server_health

    @pytest.mark.asyncio
    async def test_registry_status(self, registry):
        """Test registry status reporting"""

        # Register some servers
        await registry.fastmcp._call_tool_safe(
            "register_server",
            {
                "name": "server1",
                "endpoint": "stdio://server1",
                "tools": ["tool1", "tool2"]
            }
        )

        result = await registry.fastmcp._call_tool_safe("get_registry_status", {})

        assert result["status"] == "success"
        assert result["registry_name"] == "test-registry"
        assert result["servers"]["total"] == 1
        assert result["tools"]["total"] == 2
        assert "timestamp" in result
        assert "health_monitor" in result

    @pytest.mark.asyncio
    async def test_data_persistence(self, registry, temp_storage):
        """Test data persistence to storage file"""

        # Register a server
        await registry.fastmcp._call_tool_safe(
            "register_server",
            {
                "name": "persistent-server",
                "endpoint": "stdio://persistent",
                "tools": ["tool1"],
                "description": "Persistent test server"
            }
        )

        # Check that data was saved
        assert os.path.exists(temp_storage)

        with open(temp_storage, 'r') as f:
            data = json.load(f)

        assert "servers" in data
        assert "tools" in data
        assert len(data["servers"]) == 1
        assert data["servers"][0]["name"] == "persistent-server"

        # Create new registry instance and verify data loads
        registry2 = MCPRegistry(
            registry_name="test-registry-2",
            storage_path=temp_storage
        )

        assert "persistent-server" in registry2.servers
        assert "persistent-server.tool1" in registry2.tools

    def test_server_info_dataclass(self):
        """Test MCPServerInfo dataclass"""
        server_info = MCPServerInfo(
            name="test-server",
            endpoint="stdio://test",
            tools=["tool1", "tool2"],
            version="2.0.0",
            description="Test server for validation"
        )

        assert server_info.name == "test-server"
        assert server_info.endpoint == "stdio://test"
        assert server_info.tools == ["tool1", "tool2"]
        assert server_info.version == "2.0.0"
        assert server_info.description == "Test server for validation"
        assert server_info.status == "unknown"
        assert server_info.health_check_failures == 0

    def test_tool_info_dataclass(self):
        """Test ToolInfo dataclass"""
        tool_info = ToolInfo(
            name="test-tool",
            server_name="test-server",
            description="A test tool",
            input_schema={"type": "object", "properties": {}}
        )

        assert tool_info.name == "test-tool"
        assert tool_info.server_name == "test-server"
        assert tool_info.description == "A test tool"
        assert tool_info.use_count == 0
        assert tool_info.error_count == 0
        assert tool_info.last_used is None

    @pytest.mark.asyncio
    async def test_error_handling(self, registry):
        """Test error handling in registry operations"""

        # Test registering server with missing required fields
        try:
            await registry.fastmcp._call_tool_safe(
                "register_server",
                {"name": "incomplete-server"}  # Missing endpoint and tools
            )
            assert False, "Should have raised an error"
        except Exception:
            pass  # Expected

        # Test getting info for non-existent server
        result = await registry.fastmcp._call_tool_safe(
            "get_server_info",
            {"name": "non-existent-server"}
        )
        assert result["status"] == "error"

        # Test unregistering non-existent server
        result = await registry.fastmcp._call_tool_safe(
            "unregister_server",
            {"name": "non-existent-server"}
        )
        assert result["status"] == "error"


class TestIntegration:
    """Integration tests for the complete registry system"""

    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self):
        """Test complete end-to-end workflow"""

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name

        try:
            # Create registry
            registry = MCPRegistry(registry_name="e2e-test", storage_path=temp_path)

            # Register multiple servers
            servers = [
                {
                    "name": "math-service",
                    "endpoint": "http://localhost:8001",
                    "tools": ["add", "subtract", "multiply", "divide"],
                    "description": "Mathematical operations service"
                },
                {
                    "name": "text-service",
                    "endpoint": "http://localhost:8002",
                    "tools": ["uppercase", "lowercase", "reverse"],
                    "description": "Text processing service"
                }
            ]

            for server in servers:
                result = await registry.fastmcp._call_tool_safe("register_server", server)
                assert result["status"] == "success"

            # Verify registration
            list_result = await registry.fastmcp._call_tool_safe("list_servers", {})
            assert list_result["total_servers"] == 2

            # Discover tools
            tools_result = await registry.fastmcp._call_tool_safe("discover_tools", {})
            assert tools_result["total_tools"] == 7

            # Get registry status
            status_result = await registry.fastmcp._call_tool_safe("get_registry_status", {})
            assert status_result["servers"]["total"] == 2
            assert status_result["tools"]["total"] == 7

            # Perform health checks
            health_result = await registry.fastmcp._call_tool_safe("health_check", {})
            assert health_result["total_servers"] == 2

            # Test server-specific operations
            math_info = await registry.fastmcp._call_tool_safe(
                "get_server_info",
                {"name": "math-service"}
            )
            assert math_info["status"] == "success"
            assert len(math_info["server"]["tools"]) == 4

            # Test filtering
            math_tools = await registry.fastmcp._call_tool_safe(
                "discover_tools",
                {"server_filter": "math-service"}
            )
            assert math_tools["total_tools"] == 4

        finally:
            # Cleanup
            if os.path.exists(temp_path):
                os.unlink(temp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
