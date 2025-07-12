#!/usr/bin/env python3
"""
Start all 13 Machina MCP servers with the registry.
This script converts our FastMCP stdio servers to HTTP servers that register with the MCP registry.
"""

import subprocess
import time
import signal
import sys
import os
from pathlib import Path

# List of all 13 verified MCP servers
SERVERS = [
    {
        "name": "surrealdb_mcp",
        "file": "src/surrealdb_mcp.py",
        "description": "SurrealDB connectivity and database operations",
        "tools": 10
    },
    {
        "name": "sequential_thinking_mcp", 
        "file": "src/sequential_thinking_mcp.py",
        "description": "Sequential thinking engine for problem solving",
        "tools": 9
    },
    {
        "name": "registry_mcp",
        "file": "src/registry_mcp.py", 
        "description": "MCP server discovery and registry management",
        "tools": 8
    },
    {
        "name": "memory_mcp",
        "file": "src/memory_mcp.py",
        "description": "Memory management and persistence for AI workflows",
        "tools": 8
    },
    {
        "name": "docker_mcp",
        "file": "src/docker_mcp.py",
        "description": "Docker container management and orchestration", 
        "tools": 7
    },
    {
        "name": "pytest_mcp",
        "file": "src/pytest_mcp.py",
        "description": "Python testing framework integration",
        "tools": 7
    },
    {
        "name": "fastapi_mcp",
        "file": "src/fastapi_mcp.py",
        "description": "FastAPI application development and management",
        "tools": 6
    },
    {
        "name": "fastmcp_mcp",
        "file": "src/fastmcp_mcp.py", 
        "description": "FastMCP framework development tools",
        "tools": 6
    },
    {
        "name": "github_mcp",
        "file": "src/github_mcp.py",
        "description": "GitHub repository operations and management",
        "tools": 6
    },
    {
        "name": "pydantic_ai_mcp",
        "file": "src/pydantic_ai_mcp.py",
        "description": "Pydantic AI agent management and orchestration",
        "tools": 6
    },
    {
        "name": "server_template",
        "file": "src/server_template.py",
        "description": "Production MCP server template",
        "tools": 5
    },
    {
        "name": "crawl4ai_mcp",
        "file": "src/crawl4ai_mcp.py",
        "description": "Web crawling and content extraction",
        "tools": 4
    },
    {
        "name": "logfire_mcp",
        "file": "src/logfire_mcp.py",
        "description": "Logfire observability and monitoring",
        "tools": 4
    }
]

class ServerManager:
    def __init__(self):
        self.processes = []
        self.registry_process = None
        
    def start_registry(self):
        """Start the MCP registry server."""
        print("🚀 Starting MCP Registry server...")
        try:
            self.registry_process = subprocess.Popen(
                ["python3", "start_registry_server.py"],
                cwd="/Users/dionedge/devqai/machina/mcp-registry",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            time.sleep(3)  # Give registry time to start
            print("✅ MCP Registry started on http://127.0.0.1:31337")
            return True
        except Exception as e:
            print(f"❌ Failed to start registry: {e}")
            return False
    
    def create_http_server_wrapper(self, server_config):
        """Create an HTTP wrapper for a FastMCP stdio server."""
        wrapper_code = f'''#!/usr/bin/env python3
"""
HTTP wrapper for {server_config["name"]} to work with MCP Registry.
Auto-generated wrapper that converts stdio server to HTTP server.
"""

import sys
import os
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import the original server
from {server_config["name"]} import app as original_app

# Import HTTP server functionality
from fastmcp_http.server import FastMCPHttpServer
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create HTTP server with same name and description
http_server = FastMCPHttpServer(
    "{server_config['name'].replace('_', '-')}",
    description="{server_config['description']}"
)

# Copy all tools from the original FastMCP app to the HTTP server
if hasattr(original_app, '_tools'):
    for tool_name, tool_func in original_app._tools.items():
        # Register the tool with the HTTP server
        http_server.add_tool(tool_func)
        logger.info(f"Registered tool: {{tool_name}}")

if __name__ == "__main__":
    logger.info("🚀 Starting {{server_config['name']}} HTTP server")
    logger.info("📡 Auto-registering with MCP Registry")
    try:
        http_server.run_http()
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped")
    except Exception as e:
        logger.error(f"❌ Server failed: {{e}}")
'''
        
        wrapper_file = f"http_wrappers/{server_config['name']}_http.py"
        os.makedirs("http_wrappers", exist_ok=True)
        
        with open(wrapper_file, 'w') as f:
            f.write(wrapper_code)
            
        return wrapper_file
    
    def start_server(self, server_config):
        """Start a single MCP server as HTTP server."""
        print(f"🔧 Starting {server_config['name']} ({server_config['tools']} tools)...")
        
        try:
            # Create HTTP wrapper
            wrapper_file = self.create_http_server_wrapper(server_config)
            
            # Start the HTTP wrapper
            process = subprocess.Popen(
                ["python3", wrapper_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            self.processes.append({
                "name": server_config["name"],
                "process": process,
                "tools": server_config["tools"]
            })
            
            time.sleep(2)  # Give server time to start and register
            print(f"✅ {server_config['name']} started")
            return True
            
        except Exception as e:
            print(f"❌ Failed to start {server_config['name']}: {e}")
            return False
    
    def start_all_servers(self):
        """Start the registry and all MCP servers."""
        print("🚀 Starting Machina MCP Server Collection")
        print("=" * 50)
        
        # Start registry first
        if not self.start_registry():
            print("❌ Cannot start servers without registry")
            return False
        
        print(f"\\n📦 Starting {len(SERVERS)} MCP servers...")
        successful_starts = 0
        
        for server_config in SERVERS:
            if self.start_server(server_config):
                successful_starts += 1
            time.sleep(1)  # Stagger server starts
        
        print(f"\\n📊 Startup Summary:")
        print(f"   • Registry: ✅ Running on http://127.0.0.1:31337")
        print(f"   • Servers: {successful_starts}/{len(SERVERS)} started successfully")
        print(f"   • Expected tools: {sum(s['tools'] for s in SERVERS)}")
        
        return successful_starts == len(SERVERS)
    
    def check_registry_status(self):
        """Check the registry to see all registered servers."""
        print("\\n🔍 Checking MCP Registry status...")
        time.sleep(3)  # Give servers time to register
        
        try:
            from fastmcp_http.client import FastMCPHttpClient
            client = FastMCPHttpClient("http://127.0.0.1:31337")
            
            servers = client.list_servers()
            tools = client.list_tools()
            
            print(f"\\n📋 Registry Status:")
            print(f"   • Registered servers: {len(servers)}")
            print(f"   • Available tools: {len(tools)}")
            
            print(f"\\n🖥️  Registered Servers:")
            for server in servers:
                # Count tools for this server
                server_tools = [t for t in tools if t.name.startswith(f"{server.name}.")]
                print(f"   • {server.name}: {len(server_tools)} tools - {server.description}")
            
            return len(servers), len(tools)
            
        except Exception as e:
            print(f"❌ Failed to check registry: {e}")
            return 0, 0
    
    def cleanup(self):
        """Stop all servers and registry."""
        print("\\n🛑 Stopping all servers...")
        
        for server_info in self.processes:
            try:
                server_info["process"].terminate()
                print(f"✅ Stopped {server_info['name']}")
            except:
                pass
        
        if self.registry_process:
            try:
                self.registry_process.terminate()
                print("✅ Stopped MCP Registry")
            except:
                pass
        
        print("🧹 Cleanup complete")

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    print("\\n\\n⚠️  Interrupt received...")
    manager.cleanup()
    sys.exit(0)

def main():
    global manager
    manager = ServerManager()
    
    # Set up signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Start all servers
        if manager.start_all_servers():
            print("\\n✅ All servers started successfully!")
        else:
            print("\\n⚠️  Some servers failed to start")
        
        # Check registry status
        registered_servers, total_tools = manager.check_registry_status()
        
        if registered_servers >= 10:  # Allow for some potential failures
            print(f"\\n🎉 SUCCESS! {registered_servers} servers registered with {total_tools} tools")
            print("\\n🌐 Registry available at: http://127.0.0.1:31337")
            print("📊 View servers: curl http://127.0.0.1:31337/servers")
            print("🛠️  View tools: curl http://127.0.0.1:31337/tools")
        else:
            print(f"\\n⚠️  Only {registered_servers} servers registered (expected ~13)")
        
        print("\\n✨ Press Ctrl+C to stop all servers")
        
        # Keep running until interrupted
        while True:
            time.sleep(10)
            
    except KeyboardInterrupt:
        print("\\n⚠️  Shutting down...")
    finally:
        manager.cleanup()

if __name__ == "__main__":
    main()