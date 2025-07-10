"""
FastMCP - Fast Model Context Protocol Framework
A high-performance MCP server framework with built-in observability and tool management.
"""

from .core import FastMCP
from .registry import MCPRegistry
from .health import HealthMonitor
from .tools import tool, MCPTool

__version__ = "1.0.0"
__all__ = ["FastMCP", "MCPRegistry", "HealthMonitor", "tool", "MCPTool"]
