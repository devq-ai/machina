#!/usr/bin/env python3
"""
MCP Server Setup and Configuration Script for Machina Registry Service

This script helps set up and configure the MCP (Model Context Protocol) server
for integration with AI development environments like Zed IDE, Cursor, and other
MCP-compatible clients.

Features:
- Automatic detection of project structure
- Generation of MCP server configuration
- Validation of dependencies and environment
- Interactive setup for different IDEs
- Testing and verification of MCP server functionality

Usage:
    python setup_mcp.py [--ide zed|cursor|other] [--test] [--config-only]

Examples:
    python setup_mcp.py --ide zed
    python setup_mcp.py --test
    python setup_mcp.py --config-only
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
import shutil


class MCPSetup:
    """MCP Server setup and configuration manager."""

    def __init__(self):
        """Initialize MCP setup manager."""
        self.project_root = Path(__file__).parent.absolute()
        self.src_path = self.project_root / "src"
        self.mcp_server_path = self.project_root / "mcp_server.py"
        self.requirements_path = self.project_root / "requirements.txt"

    def validate_environment(self) -> Dict[str, bool]:
        """Validate the development environment for MCP server."""
        checks = {}

        # Check Python version
        checks["python_version"] = sys.version_info >= (3, 8)

        # Check if source directory exists
        checks["src_directory"] = self.src_path.exists()

        # Check if MCP server script exists
        checks["mcp_server_script"] = self.mcp_server_path.exists()

        # Check if requirements file exists
        checks["requirements_file"] = self.requirements_path.exists()

        # Check if main FastAPI app exists
        checks["fastapi_app"] = (self.src_path / "main.py").exists()

        # Check if MCP modules exist
        mcp_dir = self.src_path / "app" / "mcp"
        checks["mcp_modules"] = (
            mcp_dir.exists() and
            (mcp_dir / "server.py").exists() and
            (mcp_dir / "handlers.py").exists() and
            (mcp_dir / "tools.py").exists()
        )

        return checks

    def check_dependencies(self) -> Dict[str, bool]:
        """Check if required Python packages are installed."""
        required_packages = [
            "fastapi",
            "uvicorn",
            "pydantic",
            "logfire",
            "mcp",
            "redis",
            "sqlalchemy"
        ]

        deps = {}
        for package in required_packages:
            try:
                __import__(package.replace("-", "_"))
                deps[package] = True
            except ImportError:
                deps[package] = False

        return deps

    def install_dependencies(self) -> bool:
        """Install required dependencies."""
        try:
            print("Installing MCP server dependencies...")
            subprocess.run([
                sys.executable, "-m", "pip", "install", "-r", str(self.requirements_path)
            ], check=True, capture_output=True)
            print("✅ Dependencies installed successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install dependencies: {e}")
            return False

    def generate_zed_config(self) -> Dict[str, Any]:
        """Generate Zed IDE MCP server configuration."""
        return {
            "mcpServers": {
                "machina-registry": {
                    "command": "python",
                    "args": [str(self.mcp_server_path)],
                    "env": {
                        "PYTHONPATH": str(self.src_path),
                        "MCP_DEBUG": "false"
                    }
                }
            }
        }

    def generate_cursor_config(self) -> Dict[str, Any]:
        """Generate Cursor IDE MCP server configuration."""
        return {
            "mcp": {
                "servers": {
                    "machina-registry": {
                        "command": "python",
                        "args": [str(self.mcp_server_path)],
                        "env": {
                            "PYTHONPATH": str(self.src_path),
                            "MCP_DEBUG": "false"
                        }
                    }
                }
            }
        }

    def save_zed_config(self, config: Dict[str, Any]) -> bool:
        """Save configuration to Zed IDE settings."""
        try:
            # Check if .zed directory exists
            zed_dir = self.project_root / ".zed"
            if not zed_dir.exists():
                zed_dir.mkdir(exist_ok=True)
                print(f"📁 Created .zed directory: {zed_dir}")

            settings_file = zed_dir / "settings.json"

            # Load existing settings if they exist
            existing_settings = {}
            if settings_file.exists():
                try:
                    with open(settings_file, 'r') as f:
                        existing_settings = json.load(f)
                except json.JSONDecodeError:
                    print("⚠️  Existing settings.json is invalid, will overwrite")

            # Merge MCP server configuration
            if "mcpServers" in existing_settings:
                existing_settings["mcpServers"].update(config["mcpServers"])
            else:
                existing_settings.update(config)

            # Save updated settings
            with open(settings_file, 'w') as f:
                json.dump(existing_settings, f, indent=2)

            print(f"✅ Zed configuration saved to: {settings_file}")
            return True

        except Exception as e:
            print(f"❌ Failed to save Zed configuration: {e}")
            return False

    def save_cursor_config(self, config: Dict[str, Any]) -> bool:
        """Save configuration to Cursor IDE settings."""
        try:
            # Cursor typically uses a different location
            # This is a simplified version - actual implementation may vary
            config_file = self.project_root / ".cursor" / "mcp.json"
            config_file.parent.mkdir(exist_ok=True)

            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)

            print(f"✅ Cursor configuration saved to: {config_file}")
            return True

        except Exception as e:
            print(f"❌ Failed to save Cursor configuration: {e}")
            return False

    def test_mcp_server(self) -> bool:
        """Test the MCP server functionality."""
        try:
            print("🧪 Testing MCP server...")

            # Test that the server script can be imported
            test_script = f"""
import sys
sys.path.insert(0, '{self.src_path}')

try:
    from app.mcp.server import MCPServer
    from app.mcp.tools import get_all_mcp_tools

    # Create server instance
    server = MCPServer()
    print("✅ MCP server instantiated successfully")

    # Check tools
    tools = get_all_mcp_tools()
    print(f"✅ Found {{len(tools)}} MCP tools")

    for tool in tools[:3]:  # Show first 3 tools
        print(f"  - {{tool.name}}: {{tool.description}}")

    if len(tools) > 3:
        print(f"  ... and {{len(tools) - 3}} more tools")

    print("✅ MCP server test passed")

except Exception as e:
    print(f"❌ MCP server test failed: {{e}}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
"""

            # Run the test in a subprocess
            result = subprocess.run([
                sys.executable, "-c", test_script
            ], capture_output=True, text=True)

            if result.returncode == 0:
                print(result.stdout)
                return True
            else:
                print(f"❌ MCP server test failed:")
                print(result.stderr)
                return False

        except Exception as e:
            print(f"❌ MCP server test error: {e}")
            return False

    def show_integration_instructions(self, ide: str):
        """Show integration instructions for specific IDE."""
        print(f"\n🔧 Integration Instructions for {ide.upper()}:")
        print("=" * 50)

        if ide == "zed":
            print(f"""
1. The MCP server configuration has been added to: {self.project_root}/.zed/settings.json

2. Restart Zed IDE to load the new MCP server

3. The following MCP tools will be available:
   - get_tasks: Get all tasks with filtering and pagination
   - create_task: Create new tasks with details
   - update_task_status: Update task status
   - analyze_task_complexity: AI-powered complexity analysis
   - get_task_statistics: Task analytics and metrics
   - search_tasks: Search tasks with queries and filters
   - get_service_health: Monitor service health

4. Use the tools in Zed by typing commands like:
   - "Show me all high priority tasks"
   - "Create a new feature task for user authentication"
   - "Update task 5 status to in progress"
   - "Analyze the complexity of task 3"

5. If you encounter issues, check the Zed console for MCP server logs
""")

        elif ide == "cursor":
            print(f"""
1. The MCP server configuration has been saved to: {self.project_root}/.cursor/mcp.json

2. Restart Cursor IDE to load the new MCP server

3. Configure Cursor to use the MCP server by adding it to your settings

4. The MCP tools will be available for AI-assisted development

5. Refer to Cursor documentation for specific MCP integration steps
""")

        else:
            print(f"""
1. For {ide}, you'll need to configure the MCP server manually

2. MCP Server Details:
   - Script: {self.mcp_server_path}
   - Command: python {self.mcp_server_path}
   - Environment: PYTHONPATH={self.src_path}

3. Transport: stdio (standard input/output)

4. Protocol: MCP (Model Context Protocol) v2024-11-05

5. Available Tools: 10 task management and analysis tools

6. Refer to your IDE's MCP integration documentation
""")

    def run_interactive_setup(self):
        """Run interactive setup process."""
        print("🚀 Machina Registry MCP Server Setup")
        print("=" * 40)

        # Validate environment
        print("\n📋 Validating environment...")
        env_checks = self.validate_environment()

        all_env_ok = True
        for check, status in env_checks.items():
            status_icon = "✅" if status else "❌"
            print(f"{status_icon} {check.replace('_', ' ').title()}: {'OK' if status else 'MISSING'}")
            if not status:
                all_env_ok = False

        if not all_env_ok:
            print("\n❌ Environment validation failed. Please fix the issues above.")
            return False

        # Check dependencies
        print("\n📦 Checking dependencies...")
        deps = self.check_dependencies()

        missing_deps = [dep for dep, installed in deps.items() if not installed]
        if missing_deps:
            print(f"❌ Missing dependencies: {', '.join(missing_deps)}")
            install_choice = input("Install missing dependencies? (y/n): ").lower().strip()
            if install_choice == 'y':
                if not self.install_dependencies():
                    return False
            else:
                print("❌ Cannot proceed without required dependencies")
                return False
        else:
            print("✅ All dependencies are installed")

        # Choose IDE
        print("\n🔧 IDE Integration Setup")
        ide_choice = input("Which IDE are you using? (zed/cursor/other): ").lower().strip()

        if ide_choice == "zed":
            config = self.generate_zed_config()
            self.save_zed_config(config)
        elif ide_choice == "cursor":
            config = self.generate_cursor_config()
            self.save_cursor_config(config)
        else:
            print("Manual configuration required for other IDEs")

        # Test server
        test_choice = input("\nTest MCP server functionality? (y/n): ").lower().strip()
        if test_choice == 'y':
            if self.test_mcp_server():
                print("✅ MCP server is working correctly")
            else:
                print("❌ MCP server test failed - check configuration")
                return False

        # Show integration instructions
        self.show_integration_instructions(ide_choice)

        print("\n🎉 MCP server setup completed successfully!")
        print("\nNext steps:")
        print("1. Restart your IDE")
        print("2. Try using MCP tools in your AI assistant")
        print("3. Check logs if you encounter issues")

        return True


def main():
    """Main entry point for MCP setup script."""
    parser = argparse.ArgumentParser(description="Setup MCP server for Machina Registry Service")
    parser.add_argument("--ide", choices=["zed", "cursor", "other"], help="Target IDE for configuration")
    parser.add_argument("--test", action="store_true", help="Test MCP server functionality")
    parser.add_argument("--config-only", action="store_true", help="Generate configuration only")
    parser.add_argument("--install-deps", action="store_true", help="Install dependencies only")

    args = parser.parse_args()

    setup = MCPSetup()

    try:
        if args.install_deps:
            # Install dependencies only
            setup.install_dependencies()
            return

        if args.test:
            # Test MCP server only
            if setup.test_mcp_server():
                print("✅ MCP server test passed")
            else:
                print("❌ MCP server test failed")
                sys.exit(1)
            return

        if args.config_only:
            # Generate configuration only
            if args.ide == "zed":
                config = setup.generate_zed_config()
                setup.save_zed_config(config)
            elif args.ide == "cursor":
                config = setup.generate_cursor_config()
                setup.save_cursor_config(config)
            else:
                print("Please specify --ide for configuration generation")
                sys.exit(1)
            return

        if args.ide:
            # Non-interactive setup for specific IDE
            print(f"Setting up MCP server for {args.ide.upper()}...")

            # Validate environment
            env_checks = setup.validate_environment()
            if not all(env_checks.values()):
                print("❌ Environment validation failed")
                sys.exit(1)

            # Check dependencies
            deps = setup.check_dependencies()
            missing_deps = [dep for dep, installed in deps.items() if not installed]
            if missing_deps:
                print(f"Installing missing dependencies: {', '.join(missing_deps)}")
                if not setup.install_dependencies():
                    sys.exit(1)

            # Generate and save configuration
            if args.ide == "zed":
                config = setup.generate_zed_config()
                setup.save_zed_config(config)
            elif args.ide == "cursor":
                config = setup.generate_cursor_config()
                setup.save_cursor_config(config)

            # Test server
            if setup.test_mcp_server():
                print("✅ MCP server setup completed successfully")
                setup.show_integration_instructions(args.ide)
            else:
                print("❌ MCP server test failed")
                sys.exit(1)

        else:
            # Interactive setup
            if not setup.run_interactive_setup():
                sys.exit(1)

    except KeyboardInterrupt:
        print("\n❌ Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
