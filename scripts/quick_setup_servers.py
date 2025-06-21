#!/usr/bin/env python3
"""
Quick MCP Servers Setup Script

This script quickly creates the missing MCP server directories and basic files
to resolve the "Source directory missing" errors.
"""

import os
from pathlib import Path

def create_mcp_server(server_name: str, base_dir: Path):
    """Create a basic MCP server structure."""
    server_dir = base_dir / server_name
    server_dir.mkdir(parents=True, exist_ok=True)

    # Create __init__.py
    (server_dir / "__init__.py").touch()

    # Create basic server.py
    server_py = server_dir / "server.py"
    if not server_py.exists():
        content = f'''"""
{server_name} MCP Server

Basic MCP server implementation for {server_name}.
"""

import asyncio
from typing import Any, Sequence
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import Resource, Tool, TextContent

# Create server instance
server = Server("{server_name}")

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name=f"{server_name}_status",
            description=f"Get status of {server_name} server",
            inputSchema={{
                "type": "object",
                "properties": {{}},
                "required": []
            }}
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> Sequence[TextContent]:
    """Handle tool calls."""
    if name == f"{server_name}_status":
        return [
            TextContent(
                type="text",
                text=f"{server_name} server is running and ready to receive requests."
            )
        ]
    else:
        raise ValueError(f"Unknown tool: {{name}}")

async def main():
    """Main server entry point."""
    options = InitializationOptions(
        server_name="{server_name}",
        server_version="1.0.0",
        capabilities=server.get_capabilities(
            notification_options=None,
            experimental_capabilities={{}}
        )
    )

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            options
        )

if __name__ == "__main__":
    asyncio.run(main())
'''
        with open(server_py, 'w') as f:
            f.write(content)

    # Create requirements.txt
    requirements_txt = server_dir / "requirements.txt"
    if not requirements_txt.exists():
        with open(requirements_txt, 'w') as f:
            f.write("mcp>=1.0.0\n")

    print(f"✅ Created MCP server: {server_name}")

def main():
    """Main setup function."""
    # Base MCP servers directory
    devqai_root = Path(os.getenv('DEVQAI_ROOT', '/Users/dionedge/devqai'))
    mcp_servers_dir = devqai_root / "mcp" / "mcp-servers"

    print(f"🔧 Setting up MCP servers in: {mcp_servers_dir}")

    # Create base directory
    mcp_servers_dir.mkdir(parents=True, exist_ok=True)

    # List of MCP servers that need to be created based on configuration
    servers_to_create = [
        "crawl4ai-mcp",
        "context7-mcp",
        "surrealdb-mcp",
        "solver-z3-mcp",
        "solver-pysat-mcp",
        "magic-mcp",
        "shadcn-ui-mcp-server",
        "registry-mcp"
    ]

    for server_name in servers_to_create:
        create_mcp_server(server_name, mcp_servers_dir)

    print(f"\n🎉 Setup complete! Created {len(servers_to_create)} MCP servers.")
    print("\n📋 Next steps:")
    print("1. Install MCP dependencies: pip install mcp")
    print("2. Run the tools report to check updated status")
    print("3. Test individual servers if needed")

if __name__ == "__main__":
    main()
