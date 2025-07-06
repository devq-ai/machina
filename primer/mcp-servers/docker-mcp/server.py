"""
Docker MCP Server - Main Entry Point

This module serves as the main entry point for the docker-mcp server.
It imports and runs the full implementation from the docker_mcp package.
"""

from docker_mcp.server.server import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main())