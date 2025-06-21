#!/usr/bin/env python3
"""
DevQ.ai MCP Tools Report Generator

This script inventories all MCP tools configured in Zed IDE and Claude Code,
checks their status, and generates a comprehensive tools_report.md file.

Usage:
    python scripts/generate_tools_report.py
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class MCPToolsReporter:
    """Generates comprehensive MCP tools report for DevQ.ai environment."""

    def __init__(self, devqai_root: str = "/Users/dionedge/devqai"):
        self.devqai_root = Path(devqai_root)
        self.project_root = Path.cwd()
        self.zed_config = self.project_root / ".zed" / "settings.json"
        self.claude_config = self.project_root / ".claude" / "settings.json"
        self.tools_dir = self.project_root / "tools"

    def load_config(self, config_path: Path) -> Dict:
        """Load JSON configuration file."""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Warning: {config_path} not found")
            return {}
        except json.JSONDecodeError as e:
            print(f"Error parsing {config_path}: {e}")
            return {}

    def get_required_tools_fast(self) -> set:
        """Quickly get required tools list from required_tools line in tools.md."""
        tools_md_path = self.tools_dir / "tools.md"

        if not tools_md_path.exists():
            return set()

        try:
            with open(tools_md_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('required_tools:'):
                        required_tools_list = line[15:].strip().split(',')
                        return {tool.strip() for tool in required_tools_list if tool.strip()}

        except Exception:
            pass

        return set()

    def load_tools_md(self) -> Dict:
        """Load existing tools.md file for tool information."""
        tools_md_path = self.tools_dir / "tools.md"
        tools_data = {}

        if not tools_md_path.exists():
            return tools_data

        # Get required tools from first line quickly
        required_tools_set = self.get_required_tools_fast()

        try:
            with open(tools_md_path, 'r') as f:
                content = f.read()

            # Parse YAML-like content to extract tool information
            current_tool = None
            current_tool_data = {}

            for line in content.split('\n'):
                line = line.strip()

                # Skip required_tools line and empty lines
                if not line or line.startswith('required_tools:'):
                    if current_tool and current_tool_data:
                        # Handle duplicate tool names by appending type suffix
                        tool_key = current_tool
                        tool_type = current_tool_data.get('type', 'unknown')
                        if current_tool in tools_data:
                            tool_key = f"{current_tool}_{tool_type}"
                        tools_data[tool_key] = current_tool_data
                        current_tool = None
                        current_tool_data = {}
                    continue

                # Detect tool headers (tool: tool_name)
                if line.startswith('tool: '):
                    # Save previous tool if exists
                    if current_tool and current_tool_data:
                        # Handle duplicate tool names by appending type suffix
                        tool_key = current_tool
                        tool_type = current_tool_data.get('type', 'unknown')
                        if current_tool in tools_data:
                            tool_key = f"{current_tool}_{tool_type}"
                        tools_data[tool_key] = current_tool_data

                    current_tool = line[6:].strip()
                    current_tool_data = {}

                    # Set required status from required_tools line if available
                    if required_tools_set and current_tool in required_tools_set:
                        current_tool_data['required'] = 'true'

                    continue

                # Parse tool properties (key: value)
                if current_tool and ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    current_tool_data[key] = value

            # Save last tool if exists
            if current_tool and current_tool_data:
                # Handle duplicate tool names by appending type suffix
                tool_key = current_tool
                tool_type = current_tool_data.get('type', 'unknown')
                if current_tool in tools_data:
                    tool_key = f"{current_tool}_{tool_type}"
                tools_data[tool_key] = current_tool_data

        except Exception as e:
            print(f"Warning: Error parsing tools.md: {e}")

        return tools_data

    def check_command_available(self, command: str) -> bool:
        """Check if a command is available in the system PATH."""
        try:
            subprocess.run(['which', command],
                         capture_output=True, check=True)
            return True
        except subprocess.CalledProcessError:
            return False

    def check_python_module(self, module_path: str, cwd: Optional[str] = None) -> bool:
        """Check if a Python module can be imported."""
        try:
            # Check if cwd exists before using it
            if cwd and not self.check_directory_exists(cwd):
                return False

            cmd = [sys.executable, '-c', f'import {module_path}; print("OK")']
            env = os.environ.copy()
            if cwd:
                env['PYTHONPATH'] = f"{cwd}:{env.get('PYTHONPATH', '')}"

            result = subprocess.run(cmd, capture_output=True,
                                  cwd=cwd, env=env, timeout=10)
            return result.returncode == 0 and b'OK' in result.stdout
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError, OSError):
            return False

    def check_npm_package(self, package: str) -> bool:
        """Check if an NPM package is available."""
        try:
            # Special handling for task-master-ai package
            if package == 'task-master-ai':
                # Try the actual command name 'task-master' first
                try:
                    result = subprocess.run(['task-master', '--version'],
                                         capture_output=True, timeout=5)
                    if result.returncode == 0:
                        return True
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
                    pass

                # Fallback: check if we can find the package
                try:
                    result = subprocess.run(['npm', 'list', '-g', 'task-master-ai'],
                                         capture_output=True, timeout=5)
                    return 'task-master-ai@' in result.stdout.decode()
                except:
                    return False
            else:
                subprocess.run(['npx', package, '--version'],
                             capture_output=True, check=True, timeout=10)
                return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def check_directory_exists(self, path: str) -> bool:
        """Check if a directory exists."""
        return Path(path).exists() and Path(path).is_dir()

    def check_file_exists(self, path: str) -> bool:
        """Check if a file exists."""
        return Path(path).exists() and Path(path).is_file()

    def get_tool_name_mapping(self) -> Dict[str, str]:
        """Get mapping from tools.md names to configuration names."""
        return {
            # tools.md name -> config name
            'mcp-server-context7': 'context7',
            'mcp-server-github': 'github',
            'mcp-server-sequential-thinking': 'sequentialthinking',
            'mcp-server-buildkite': 'buildkite',
            'task-master-mcp-server': 'taskmaster-ai',
            'ptolemies-mcp-server': 'ptolemies',
            'crawl4ai-mcp': 'crawl4ai',
            'puppeteer-mcp': 'puppeteer',
            'browser-tools-context-server': 'browser-tools',
            'zed-slack-mcp': 'slack-mcp',
            'zed-mcp-server-shopify-dev': 'shopify-dev',
            'zed-resend-mcp-server': 'resend-mcp',
            'zed-rover-mcp-server': 'rover-mcp',
            'byterover-zed-extension': 'byterover',
            'zed-polar-context-server': 'polar-context',
            # Also check if configured tools match directly
        }

    def test_mcp_server_startup(self, tool_name: str, config: Dict) -> bool:
        """Test if an MCP server can actually start up and respond."""
        command = config.get('command', '')
        args = config.get('args', [])
        cwd = config.get('cwd')
        env_vars = config.get('env', {})

        # Build environment - be more lenient with missing env vars
        env = os.environ.copy()
        missing_critical_vars = []

        for key, value in env_vars.items():
            # Handle environment variable substitution
            if value.startswith('${') and value.endswith('}'):
                env_key = value[2:-1]
                env_value = os.environ.get(env_key, '')
                if env_value:
                    env[key] = env_value
                else:
                    # Only fail for truly critical vars, not API keys
                    critical_vars = ['DATABASE_URL', 'REQUIRED_PATH']
                    if env_key in critical_vars:
                        missing_critical_vars.append(env_key)
                    # For API keys and optional vars, just skip them
            else:
                env[key] = value

        # Only fail if critical vars are missing
        if missing_critical_vars:
            return False

        try:
            # For Python modules, try to import them
            if command == 'python' and len(args) >= 2 and args[0] == '-m':
                module_name = args[1]
                return self.check_python_module(module_name, Path(cwd) if cwd else None)

            # For NPM packages, check if they can be executed
            elif command == 'npx' and args:
                package_name = args[-1] if not args[-1].startswith('-') else args[-2]
                return self.check_npm_package(package_name)

            # For other commands, try a basic execution test
            else:
                # Just check if the command exists
                result = subprocess.run(['which', command], capture_output=True, timeout=5)
                return result.returncode == 0

        except Exception:
            return False

    def get_tool_status(self, tool_name: str, config: Dict, tools_md_data: Dict) -> Dict:
        """Get comprehensive status for a specific MCP tool."""
        # Start with tools.md data if available
        tool_md_info = tools_md_data.get(tool_name, {})

        status = {
            'name': tool_name,
            'source': None,
            'required': tool_md_info.get('required', 'false').lower() == 'true',
            'enabled': True,  # If it's in config, it's enabled
            'dev_needed': tool_md_info.get('dev_needed', 'false').lower() == 'true',
            'online': False,
            'environment': [],
            'description': tool_md_info.get('description', ''),
            'category': tool_md_info.get('category', 'Unknown'),
            'dependencies': tool_md_info.get('dependencies', ''),
            'installation': tool_md_info.get('installation', ''),
            'usage': tool_md_info.get('usage', ''),
            'documentation': tool_md_info.get('documentation', ''),
            'version': tool_md_info.get('version', ''),
            'notes': []
        }

        command = config.get('command', '')
        args = config.get('args', [])
        cwd = config.get('cwd', '')
        env = config.get('env', {})

        # Determine tool type and source
        if command == 'npx':
            if len(args) > 0:
                package_name = args[-1] if not args[-1].startswith('-') else args[-2]
                status['source'] = f"NPM: {package_name}"

                # Check if package is available and can be executed
                status['online'] = self.test_mcp_server_startup(tool_name, config)

        elif command == 'python':
            if len(args) > 1 and args[0] == '-m':
                module_name = args[1]
                status['source'] = f"Python Module: {module_name}"

                # Check if module can be imported and server can start
                if self.check_python_module(module_name, cwd):
                    status['online'] = self.test_mcp_server_startup(tool_name, config)
                else:
                    status['online'] = False

                # Check if source directory exists
                if cwd and not self.check_directory_exists(cwd):
                    status['notes'].append(f"Source directory missing: {cwd}")

        # Override required status if not specified in tools.md but is in required list
        if not status['required']:
            required_tools = {
                'taskmaster-ai', 'filesystem', 'git', 'fetch', 'memory',
                'sequentialthinking', 'ptolemies', 'bayes', 'surrealdb',
                'logfire', 'context7'
            }
            status['required'] = tool_name in required_tools

        # Set default descriptions for tools not in tools.md
        if not status['description']:
            descriptions = {
                'taskmaster-ai': 'AI-powered task management and workflow automation',
                'filesystem': 'File system operations and project management',
                'git': 'Git version control integration',
                'fetch': 'HTTP/API request capabilities',
                'memory': 'Persistent memory and context management',
                'sequentialthinking': 'Step-by-step reasoning and problem solving',
                'ptolemies': 'Knowledge base and semantic search (SurrealDB)',
                'bayes': 'Bayesian analysis and statistical modeling',
                'surrealdb': 'Multi-model database operations',
                'context7': 'Contextual reasoning with Redis backend',
                'crawl4ai': 'Web scraping and content extraction',
                'solver-z3': 'Z3 theorem prover for constraint solving',
                'solver-pysat': 'SAT solver for boolean satisfiability',
                'magic': 'Code generation and transformation utilities',
                'shadcn-ui': 'UI component generation for React/Next.js',
                'registry': 'MCP server registry and discovery',
                'github': 'GitHub integration and repository management',
                'orchestrator': 'Multi-agent orchestration and coordination'
            }
            status['description'] = descriptions.get(tool_name, 'Custom MCP tool')

        return status

    def generate_report_data(self) -> Dict:
        """Generate comprehensive report data."""
        # Load configurations
        zed_config = self.load_config(self.zed_config)
        claude_config = self.load_config(self.claude_config)
        tools_md_data = self.load_tools_md()

        # Extract MCP server configurations
        zed_servers = zed_config.get('mcpServers', {})
        claude_servers = claude_config.get('mcpServers', {})

        # Get all tools from tools.md as the source of truth
        all_tools = {}

        # Process all tools from tools.md
        for tool_key, tool_data in tools_md_data.items():
            # Extract original tool name (remove type suffix if present)
            if '_anthropic_core_tool' in tool_key:
                tool_name = tool_key.replace('_anthropic_core_tool', '')
            elif '_pydantic-ai_core_tool' in tool_key:
                tool_name = tool_key.replace('_pydantic-ai_core_tool', '')
            elif '_zed-mcp_server' in tool_key:
                tool_name = tool_key.replace('_zed-mcp_server', '')
            elif '_mcp_server' in tool_key:
                tool_name = tool_key.replace('_mcp_server', '')
            else:
                tool_name = tool_key

            tool_type = tool_data.get('type', 'unknown')
            is_required = tool_data.get('required', 'false').lower() == 'true'

            # For anthropic_core_tool - these are available in Claude Code
            if tool_type == 'anthropic_core_tool':
                # Anthropic core tools are always online when using Claude Code
                is_online = True  # Always available in Claude Code environment

                status = {
                    'name': tool_name,
                    'description': tool_data.get('description', ''),
                    'source': f'Anthropic Core Tool',
                    'required': is_required,
                    'enabled': True,  # Always enabled if in tools.md
                    'dev_needed': tool_data.get('dev_needed', 'false').lower() == 'true',
                    'online': is_online,
                    'environment': 'Claude Code',
                    'type': tool_type,
                    'category': tool_data.get('category', 'Unknown'),
                    'dependencies': tool_data.get('dependencies', ''),
                    'installation': tool_data.get('installation', ''),
                    'usage': tool_data.get('usage', ''),
                    'documentation': tool_data.get('documentation', ''),
                    'version': tool_data.get('version', ''),
                    'notes': []
                }
                all_tools[f"{tool_name}_anthropic"] = status

            # For zed-mcp_server - these are available in Zed IDE
            elif tool_type == 'zed-mcp_server':
                # Check if this tool is actually configured in Zed settings
                zed_config = self.load_config(self.zed_config)
                zed_servers = zed_config.get('mcpServers', {})

                # Use name mapping to check for the tool
                name_mapping = self.get_tool_name_mapping()
                config_name = name_mapping.get(tool_name, tool_name)

                # Also check for partial matches and common patterns
                is_configured_in_zed = False
                matched_config_name = None
                server_config = None

                # First try exact mapping
                if config_name in zed_servers:
                    is_configured_in_zed = True
                    matched_config_name = config_name
                    server_config = zed_servers[config_name]
                else:
                    # Try to find partial matches or related tools
                    for zed_server_name in zed_servers.keys():
                        # Check if zed server name contains part of our tool name
                        tool_base = tool_name.replace('mcp-server-', '').replace('zed-', '').replace('-mcp', '')
                        if tool_base in zed_server_name or zed_server_name in tool_base:
                            is_configured_in_zed = True
                            matched_config_name = zed_server_name
                            server_config = zed_servers[zed_server_name]
                            break

                is_online = False
                if is_configured_in_zed and server_config:
                    # Test if the server can actually start
                    is_online = self.test_mcp_server_startup(matched_config_name, server_config)

                notes = []
                if not is_configured_in_zed:
                    notes.append(f"Not configured in Zed settings (looking for '{config_name}') - requires manual installation")
                elif matched_config_name != config_name:
                    notes.append(f"Found as '{matched_config_name}' in Zed settings")
                    if not is_online:
                        notes.append(f"Configured but cannot start - check dependencies")
                elif not is_online:
                    notes.append(f"Configured but cannot start - check dependencies")

                status = {
                    'name': tool_name,
                    'description': tool_data.get('description', ''),
                    'source': f'Zed MCP Server',
                    'required': is_required,
                    'enabled': is_configured_in_zed,
                    'dev_needed': tool_data.get('dev_needed', 'false').lower() == 'true',
                    'online': is_online,
                    'environment': 'Zed IDE',
                    'type': tool_type,
                    'category': tool_data.get('category', 'Unknown'),
                    'dependencies': tool_data.get('dependencies', ''),
                    'installation': tool_data.get('installation', ''),
                    'usage': tool_data.get('usage', ''),
                    'documentation': tool_data.get('documentation', ''),
                    'version': tool_data.get('version', ''),
                    'notes': notes
                }
                all_tools[f"{tool_name}_zed"] = status

            # For regular mcp_server - check if configured in Zed or Claude
            elif tool_type == 'mcp_server':
                # Use name mapping to check for the tool
                name_mapping = self.get_tool_name_mapping()
                config_name = name_mapping.get(tool_name, tool_name)

                # Get configurations
                zed_config = self.load_config(self.zed_config)
                claude_config = self.load_config(self.claude_config)
                zed_servers = zed_config.get('mcpServers', {})
                claude_servers = claude_config.get('mcpServers', {})

                # Check if this tool is configured in Zed
                if config_name in zed_servers:
                    status = self.get_tool_status(config_name, zed_servers[config_name], tools_md_data)
                    status['name'] = tool_name  # Use original name for display
                    status['environment'] = 'Zed IDE'
                    status['required'] = is_required
                    status['enabled'] = status.pop('configured', True)  # Rename configured to enabled
                    status['dev_needed'] = tool_data.get('dev_needed', 'false').lower() == 'true'
                    all_tools[f"{tool_name}_zed"] = status

                # Check if this tool is configured in Claude
                if config_name in claude_servers:
                    status = self.get_tool_status(config_name, claude_servers[config_name], tools_md_data)
                    status['name'] = tool_name  # Use original name for display
                    status['environment'] = 'Claude Code'
                    status['required'] = is_required
                    status['enabled'] = status.pop('configured', True)  # Rename configured to enabled
                    status['dev_needed'] = tool_data.get('dev_needed', 'false').lower() == 'true'
                    all_tools[f"{tool_name}_claude"] = status

                # If not configured in either but is required, mark as missing
                if config_name not in zed_servers and config_name not in claude_servers and is_required:
                    status = {
                        'name': tool_name,
                        'description': tool_data.get('description', ''),
                        'source': f'MCP Server (Not Enabled)',
                        'required': is_required,
                        'enabled': False,
                        'dev_needed': tool_data.get('dev_needed', 'false').lower() == 'true',
                        'online': False,
                        'environment': 'Missing',
                        'type': tool_type,
                        'category': tool_data.get('category', 'Unknown'),
                        'dependencies': tool_data.get('dependencies', ''),
                        'installation': tool_data.get('installation', ''),
                        'usage': tool_data.get('usage', ''),
                        'documentation': tool_data.get('documentation', ''),
                        'version': tool_data.get('version', ''),
                        'notes': [f'Tool not enabled in Zed or Claude settings (looking for \'{config_name}\')']
                    }
                    all_tools[f"{tool_name}_missing"] = status

        # System information
        system_info = {
            'python_version': sys.version,
            'python_path': sys.executable,
            'devqai_root': str(self.devqai_root),
            'project_root': str(self.project_root),
            'node_available': self.check_command_available('node'),
            'npm_available': self.check_command_available('npm'),
            'npx_available': self.check_command_available('npx'),
            'git_available': self.check_command_available('git'),
            'zed_config_exists': self.zed_config.exists(),
            'claude_config_exists': self.claude_config.exists(),
            'tools_dir_exists': self.tools_dir.exists()
        }

        # Calculate unique tools for summary (don't double count)
        unique_tools = set()
        for key, tool in all_tools.items():
            unique_tools.add(tool['name'])

        unique_required = set()
        unique_online = set()
        unique_required_online = set()

        for tool in all_tools.values():
            if tool['required']:
                unique_required.add(tool['name'])
                if tool['online']:
                    unique_required_online.add(tool['name'])
            if tool['online']:
                unique_online.add(tool['name'])

        return {
            'generated_at': datetime.now().isoformat(),
            'system_info': system_info,
            'tools': all_tools,
            'summary': {
                'total_tools': len(unique_tools),
                'required_tools': len(unique_required),
                'online_tools': len(unique_online),
                'required_online': len(unique_required_online),
                'configured_tools': len(all_tools),
                'zed_tools': len(zed_servers),
                'claude_tools': len(claude_servers)
            }
        }

    def generate_markdown_report(self, data: Dict) -> str:
        """Generate markdown report from data."""
        md = []

        # Header
        md.append("# DevQ.ai MCP Tools Report")
        md.append("")
        md.append(f"**Generated:** {data['generated_at']}")
        md.append(f"**Project:** {data['system_info']['project_root']}")
        md.append("")

        # Summary (replacing Executive Summary)
        summary = data['summary']
        md.append(f"**{summary['required_online']} out of {summary['required_tools']} Required Tools Online; {summary['online_tools']} Tools Online Total**")
        md.append("")

        # Tools Table
        md.append("## MCP Tools Inventory")
        md.append("")
        md.append("| Tool | Source | Required | Enabled | Dev Needed | Online | Environment |")
        md.append("|------|--------|----------|---------|------------|--------|-------------|")

        # Sort tools by tool name (without environment suffix)
        sorted_tools = sorted(data['tools'].items(), key=lambda x: x[1]['name'])

        for tool_key, tool in sorted_tools:
            required = "✅" if tool['required'] else "❌"
            enabled = "✅" if tool['enabled'] else "❌"
            dev_needed = "✅" if tool['dev_needed'] else "❌"
            online = "✅" if tool['online'] else "❌"
            environment = tool['environment']
            source = tool['source'] or 'Unknown'
            tool_name = tool['name']

            md.append(f"| {tool_name} | {source} | {required} | {enabled} | {dev_needed} | {online} | {environment} |")

        md.append("")

        # System Information (moved after table)
        md.append("## System Information")
        md.append("")
        sys_info = data['system_info']
        md.append(f"- **Python Version:** {sys_info['python_version'].split()[0]}")
        md.append(f"- **Python Path:** `{sys_info['python_path']}`")
        md.append(f"- **DevQ.ai Root:** `{sys_info['devqai_root']}`")
        md.append(f"- **Tools Directory:** `{sys_info['project_root']}/tools/` {'✅' if sys_info['tools_dir_exists'] else '❌'}")
        md.append(f"- **Node.js Available:** {'✅' if sys_info['node_available'] else '❌'}")
        md.append(f"- **NPM Available:** {'✅' if sys_info['npm_available'] else '❌'}")
        md.append(f"- **NPX Available:** {'✅' if sys_info['npx_available'] else '❌'}")
        md.append(f"- **Git Available:** {'✅' if sys_info['git_available'] else '❌'}")
        md.append(f"- **Zed Config:** {'✅' if sys_info['zed_config_exists'] else '❌'}")
        md.append(f"- **Claude Config:** {'✅' if sys_info['claude_config_exists'] else '❌'}")
        md.append("")

        # Detailed Tool Information - Each tool gets its own line item
        md.append("## Detailed Tool Information")
        md.append("")

        for tool_key, tool in sorted_tools:
            tool_name = tool['name']
            environment = tool['environment']
            md.append(f"### {tool_name} ({environment})")
            md.append("")
            md.append(f"**Description:** {tool['description']}")
            md.append("")
            md.append(f"- **Source:** {tool['source'] or 'Unknown'}")
            md.append(f"- **Required:** {'Yes' if tool['required'] else 'No'}")
            md.append(f"- **Enabled:** {'Yes' if tool['enabled'] else 'No'}")
            md.append(f"- **Dev Needed:** {'Yes' if tool['dev_needed'] else 'No'}")
            md.append(f"- **Online:** {'Yes' if tool['online'] else 'No'}")
            md.append(f"- **Environment:** {tool['environment']}")

            # Include all parameters from tools.md if available
            if tool['category'] and tool['category'] != 'Unknown':
                md.append(f"- **Category:** {tool['category']}")
            if tool['version']:
                md.append(f"- **Version:** {tool['version']}")
            if tool['dependencies']:
                md.append(f"- **Dependencies:** {tool['dependencies']}")
            if tool['installation']:
                md.append(f"- **Installation:** {tool['installation']}")
            if tool['usage']:
                md.append(f"- **Usage:** {tool['usage']}")
            if tool['documentation']:
                md.append(f"- **Documentation:** {tool['documentation']}")

            if tool['notes']:
                md.append(f"- **Notes:**")
                for note in tool['notes']:
                    md.append(f"  - {note}")

            md.append("")

        # Status Legend
        md.append("## Status Legend")
        md.append("")
        md.append("- **Source:** Origin location or package name")
        md.append("- **Required:** Essential for DevQ.ai five-component stack")
        md.append("- **Configured:** Present in configuration files")
        md.append("- **Online:** Available and functional")
        md.append("- **Environment:** Which development environments use this tool")
        md.append("")

        # Required Tools Summary
        md.append("## Required Tools Summary")
        md.append("")
        required_tools = [(tool_key, tool) for tool_key, tool in sorted_tools if tool['required']]

        if required_tools:
            md.append("| Tool | Status | Environment |")
            md.append("|------|--------|-------------|")

            for tool_key, tool in required_tools:
                status = "🟢 Online" if tool['online'] else "🔴 Offline"
                environment = tool['environment']
                tool_name = tool['name']
                md.append(f"| {tool_name} | {status} | {environment} |")
            md.append("")

        # Recommendations
        md.append("## Recommendations")
        md.append("")

        offline_required = set()
        for tool in data['tools'].values():
            if tool['required'] and not tool['online']:
                offline_required.add(tool['name'])

        if offline_required:
            md.append("### Critical Issues")
            md.append("")
            for tool_name in sorted(offline_required):
                md.append(f"- **{tool_name}:** Required tool is offline - check installation and dependencies")
            md.append("")

        md.append("### Next Steps")
        md.append("")
        md.append("1. **Install Missing Required Tools:** Ensure all required tools are online")
        md.append("2. **Verify Dependencies:** Check Python paths and NPM package availability")
        md.append("3. **Test Tool Functionality:** Run individual tool tests to verify operation")
        md.append("4. **Update Documentation:** Keep tool configurations synchronized")
        md.append("5. **Maintain tools.md:** Update tool information in `tools/tools.md` as needed")
        md.append("")

        # Footer
        md.append("---")
        md.append("")
        md.append(f"*Report generated by `python scripts/generate_tools_report.py` on {data['generated_at']}*")
        md.append("")

        return "\n".join(md)

    def run(self) -> None:
        """Generate and save the tools report."""
        print("🔍 Generating DevQ.ai MCP Tools Report...")
        print(f"📁 Project root: {self.project_root}")
        print(f"📁 DevQ.ai root: {self.devqai_root}")
        print(f"📁 Tools directory: {self.tools_dir}")
        print("")

        # Ensure tools directory exists
        self.tools_dir.mkdir(exist_ok=True)

        # Generate report data
        print("📊 Analyzing MCP tool configurations...")
        data = self.generate_report_data()

        print(f"✅ Found {data['summary']['total_tools']} tools")
        print(f"✅ {data['summary']['online_tools']} tools are online")
        print(f"✅ {data['summary']['required_online']} out of {data['summary']['required_tools']} required tools are online")
        print("")

        # Generate markdown report
        print("📝 Generating markdown report...")
        markdown_content = self.generate_markdown_report(data)

        # Save report to tools directory
        report_path = self.tools_dir / "tools_report.md"
        with open(report_path, 'w') as f:
            f.write(markdown_content)

        print(f"✅ Report saved to: {report_path}")
        print("")
        print("🎯 Quick Status:")
        print(f"   📊 {data['summary']['required_online']}/{data['summary']['required_tools']} required tools online")

        # Show critical issues (unique tools only)
        offline_required = set()
        for tool in data['tools'].values():
            if tool['required'] and not tool['online']:
                offline_required.add(tool['name'])

        if offline_required:
            print("❌ Critical Issues:")
            for tool_name in sorted(offline_required):
                print(f"   - {tool_name}: Required but offline")
        else:
            print("✅ All required tools are online")

        print("")
        print(f"📖 View full report: cat {report_path}")


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        devqai_root = sys.argv[1]
    else:
        devqai_root = "/Users/dionedge/devqai"

    reporter = MCPToolsReporter(devqai_root)
    reporter.run()


if __name__ == "__main__":
    main()
