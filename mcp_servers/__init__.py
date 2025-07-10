"""
Machina MCP Server Suite
Comprehensive collection of production-ready MCP servers using FastMCP framework.
"""

from .github_mcp import GitHubMCP
from .docker_mcp import DockerMCP
from .fastmcp_mcp import FastMCPMCPServer
from .bayes_mcp import BayesMCPServer
from .darwin_mcp import DarwinMCPServer

__version__ = "1.0.0"
__all__ = [
    "GitHubMCP",
    "DockerMCP",
    "FastMCPMCPServer",
    "BayesMCPServer",
    "DarwinMCPServer",
]

# MCP Server Registry
MCP_SERVERS = {
    "github-mcp": GitHubMCP,
    "docker-mcp": DockerMCP,
    "fastmcp-mcp": FastMCPMCPServer,
    "bayes-mcp": BayesMCPServer,
    "darwin-mcp": DarwinMCPServer,
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
