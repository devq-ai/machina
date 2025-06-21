"""
MCP (Model Context Protocol) Package

This package provides MCP protocol support for the Machina Registry Service,
exposing TaskMaster AI functionality and service registry capabilities as
MCP tools for integration with AI development environments.

Components:
- handlers: MCP tool handlers and protocol implementation
- tools: Individual MCP tool definitions
- server: MCP server implementation
- schemas: MCP-specific data schemas and validation
"""

from .handlers import MCPHandlers
from .server import MCPServer
from .tools import get_mcp_tools

__all__ = [
    "MCPHandlers",
    "MCPServer",
    "get_mcp_tools"
]
