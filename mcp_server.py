#!/usr/bin/env python3
"""
Standalone MCP Server for Machina Registry Service

This script provides a standalone MCP (Model Context Protocol) server that can
be run independently for integration with AI development environments like Zed IDE.
It exposes TaskMaster AI functionality and registry services as MCP tools.

Usage:
    python mcp_server.py

Environment Variables:
    PYTHONPATH: Should include the src directory
    MCP_DEBUG: Enable debug logging (default: false)
    MACHINA_CONFIG_PATH: Path to configuration file (optional)

Integration:
    Add to Zed IDE .zed/settings.json:
    {
        "mcpServers": {
            "machina-registry": {
                "command": "python",
                "args": ["/path/to/machina/mcp_server.py"],
                "env": {
                    "PYTHONPATH": "/path/to/machina/src"
                }
            }
        }
    }
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Optional

# Add src to Python path for imports
current_dir = Path(__file__).parent
src_path = current_dir / "src"
sys.path.insert(0, str(src_path))

try:
    import logfire
    from mcp.server.stdio import stdio_server

    # Import our MCP server implementation
    from app.mcp.server import MCPServer
    from app.core.config import Settings

except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Make sure you have installed all dependencies:")
    print("pip install -r requirements.txt")
    sys.exit(1)


def setup_logging():
    """Set up logging configuration for MCP server."""
    log_level = logging.DEBUG if os.getenv("MCP_DEBUG", "false").lower() == "true" else logging.INFO

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stderr)  # MCP uses stderr for logs
        ]
    )

    # Reduce noise from some libraries
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def load_settings() -> Settings:
    """Load application settings for MCP server."""
    try:
        # Load configuration
        config_path = os.getenv("MACHINA_CONFIG_PATH")
        if config_path and Path(config_path).exists():
            # Could load from custom config file if needed
            pass

        settings = Settings()

        # Configure minimal Logfire for MCP server
        if settings.LOGFIRE_TOKEN:
            try:
                logfire.configure(**settings.logfire_config)
                logfire.info("MCP Server starting with Logfire observability")
            except Exception as e:
                logging.warning(f"Logfire configuration failed: {e}")

        return settings

    except Exception as e:
        logging.error(f"Failed to load settings: {e}")
        # Return minimal settings for basic operation
        return Settings(
            MCP_TOOLS_ENABLED=True,
            DEBUG=os.getenv("MCP_DEBUG", "false").lower() == "true"
        )


async def check_dependencies():
    """Check if required services are available."""
    try:
        # Import and test cache service
        from app.services.cache_service import get_cache_service
        cache_service = await get_cache_service()

        # Test Redis connection
        await cache_service.health_check()
        logging.info("Redis connection verified")

        return True

    except Exception as e:
        logging.warning(f"Dependency check failed: {e}")
        logging.warning("MCP server will run with limited functionality")
        return False


async def run_mcp_server():
    """Run the MCP server with stdio transport."""
    try:
        # Load settings
        settings = load_settings()

        if not settings.MCP_TOOLS_ENABLED:
            logging.error("MCP tools are disabled in configuration")
            return

        # Check dependencies (non-blocking)
        deps_ok = await check_dependencies()
        if not deps_ok:
            logging.warning("Some dependencies unavailable, continuing with reduced functionality")

        # Create and run MCP server
        mcp_server = MCPServer()

        logging.info("Starting Machina Registry MCP Server")
        logging.info(f"Server name: {settings.MCP_SERVER_NAME}")
        logging.info(f"Version: {settings.MCP_SERVER_VERSION}")
        logging.info("Available tools: get_tasks, create_task, update_task_status, analyze_task_complexity, and more")

        # Run server with stdio transport
        async with stdio_server() as (read_stream, write_stream):
            await mcp_server.server.run(
                read_stream,
                write_stream,
                mcp_server.server.create_initialization_options()
            )

    except KeyboardInterrupt:
        logging.info("MCP server shutdown requested by user")
    except Exception as e:
        logging.error(f"MCP server failed: {e}")
        if settings.DEBUG:
            import traceback
            logging.error(traceback.format_exc())
        raise


def main():
    """Main entry point for standalone MCP server."""
    # Set up logging first
    setup_logging()

    try:
        # Run the async MCP server
        asyncio.run(run_mcp_server())

    except KeyboardInterrupt:
        logging.info("MCP server stopped")
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
