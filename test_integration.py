#!/usr/bin/env python3
"""
Integration test for FastMCP Registry Implementation
Tests registry functionality without Logfire dependencies
"""

import asyncio
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from fastmcp.core import FastMCP
from fastmcp.registry import MCPRegistry, MCPServerInfo, ToolInfo
from fastmcp.health import HealthMonitor, HealthStatus


class MockLogfire:
    """Mock logfire for testing without credentials"""

    @staticmethod
    def configure():
        pass

    @staticmethod
    def info(msg, **kwargs):
        print(f"INFO: {msg} {kwargs}")

    @staticmethod
    def error(msg, **kwargs):
        print(f"ERROR: {msg} {kwargs}")

    @staticmethod
    def warning(msg, **kwargs):
        print(f"WARNING: {msg} {kwargs}")

    def span(self, name, **kwargs):
        return MockSpan(name, kwargs)


class MockSpan:
    def __init__(self, name, kwargs):
        self.name = name
        self.kwargs = kwargs

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


# Monkey patch logfire
import fastmcp.core
import fastmcp.registry
import fastmcp.health
import fastmcp.tools

mock_logfire = MockLogfire()
fastmcp.core.logfire = mock_logfire
fastmcp.registry.logfire = mock_logfire
fastmcp.health.logfire = mock_logfire
fastmcp.tools.logfire = mock_logfire


async def test_fastmcp_framework():
    """Test FastMCP framework functionality"""
    print("\n=== Testing FastMCP Framework ===")

    # Create FastMCP server
    server = FastMCP("test-server", version="1.0.0", description="Test server")

    # Register a test tool
    @server.tool(
        name="echo_tool",
        description="Echo back a message",
        input_schema={
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Message to echo"}
            },
            "required": ["message"]
        }
    )
    async def echo_tool(message: str) -> str:
        return f"Echo: {message}"

    # Test tool registration
    assert "echo_tool" in server._tools
    assert "echo_tool" in server._tool_schemas
    print("✅ Tool registration successful")

    # Test tool execution
    result = await server._call_tool_safe("echo_tool", {"message": "Hello World"})
    assert result == "Echo: Hello World"
    print("✅ Tool execution successful")

    # Test health status
    health = server.get_health_status()
    assert health["status"] == "healthy"
    assert health["server_name"] == "test-server"
    print("✅ Health status check successful")

    print("FastMCP Framework tests completed successfully!")


async def test_mcp_registry():
    """Test MCP Registry functionality"""
    print("\n=== Testing MCP Registry ===")

    # Create registry with temp storage
    registry = MCPRegistry(
        registry_name="test-registry",
        storage_path="/tmp/test_mcp_status.json"
    )

    # Test server registration
    result = await registry.fastmcp._call_tool_safe(
        "register_server",
        {
            "name": "test-server",
            "endpoint": "stdio://test",
            "tools": ["tool1", "tool2"],
            "version": "1.0.0",
            "description": "Test server for integration"
        }
    )

    assert result["status"] == "success"
    assert "test-server" in registry.servers
    print("✅ Server registration successful")

    # Test server listing
    result = await registry.fastmcp._call_tool_safe("list_servers", {})
    assert result["status"] == "success"
    assert result["total_servers"] == 1
    print("✅ Server listing successful")

    # Test tool discovery
    result = await registry.fastmcp._call_tool_safe("discover_tools", {})
    assert result["status"] == "success"
    assert result["total_tools"] == 2
    print("✅ Tool discovery successful")

    # Test health check
    result = await registry.fastmcp._call_tool_safe("health_check", {})
    assert result["status"] == "success"
    print("✅ Health check successful")

    # Test registry status
    result = await registry.fastmcp._call_tool_safe("get_registry_status", {})
    assert result["status"] == "success"
    assert result["servers"]["total"] == 1
    assert result["tools"]["total"] == 2
    print("✅ Registry status check successful")

    # Test server unregistration
    result = await registry.fastmcp._call_tool_safe(
        "unregister_server",
        {"name": "test-server"}
    )
    assert result["status"] == "success"
    assert "test-server" not in registry.servers
    print("✅ Server unregistration successful")

    print("MCP Registry tests completed successfully!")


async def test_data_persistence():
    """Test data persistence functionality"""
    print("\n=== Testing Data Persistence ===")

    storage_path = "/tmp/test_persistence.json"

    # Create registry and register a server
    registry1 = MCPRegistry(
        registry_name="persistence-test",
        storage_path=storage_path
    )

    await registry1.fastmcp._call_tool_safe(
        "register_server",
        {
            "name": "persistent-server",
            "endpoint": "stdio://persistent",
            "tools": ["persistent-tool"],
            "description": "Persistent test server"
        }
    )

    # Verify data was saved
    with open(storage_path, 'r') as f:
        data = json.load(f)

    assert "servers" in data
    assert len(data["servers"]) == 1
    assert data["servers"][0]["name"] == "persistent-server"
    print("✅ Data save successful")

    # Create new registry instance and verify data loads
    registry2 = MCPRegistry(
        registry_name="persistence-test-2",
        storage_path=storage_path
    )

    assert "persistent-server" in registry2.servers
    assert "persistent-server.persistent-tool" in registry2.tools
    print("✅ Data load successful")

    # Cleanup
    import os
    if os.path.exists(storage_path):
        os.unlink(storage_path)

    print("Data persistence tests completed successfully!")


async def test_health_monitoring():
    """Test health monitoring functionality"""
    print("\n=== Testing Health Monitoring ===")

    # Create health monitor
    monitor = HealthMonitor("test-monitor")

    # Add a basic health check
    def basic_check():
        return True

    monitor.add_health_check("basic", basic_check, interval=5)

    # Test health check execution
    check = monitor.health_checks["basic"]
    result = await monitor.run_health_check(check)
    assert result is True
    print("✅ Health check execution successful")

    # Test status reporting
    status = monitor.get_health_status()
    assert status == HealthStatus.HEALTHY
    print("✅ Health status reporting successful")

    # Test detailed status
    detailed = monitor.get_detailed_status()
    assert detailed["server_name"] == "test-monitor"
    assert "health_checks" in detailed
    print("✅ Detailed status reporting successful")

    print("Health monitoring tests completed successfully!")


async def test_end_to_end_workflow():
    """Test complete end-to-end workflow"""
    print("\n=== Testing End-to-End Workflow ===")

    # Create registry
    registry = MCPRegistry(
        registry_name="e2e-test",
        storage_path="/tmp/e2e_test.json"
    )

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

    print("✅ Multiple server registration successful")

    # Verify registration
    list_result = await registry.fastmcp._call_tool_safe("list_servers", {})
    assert list_result["total_servers"] == 2
    print("✅ Server listing verification successful")

    # Discover tools
    tools_result = await registry.fastmcp._call_tool_safe("discover_tools", {})
    assert tools_result["total_tools"] == 7
    print("✅ Tool discovery verification successful")

    # Get registry status
    status_result = await registry.fastmcp._call_tool_safe("get_registry_status", {})
    assert status_result["servers"]["total"] == 2
    assert status_result["tools"]["total"] == 7
    print("✅ Registry status verification successful")

    # Test filtering
    math_tools = await registry.fastmcp._call_tool_safe(
        "discover_tools",
        {"server_filter": "math-service"}
    )
    assert math_tools["total_tools"] == 4
    print("✅ Tool filtering verification successful")

    # Cleanup
    import os
    if os.path.exists("/tmp/e2e_test.json"):
        os.unlink("/tmp/e2e_test.json")

    print("End-to-end workflow tests completed successfully!")


async def main():
    """Main test runner"""
    print("🚀 Starting FastMCP Registry Integration Tests")
    print("=" * 60)

    try:
        await test_fastmcp_framework()
        await test_mcp_registry()
        await test_data_persistence()
        await test_health_monitoring()
        await test_end_to_end_workflow()

        print("\n" + "=" * 60)
        print("🎉 ALL INTEGRATION TESTS PASSED!")
        print("FastMCP Registry implementation is working correctly.")

        # Print summary
        print("\n📊 Test Summary:")
        print("✅ FastMCP Framework - Core functionality")
        print("✅ MCP Registry - Server and tool management")
        print("✅ Data Persistence - Storage and loading")
        print("✅ Health Monitoring - Status and checks")
        print("✅ End-to-End - Complete workflow")

        return True

    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
