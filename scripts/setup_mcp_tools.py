#!/usr/bin/env python3
"""
MCP Tools Setup Script

This script sets up and configures all MCP tools based on the tools.md source of truth.
It handles different tool types: anthropic_core_tool, zed-mcp_server, and mcp_server.

Usage:
    python scripts/setup_mcp_tools.py
    python scripts/setup_mcp_tools.py --check-only
    python scripts/setup_mcp_tools.py --setup-missing
    python scripts/setup_mcp_tools.py --start-servers
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
import shutil
import requests


class MCPToolsSetup:
    """Setup and manage MCP tools based on tools.md configuration."""

    def __init__(self):
        self.project_root = Path.cwd()
        self.devqai_root = Path(os.getenv('DEVQAI_ROOT', '/Users/dionedge/devqai'))
        self.tools_dir = self.project_root / "tools"
        self.tools_md_path = self.tools_dir / "tools.md"

        # Configuration paths
        self.zed_config = self.project_root / ".zed" / "settings.json"
        self.claude_config = self.project_root / ".claude" / "settings.json"

        # MCP servers directory
        self.mcp_servers_dir = self.devqai_root / "mcp" / "mcp-servers"

        # Tool installation status
        self.installation_log = []
        self.errors = []

    def log(self, message: str, level: str = "INFO"):
        """Log a message with timestamp."""
        timestamp = time.strftime("%H:%M:%S")
        formatted_msg = f"[{timestamp}] {level}: {message}"
        print(formatted_msg)
        self.installation_log.append(formatted_msg)

    def error(self, message: str):
        """Log an error message."""
        self.log(message, "ERROR")
        self.errors.append(message)

    def run_command(self, cmd: List[str], cwd: Optional[Path] = None, env: Optional[Dict] = None) -> Tuple[bool, str]:
        """Run a command and return success status and output."""
        try:
            env_vars = os.environ.copy()
            if env:
                env_vars.update(env)

            result = subprocess.run(
                cmd,
                cwd=cwd,
                env=env_vars,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                return True, result.stdout.strip()
            else:
                return False, result.stderr.strip()

        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except Exception as e:
            return False, str(e)

    def load_tools_md(self) -> Dict:
        """Load and parse tools.md file."""
        if not self.tools_md_path.exists():
            self.error(f"tools.md not found at {self.tools_md_path}")
            return {}

        tools_data = {}
        current_tool = None
        current_data = {}

        try:
            with open(self.tools_md_path, 'r') as f:
                for line in f:
                    line = line.strip()

                    if not line or line.startswith('required_tools:') or line.startswith('rule_'):
                        if current_tool and current_data:
                            # Handle duplicates by appending type
                            tool_key = current_tool
                            if current_tool in tools_data:
                                tool_type = current_data.get('type', 'unknown')
                                tool_key = f"{current_tool}_{tool_type}"
                            tools_data[tool_key] = current_data
                            current_tool = None
                            current_data = {}
                        continue

                    if line.startswith('tool: '):
                        if current_tool and current_data:
                            tool_key = current_tool
                            if current_tool in tools_data:
                                tool_type = current_data.get('type', 'unknown')
                                tool_key = f"{current_tool}_{tool_type}"
                            tools_data[tool_key] = current_data

                        current_tool = line[6:].strip()
                        current_data = {}
                        continue

                    if current_tool and ':' in line:
                        key, value = line.split(':', 1)
                        current_data[key.strip()] = value.strip()

                # Handle last tool
                if current_tool and current_data:
                    tool_key = current_tool
                    if current_tool in tools_data:
                        tool_type = current_data.get('type', 'unknown')
                        tool_key = f"{current_tool}_{tool_type}"
                    tools_data[tool_key] = current_data

        except Exception as e:
            self.error(f"Error parsing tools.md: {e}")
            return {}

        return tools_data

    def load_config(self, config_path: Path) -> Dict:
        """Load JSON configuration file."""
        if not config_path.exists():
            return {}

        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.error(f"Error loading {config_path}: {e}")
            return {}

    def check_npm_package(self, package_name: str) -> bool:
        """Check if NPM package is available."""
        success, _ = self.run_command(['npx', package_name, '--version'])
        return success

    def check_python_module(self, module_name: str, cwd: Optional[Path] = None) -> bool:
        """Check if Python module can be imported."""
        env = {'PYTHONPATH': f"{self.devqai_root}:{os.environ.get('PYTHONPATH', '')}"}
        success, _ = self.run_command(['python', '-c', f'import {module_name}'], cwd=cwd, env=env)
        return success

    def install_npm_package(self, package_name: str) -> bool:
        """Install NPM package globally."""
        self.log(f"Installing NPM package: {package_name}")
        success, output = self.run_command(['npm', 'install', '-g', package_name])
        if success:
            self.log(f"Successfully installed {package_name}")
        else:
            self.error(f"Failed to install {package_name}: {output}")
        return success

    def setup_python_mcp_server(self, tool_name: str, server_dir: Path) -> bool:
        """Setup a Python MCP server directory and dependencies."""
        self.log(f"Setting up Python MCP server: {tool_name}")

        if not server_dir.exists():
            self.log(f"Creating MCP server directory: {server_dir}")
            server_dir.mkdir(parents=True, exist_ok=True)

            # Create basic server structure
            (server_dir / "__init__.py").touch()

            # Create basic server.py if it doesn't exist
            server_py = server_dir / "server.py"
            if not server_py.exists():
                server_content = f'''"""
{tool_name} MCP Server

Basic MCP server implementation for {tool_name}.
"""

from typing import Any, Sequence
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import Resource, Tool


class {tool_name.title().replace('-', '')}Server:
    """MCP Server for {tool_name}."""

    def __init__(self):
        self.server = Server("{tool_name}")
        self.setup_handlers()

    def setup_handlers(self):
        """Setup MCP server handlers."""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List available tools."""
            return [
                Tool(
                    name="{tool_name}_example",
                    description=f"Example tool for {tool_name}",
                    inputSchema={{
                        "type": "object",
                        "properties": {{
                            "input": {{"type": "string", "description": "Input parameter"}}
                        }},
                        "required": ["input"]
                    }}
                )
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[Any]:
            """Handle tool calls."""
            if name == "{tool_name}_example":
                return [f"Example response from {tool_name}: {{arguments.get('input', 'no input')}}"]
            else:
                raise ValueError(f"Unknown tool: {{name}}")


async def main():
    """Main server entry point."""
    server = {tool_name.title().replace('-', '')}Server()

    async with stdio_server() as (read_stream, write_stream):
        await server.server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="{tool_name}",
                server_version="1.0.0",
                capabilities=server.server.get_capabilities(
                    notification_options=None,
                    experimental_capabilities={{}}
                )
            )
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
'''
                with open(server_py, 'w') as f:
                    f.write(server_content)

            # Create requirements.txt
            requirements_txt = server_dir / "requirements.txt"
            if not requirements_txt.exists():
                with open(requirements_txt, 'w') as f:
                    f.write("mcp>=1.0.0\n")

        # Try to install dependencies
        if (server_dir / "requirements.txt").exists():
            success, output = self.run_command(['pip', 'install', '-r', 'requirements.txt'], cwd=server_dir)
            if not success:
                self.error(f"Failed to install requirements for {tool_name}: {output}")
                return False

        return True

    def setup_anthropic_tools(self, tools: List[Dict]) -> Dict[str, bool]:
        """Setup Anthropic core tools (these are built-in to Claude Code)."""
        results = {}

        for tool_data in tools:
            tool_name = tool_data['name']
            self.log(f"Anthropic core tool '{tool_name}' is built-in to Claude Code")
            results[tool_name] = True  # Always available in Claude Code

        return results

    def setup_zed_mcp_servers(self, tools: List[Dict]) -> Dict[str, bool]:
        """Setup Zed MCP servers."""
        results = {}

        for tool_data in tools:
            tool_name = tool_data['name']
            self.log(f"Setting up Zed MCP server: {tool_name}")

            # These are typically installed via Zed's extension system or NPM
            # For now, we'll mark them as requiring manual setup
            self.log(f"Zed MCP server '{tool_name}' requires manual installation via Zed extension system")
            results[tool_name] = False  # Needs manual setup

        return results

    def setup_mcp_servers(self, tools: List[Dict]) -> Dict[str, bool]:
        """Setup regular MCP servers."""
        results = {}

        for tool_data in tools:
            tool_name = tool_data['name']
            self.log(f"Setting up MCP server: {tool_name}")

            # Check if it's configured in Zed or Claude
            zed_config = self.load_config(self.zed_config)
            claude_config = self.load_config(self.claude_config)

            zed_servers = zed_config.get('mcpServers', {})
            claude_servers = claude_config.get('mcpServers', {})

            configured = tool_name in zed_servers or tool_name in claude_servers

            if configured:
                # Check if the server exists and works
                config = zed_servers.get(tool_name) or claude_servers.get(tool_name)
                if config:
                    success = self.test_mcp_server(tool_name, config)
                    if not success:
                        # Try to set it up
                        success = self.setup_missing_mcp_server(tool_name, config)
                    results[tool_name] = success
                else:
                    results[tool_name] = False
            else:
                self.log(f"MCP server '{tool_name}' not configured in Zed or Claude settings")
                results[tool_name] = False

        return results

    def setup_missing_mcp_server(self, tool_name: str, config: Dict) -> bool:
        """Setup a missing MCP server based on its configuration."""
        command = config.get('command', '')
        cwd = config.get('cwd', '')

        if command == 'python' and cwd:
            # Python-based MCP server
            server_dir = Path(cwd)
            return self.setup_python_mcp_server(tool_name, server_dir)

        elif command == 'npx':
            # NPM-based MCP server
            args = config.get('args', [])
            if args:
                package_name = None
                for arg in args:
                    if not arg.startswith('-') and '/' in arg:
                        package_name = arg
                        break

                if package_name:
                    return self.install_npm_package(package_name)

        return False

    def test_mcp_server(self, tool_name: str, config: Dict) -> bool:
        """Test if an MCP server is working."""
        command = config.get('command', '')
        args = config.get('args', [])
        cwd = config.get('cwd')
        env = config.get('env', {})

        # Build full command
        full_cmd = [command] + args

        # For testing, we'll try a simple version check or module import
        if command == 'python' and len(args) >= 2 and args[0] == '-m':
            module_name = args[1]
            return self.check_python_module(module_name, Path(cwd) if cwd else None)

        elif command == 'npx' and args:
            package_name = args[-1]
            return self.check_npm_package(package_name)

        return False

    def get_required_tools_by_type(self) -> Dict[str, List[Dict]]:
        """Get required tools categorized by type."""
        tools_data = self.load_tools_md()

        categorized = {
            'anthropic_core_tool': [],
            'zed-mcp_server': [],
            'mcp_server': []
        }

        for tool_key, tool_data in tools_data.items():
            if tool_data.get('required', 'false').lower() == 'true':
                tool_type = tool_data.get('type', 'unknown')

                # Extract original tool name
                if '_anthropic_core_tool' in tool_key:
                    tool_name = tool_key.replace('_anthropic_core_tool', '')
                elif '_pydantic-ai_core_tool' in tool_key:
                    continue  # Skip pydantic-ai tools as they're not required for this setup
                elif '_zed-mcp_server' in tool_key:
                    tool_name = tool_key.replace('_zed-mcp_server', '')
                elif '_mcp_server' in tool_key:
                    tool_name = tool_key.replace('_mcp_server', '')
                else:
                    tool_name = tool_key

                tool_info = {
                    'name': tool_name,
                    'type': tool_type,
                    'data': tool_data
                }

                if tool_type in categorized:
                    categorized[tool_type].append(tool_info)

        return categorized

    def check_all_tools(self) -> Dict[str, Dict[str, bool]]:
        """Check status of all required tools."""
        self.log("Checking status of all required tools...")

        categorized_tools = self.get_required_tools_by_type()
        results = {}

        # Check Anthropic core tools
        if categorized_tools['anthropic_core_tool']:
            self.log("Checking Anthropic core tools...")
            results['anthropic_core_tool'] = self.setup_anthropic_tools(categorized_tools['anthropic_core_tool'])

        # Check Zed MCP servers
        if categorized_tools['zed-mcp_server']:
            self.log("Checking Zed MCP servers...")
            results['zed-mcp_server'] = self.setup_zed_mcp_servers(categorized_tools['zed-mcp_server'])

        # Check regular MCP servers
        if categorized_tools['mcp_server']:
            self.log("Checking MCP servers...")
            results['mcp_server'] = self.setup_mcp_servers(categorized_tools['mcp_server'])

        return results

    def setup_missing_tools(self) -> bool:
        """Setup all missing required tools."""
        self.log("Setting up missing required tools...")

        results = self.check_all_tools()
        success_count = 0
        total_count = 0

        for tool_type, tool_results in results.items():
            for tool_name, is_working in tool_results.items():
                total_count += 1
                if is_working:
                    success_count += 1
                else:
                    self.log(f"Tool '{tool_name}' ({tool_type}) needs attention")

        self.log(f"Setup complete: {success_count}/{total_count} tools working")
        return success_count == total_count

    def start_mcp_servers(self) -> Dict[str, bool]:
        """Start all configured MCP servers."""
        self.log("Starting MCP servers...")

        # This would start the actual MCP server processes
        # For now, we'll just verify they can be started
        zed_config = self.load_config(self.zed_config)
        claude_config = self.load_config(self.claude_config)

        all_servers = {}
        all_servers.update(zed_config.get('mcpServers', {}))
        all_servers.update(claude_config.get('mcpServers', {}))

        results = {}
        for server_name, config in all_servers.items():
            self.log(f"Testing server startup: {server_name}")
            results[server_name] = self.test_mcp_server(server_name, config)

        return results

    def generate_report(self) -> str:
        """Generate a setup report."""
        report = []
        report.append("# MCP Tools Setup Report")
        report.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        # Add installation log
        if self.installation_log:
            report.append("## Installation Log")
            for log_entry in self.installation_log:
                report.append(f"- {log_entry}")
            report.append("")

        # Add errors if any
        if self.errors:
            report.append("## Errors")
            for error in self.errors:
                report.append(f"- ❌ {error}")
            report.append("")

        # Add recommendations
        report.append("## Next Steps")
        report.append("1. Review any errors above")
        report.append("2. Manually install Zed MCP servers via Zed extension system")
        report.append("3. Verify environment variables are set correctly")
        report.append("4. Test individual MCP servers")
        report.append("5. Run the tools report to verify online status")

        return "\n".join(report)

    def run(self, check_only: bool = False, setup_missing: bool = False, start_servers: bool = False):
        """Main execution method."""
        self.log("Starting MCP Tools Setup...")

        if check_only:
            results = self.check_all_tools()
            self.log("Check complete - see results above")

        elif setup_missing:
            success = self.setup_missing_tools()
            if success:
                self.log("All tools setup successfully!")
            else:
                self.error("Some tools failed to setup - see errors above")

        elif start_servers:
            results = self.start_mcp_servers()
            working_count = sum(1 for working in results.values() if working)
            total_count = len(results)
            self.log(f"Server startup test: {working_count}/{total_count} servers working")

        else:
            # Default: check and setup
            self.log("Running comprehensive setup...")
            self.check_all_tools()
            self.setup_missing_tools()

        # Generate and save report
        report = self.generate_report()
        report_path = self.tools_dir / "setup_report.md"
        with open(report_path, 'w') as f:
            f.write(report)

        self.log(f"Setup report saved to: {report_path}")

        if self.errors:
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='Setup and configure MCP tools based on tools.md',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/setup_mcp_tools.py                    # Check and setup all tools
  python scripts/setup_mcp_tools.py --check-only       # Only check tool status
  python scripts/setup_mcp_tools.py --setup-missing    # Setup missing tools
  python scripts/setup_mcp_tools.py --start-servers    # Test server startup
        """
    )

    parser.add_argument('--check-only', action='store_true', help='Only check tool status')
    parser.add_argument('--setup-missing', action='store_true', help='Setup missing tools')
    parser.add_argument('--start-servers', action='store_true', help='Test MCP server startup')

    args = parser.parse_args()

    setup = MCPToolsSetup()
    setup.run(
        check_only=args.check_only,
        setup_missing=args.setup_missing,
        start_servers=args.start_servers
    )


if __name__ == '__main__':
    main()
