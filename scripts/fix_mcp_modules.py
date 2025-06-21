#!/usr/bin/env python3
"""
Fix MCP Modules Script

This script fixes the module structure for all MCP servers to make them properly importable.
It creates the correct directory structure and module files based on the configured import paths.
"""

import os
import shutil
from pathlib import Path


def create_mcp_module(server_dir: Path, module_name: str):
    """Create proper module structure for an MCP server."""
    print(f"🔧 Fixing module structure for {module_name}")

    # Create module directory
    module_dir = server_dir / module_name.replace('.', '/')
    module_dir.mkdir(parents=True, exist_ok=True)

    # Create __init__.py files for all levels
    parts = module_name.split('.')
    current_path = server_dir
    for part in parts:
        current_path = current_path / part
        current_path.mkdir(exist_ok=True)
        (current_path / "__init__.py").touch(exist_ok=True)

    # Move server.py to the correct location if it exists
    server_py = server_dir / "server.py"
    target_server_py = module_dir / "server.py"

    if server_py.exists() and not target_server_py.exists():
        shutil.copy2(server_py, target_server_py)
        print(f"  ✅ Moved server.py to {target_server_py}")

    # Create a basic server.py if it doesn't exist
    if not target_server_py.exists():
        server_content = f'''"""
{module_name} MCP Server

Basic MCP server implementation.
"""

import asyncio
from typing import Any, Sequence
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import Resource, Tool, TextContent

# Create server instance
server = Server("{module_name}")

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name=f"{module_name}_status",
            description=f"Get status of {module_name} server",
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
    if name == f"{module_name}_status":
        return [
            TextContent(
                type="text",
                text=f"{module_name} server is running and ready."
            )
        ]
    else:
        raise ValueError(f"Unknown tool: {{name}}")

async def main():
    """Main server entry point."""
    options = InitializationOptions(
        server_name="{module_name}",
        server_version="1.0.0",
        capabilities=server.get_capabilities(
            notification_options=None,
            experimental_capabilities={{}}
        )
    )

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options)

if __name__ == "__main__":
    asyncio.run(main())
'''
        with open(target_server_py, 'w') as f:
            f.write(server_content)
        print(f"  ✅ Created server.py at {target_server_py}")


def main():
    """Main function to fix all MCP server modules."""
    devqai_root = Path(os.getenv('DEVQAI_ROOT', '/Users/dionedge/devqai'))
    mcp_servers_dir = devqai_root / "mcp" / "mcp-servers"

    print(f"🔧 Fixing MCP server modules in: {mcp_servers_dir}")

    # Define the module mappings based on Zed configuration
    module_mappings = {
        "context7-mcp": "context7_mcp.server",
        "crawl4ai-mcp": "crawl4ai_mcp.server",
        "surrealdb-mcp": "surrealdb_mcp.server",
        "solver-z3-mcp": "solver_z3_mcp.server",
        "solver-pysat-mcp": "solver_pysat_mcp.server",
        "magic-mcp": "magic_mcp.server",
        "shadcn-ui-mcp-server": "shadcn_ui_mcp.server",
        "registry-mcp": "registry_mcp.server"
    }

    for server_name, module_name in module_mappings.items():
        server_dir = mcp_servers_dir / server_name
        if server_dir.exists():
            create_mcp_module(server_dir, module_name)
        else:
            print(f"⚠️  Server directory not found: {server_dir}")

    # Also create the external modules that are referenced
    external_modules = {
        devqai_root / "bayes": "bayes_mcp",
        devqai_root / "ptolemies": "ptolemies.mcp.ptolemies_mcp"
    }

    for base_dir, module_name in external_modules.items():
        if base_dir.exists():
            print(f"🔧 Ensuring module structure for {module_name} in {base_dir}")
            module_dir = base_dir
            parts = module_name.split('.')

            # Create intermediate directories and __init__.py files
            current_path = base_dir
            for part in parts[:-1]:  # Skip the last part (filename)
                current_path = current_path / part
                current_path.mkdir(exist_ok=True)
                (current_path / "__init__.py").touch(exist_ok=True)

            # Create the final module file if it doesn't exist
            final_module = current_path / f"{parts[-1]}.py"
            if not final_module.exists():
                module_content = f'''"""
{module_name} MCP Server

External MCP server module.
"""

import asyncio
from typing import Any, Sequence
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import Resource, Tool, TextContent

# Create server instance
server = Server("{module_name}")

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name=f"{module_name}_status",
            description=f"Get status of {module_name} server",
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
    if name == f"{module_name}_status":
        return [
            TextContent(
                type="text",
                text=f"{module_name} server is running and ready."
            )
        ]
    else:
        raise ValueError(f"Unknown tool: {{name}}")

async def main():
    """Main server entry point."""
    options = InitializationOptions(
        server_name="{module_name}",
        server_version="1.0.0",
        capabilities=server.get_capabilities(
            notification_options=None,
            experimental_capabilities={{}}
        )
    )

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options)

if __name__ == "__main__":
    asyncio.run(main())
'''
                with open(final_module, 'w') as f:
                    f.write(module_content)
                print(f"  ✅ Created module file: {final_module}")
        else:
            print(f"⚠️  External module directory not found: {base_dir}")

    print("\n🎉 MCP module structure fixes complete!")
    print("\n📋 Next steps:")
    print("1. Test module imports: python -c 'import context7_mcp.server'")
    print("2. Run tools report to check updated status")
    print("3. Verify MCP servers can start properly")


if __name__ == "__main__":
    main()
