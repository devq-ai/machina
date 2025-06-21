"""
MCP API Package for Machina Registry Service

This package contains the Model Context Protocol (MCP) implementation for the
Machina Registry Service, providing MCP server functionality for AI-powered
development tools and service discovery.

Components:
- handlers/: MCP tool handlers and protocol implementations
"""

from .handlers import register_handlers

__all__ = ["register_handlers"]
