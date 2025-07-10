"""
Machina MCP Server Suite
Comprehensive collection of production-ready MCP servers using FastMCP framework.
"""

from .github_mcp import GitHubMCP
from .docker_mcp import DockerMCP
from .fastmcp_mcp import FastMCPMCPServer
from .bayes_mcp import BayesMCPServer
from .darwin_mcp import DarwinMCPServer
from .context7_mcp import Context7MCP
from .crawl4ai_mcp import Crawl4AIMCP
from .fastapi_mcp import FastAPIMCP
from .logfire_mcp import LogfireMCP
from .memory_mcp import MemoryMCP
from .pydantic_ai_mcp import PydanticAIMCP
from .pytest_mcp import PyTestMCP
from .registry_mcp import RegistryMCP
from .sequential_thinking_mcp import SequentialThinkingMCPServer
from .surrealdb_mcp import SurrealDBMCPServer

__version__ = "1.0.0"
__all__ = [
    "GitHubMCP",
    "DockerMCP",
    "FastMCPMCPServer",
    "BayesMCPServer",
    "DarwinMCPServer",
    "Context7MCP",
    "Crawl4AIMCP",
    "FastAPIMCP",
    "LogfireMCP",
    "MemoryMCP",
    "PydanticAIMCP",
    "PyTestMCP",
    "RegistryMCP",
    "SequentialThinkingMCPServer",
    "SurrealDBMCPServer",
]

# MCP Server Registry - Production Servers
MCP_SERVERS = {
    "github-mcp": GitHubMCP,
    "docker-mcp": DockerMCP,
    "fastmcp-mcp": FastMCPMCPServer,
    "bayes-mcp": BayesMCPServer,
    "darwin-mcp": DarwinMCPServer,
    "context7-mcp": Context7MCP,
    "crawl4ai-mcp": Crawl4AIMCP,
    "fastapi-mcp": FastAPIMCP,
    "logfire-mcp": LogfireMCP,
    "memory-mcp": MemoryMCP,
    "pydantic-ai-mcp": PydanticAIMCP,
    "pytest-mcp": PyTestMCP,
    "registry-mcp": RegistryMCP,
    "sequential-thinking-mcp": SequentialThinkingMCPServer,
    "surrealdb-mcp": SurrealDBMCPServer,
}

def get_server_class(server_name: str):
    """Get MCP server class by name"""
    return MCP_SERVERS.get(server_name)

def list_available_servers():
    """List all available MCP servers"""
    return list(MCP_SERVERS.keys())

def get_server_info():
    """Get information about all available MCP servers"""
    return {
        "total_servers": len(MCP_SERVERS),
        "servers": list(MCP_SERVERS.keys()),
        "version": __version__
    }
