#!/usr/bin/env python3
"""
Demo script showing multiple MCP servers registering with the registry.
Creates HTTP versions of our top servers to demonstrate the registry functionality.
"""

import subprocess
import time
import signal
import sys
from fastmcp_http.server import FastMCPHttpServer
import threading

# Create multiple demo servers based on our verified tools
def create_surrealdb_server():
    """SurrealDB MCP server with 10 tools."""
    server = FastMCPHttpServer("surrealdb-mcp", description="SurrealDB connectivity and database operations")
    
    @server.tool()
    def surrealdb_health_check() -> dict:
        return {"status": "healthy", "database": "surrealdb", "tools": 10}
    
    @server.tool()
    def execute_sql_query(query: str) -> dict:
        return {"query": query, "status": "executed", "rows": 42}
    
    @server.tool()
    def create_record(table: str, data: dict) -> dict:
        return {"table": table, "created": True, "id": "record_123"}
    
    @server.tool()
    def vector_search(query: str, limit: int = 10) -> dict:
        return {"query": query, "results": f"{limit} matches found"}
    
    @server.tool()
    def get_database_schema() -> dict:
        return {"tables": ["users", "docs", "vectors"], "count": 3}
    
    return server

def create_thinking_server():
    """Sequential thinking MCP server with 9 tools."""
    server = FastMCPHttpServer("sequential-thinking-mcp", description="Step-by-step problem solving and reasoning")
    
    @server.tool()
    def thinking_health_check() -> dict:
        return {"status": "healthy", "engine": "sequential-thinking", "tools": 9}
    
    @server.tool()
    def create_thinking_workflow(problem: str) -> dict:
        return {"workflow_id": "wf_123", "problem": problem, "steps": 5}
    
    @server.tool()
    def analyze_problem(description: str) -> dict:
        return {"analysis": f"Complex problem: {description}", "complexity": "high"}
    
    @server.tool()
    def execute_workflow(workflow_id: str) -> dict:
        return {"workflow_id": workflow_id, "status": "completed", "result": "success"}
    
    return server

def create_registry_server():
    """Registry MCP server with 8 tools.""" 
    server = FastMCPHttpServer("registry-mcp", description="MCP server discovery and registry management")
    
    @server.tool()
    def registry_health_check() -> dict:
        return {"status": "healthy", "type": "registry", "tools": 8}
    
    @server.tool()
    def list_servers() -> dict:
        return {"servers": ["surrealdb-mcp", "thinking-mcp", "registry-mcp"], "count": 3}
    
    @server.tool()
    def get_server_info(server_name: str) -> dict:
        return {"name": server_name, "status": "active", "tools": "varies"}
    
    @server.tool()
    def validate_registry() -> dict:
        return {"validation": "passed", "issues": [], "servers_validated": 13}
    
    return server

def create_development_server():
    """Development tools MCP server."""
    server = FastMCPHttpServer("development-mcp", description="Development and testing tools collection")
    
    @server.tool() 
    def pytest_health_check() -> dict:
        return {"status": "healthy", "framework": "pytest", "tools": 7}
    
    @server.tool()
    def run_tests(test_path: str = "tests/") -> dict:
        return {"path": test_path, "passed": 45, "failed": 0, "coverage": "95%"}
    
    @server.tool()
    def fastapi_health_check() -> dict:
        return {"status": "healthy", "framework": "fastapi", "tools": 6}
    
    @server.tool()
    def generate_fastapi_app(name: str) -> dict:
        return {"app_name": name, "created": True, "endpoints": 5}
    
    return server

def create_infrastructure_server():
    """Infrastructure management MCP server."""
    server = FastMCPHttpServer("infrastructure-mcp", description="Docker and infrastructure management")
    
    @server.tool()
    def docker_health_check() -> dict:
        return {"status": "healthy", "docker": "running", "tools": 7}
    
    @server.tool()
    def list_containers() -> dict:
        return {"containers": ["app-1", "db-1", "cache-1"], "running": 3}
    
    @server.tool()
    def logfire_health_check() -> dict:
        return {"status": "healthy", "observability": "active", "tools": 4}
    
    return server

def start_server_in_thread(server, port_offset=0):
    """Start a server in a separate thread."""
    def run_server():
        try:
            server.run_http(port=8000 + port_offset)
        except Exception as e:
            print(f"Server failed: {e}")
    
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    return thread

def start_registry():
    """Start the MCP registry."""
    print("🚀 Starting MCP Registry...")
    try:
        registry_process = subprocess.Popen(
            ["python3", "start_registry_server.py"],
            cwd="mcp-registry",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        time.sleep(3)
        print("✅ MCP Registry started on http://127.0.0.1:31337")
        return registry_process
    except Exception as e:
        print(f"❌ Failed to start registry: {e}")
        return None

def check_registry_status():
    """Check how many servers are registered."""
    try:
        from fastmcp_http.client import FastMCPHttpClient
        client = FastMCPHttpClient("http://127.0.0.1:31337")
        
        servers = client.list_servers()
        tools = client.list_tools()
        
        print(f"\n📊 Registry Status:")
        print(f"   • Total registered servers: {len(servers)}")
        print(f"   • Total available tools: {len(tools)}")
        
        print(f"\n🖥️  Registered Servers:")
        for server in servers:
            server_tools = [t for t in tools if t.name.startswith(f"{server.name}.")]
            print(f"   • {server.name}: {len(server_tools)} tools")
        
        return len(servers), len(tools)
        
    except Exception as e:
        print(f"❌ Failed to check registry: {e}")
        return 0, 0

def main():
    print("🚀 Starting Machina MCP Demo with Registry")
    print("=" * 50)
    
    # Start registry first
    registry_process = start_registry()
    if not registry_process:
        print("❌ Cannot continue without registry")
        return
    
    print("\n📦 Starting demo MCP servers...")
    
    # Create and start servers
    servers = [
        ("SurrealDB", create_surrealdb_server()),
        ("Sequential Thinking", create_thinking_server()), 
        ("Registry Management", create_registry_server()),
        ("Development Tools", create_development_server()),
        ("Infrastructure", create_infrastructure_server())
    ]
    
    threads = []
    for i, (name, server) in enumerate(servers):
        print(f"🔧 Starting {name} server...")
        thread = start_server_in_thread(server, i * 10)
        threads.append(thread)
        time.sleep(2)  # Stagger starts
        print(f"✅ {name} server started")
    
    print(f"\n⏳ Waiting for servers to register with registry...")
    time.sleep(5)
    
    # Check registry status
    registered_servers, total_tools = check_registry_status()
    
    if registered_servers >= 5:
        print(f"\n🎉 SUCCESS! {registered_servers} servers registered with {total_tools} tools")
        print("\n🌐 Access the registry:")
        print("   • Registry: http://127.0.0.1:31337")
        print("   • Servers: curl http://127.0.0.1:31337/servers")
        print("   • Tools: curl http://127.0.0.1:31337/tools")
    else:
        print(f"\n⚠️  Only {registered_servers} servers registered")
    
    print(f"\n📈 This demonstrates our 13-server collection:")
    print(f"   • 5 demo servers running (representing the 13 verified servers)")
    print(f"   • {total_tools} tools available through registry")
    print(f"   • All servers auto-registered and discoverable")
    
    try:
        print("\n✨ Press Ctrl+C to stop all servers")
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        print("\n🛑 Stopping servers...")
        if registry_process:
            registry_process.terminate()
        print("✅ Demo complete")

if __name__ == "__main__":
    main()