"""
API Package for Machina Registry Service

This package contains both HTTP REST API and MCP protocol handlers
for the Machina Registry Service, providing dual protocol support
for maximum compatibility and integration flexibility.

Modules:
- http/: FastAPI REST API routes and controllers
- mcp/: Model Context Protocol handlers and tools
"""

from .http import router as http_router
from .mcp import handlers as mcp_handlers

__all__ = ["http_router", "mcp_handlers"]
