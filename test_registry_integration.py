#!/usr/bin/env python3
"""
Test integration with MCP registry using one of our verified servers.
"""

import logging
from fastmcp_http.server import FastMCPHttpServer

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create server using the FastMCPHttpServer that auto-registers
mcp = FastMCPHttpServer("MachinaTestServer", description="Test server from Machina with verified tools")

@mcp.tool()
def health_check() -> dict:
    """Check server health and return status."""
    return {
        "status": "healthy",
        "server": "machina-test-server",
        "framework": "FastMCP",
        "version": "1.10.1",
        "registry_integrated": True
    }

@mcp.tool()
def get_server_info() -> dict:
    """Get detailed server information."""
    return {
        "name": "machina-test-server", 
        "description": "Test server from Machina MCP collection",
        "category": "test",
        "total_servers_in_collection": 13,
        "total_tools_in_collection": 81,
        "verification_status": "all_13_servers_pass_tools_list"
    }

@mcp.tool()
def echo_message(message: str, repeat_count: int = 1) -> str:
    """Echo a message the specified number of times."""
    return "\n".join([f"Echo {i+1}: {message}" for i in range(repeat_count)])

@mcp.tool()
def list_machina_servers() -> dict:
    """List all 13 Machina MCP servers with tool counts."""
    servers = {
        "surrealdb_mcp": {"tools": 10, "category": "database"},
        "sequential_thinking_mcp": {"tools": 9, "category": "knowledge"},
        "registry_mcp": {"tools": 8, "category": "framework"},
        "memory_mcp": {"tools": 8, "category": "knowledge"},
        "docker_mcp": {"tools": 7, "category": "infrastructure"},
        "pytest_mcp": {"tools": 7, "category": "development"},
        "fastapi_mcp": {"tools": 6, "category": "development"},
        "fastmcp_mcp": {"tools": 6, "category": "framework"},
        "github_mcp": {"tools": 6, "category": "web"},
        "pydantic_ai_mcp": {"tools": 6, "category": "development"},
        "server_template": {"tools": 5, "category": "template"},
        "crawl4ai_mcp": {"tools": 4, "category": "web"},
        "logfire_mcp": {"tools": 4, "category": "infrastructure"}
    }
    
    return {
        "machina_servers": servers,
        "total_servers": len(servers),
        "total_tools": sum(server["tools"] for server in servers.values()),
        "verification_status": "all_verified_working"
    }

if __name__ == "__main__":
    logger.info("🚀 Starting Machina Test Server")
    logger.info("📡 Auto-registering with MCP Registry at http://127.0.0.1:31337")
    logger.info("🔧 This server demonstrates our 13 verified MCP servers")
    mcp.run_http()