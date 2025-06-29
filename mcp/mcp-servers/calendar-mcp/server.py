"""
Calendar MCP Server - Main Entry Point

This module serves as the main entry point for the calendar-mcp server.
It imports and runs the full implementation from the calendar_mcp package.
"""

from calendar_mcp.server.server import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main())