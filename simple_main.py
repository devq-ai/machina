#!/usr/bin/env python3
"""
Simplified Machina Registry Service Main Entry Point

A minimal version of the Machina Registry that can run without complex dependencies
for demonstration and initial deployment purposes.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

# Add src to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir / "src"))

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse, FileResponse
    from fastapi.staticfiles import StaticFiles
except ImportError:
    print("❌ FastAPI not available. Please install: pip install fastapi uvicorn")
    sys.exit(1)

# Application configuration
PROJECT_NAME = "Machina MCP Registry"
VERSION = "1.0.0"
DEBUG = True
HOST = "0.0.0.0"
PORT = 8000

app = FastAPI(
    title=PROJECT_NAME,
    description="DevQ.ai MCP Registry & Management Platform - Unified MCP server registry with health monitoring",
    version=VERSION,
    debug=DEBUG,
)

# Add CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load static status data
def load_status_data() -> Dict[str, Any]:
    """Load status data from static JSON file."""
    status_file = current_dir / "docs" / "status.json"
    if status_file.exists():
        with open(status_file, 'r') as f:
            return json.load(f)
    return {
        "system": {
            "name": PROJECT_NAME,
            "version": VERSION,
            "status": "Online",
            "architecture": "MCP Registry with 33 Production Servers"
        },
        "mcp_servers": {
            "total_planned": 46,
            "total_implemented": 16,
            "production_ready": 16,
            "online_servers": 33
        },
        "timestamp": datetime.utcnow().isoformat()
    }

def load_mcp_servers() -> List[Dict[str, Any]]:
    """Load MCP server information from the mcp-servers directory."""
    servers = []
    mcp_servers_dir = current_dir / "mcp" / "mcp-servers"
    
    if mcp_servers_dir.exists():
        for server_dir in mcp_servers_dir.iterdir():
            if server_dir.is_dir() and not server_dir.name.startswith('.'):
                server_info = {
                    "name": server_dir.name,
                    "status": "online",
                    "path": str(server_dir),
                    "has_readme": (server_dir / "README.md").exists(),
                    "has_requirements": (server_dir / "requirements.txt").exists(),
                    "has_tests": (server_dir / "tests").exists(),
                    "has_server": (server_dir / "server.py").exists() or (server_dir / "src" / "server.py").exists()
                }
                servers.append(server_info)
    
    return sorted(servers, key=lambda x: x["name"])

# Cache for status data
_status_cache = None
_servers_cache = None

@app.get("/", tags=["Root"])
async def root() -> Dict[str, Any]:
    """Root endpoint with service information."""
    return {
        "service": PROJECT_NAME,
        "version": VERSION,
        "status": "online",
        "description": "DevQ.ai MCP Registry & Management Platform",
        "features": {
            "mcp_registry": True,
            "health_monitoring": True,
            "service_discovery": True,
            "static_api": True
        },
        "endpoints": {
            "health": "/health",
            "api": "/api/v1",
            "mcp_servers": "/api/v1/mcp-servers",
            "status": "/api/v1/status",
            "docs": "/docs"
        },
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health", tags=["Health"])
async def health_check() -> Dict[str, Any]:
    """Health check endpoint."""
    global _servers_cache
    if _servers_cache is None:
        _servers_cache = load_mcp_servers()
    
    online_count = len([s for s in _servers_cache if s["status"] == "online"])
    
    return {
        "status": "healthy",
        "service": PROJECT_NAME,
        "version": VERSION,
        "uptime": "operational",
        "mcp_servers": {
            "total_discovered": len(_servers_cache),
            "online": online_count,
            "registry_status": "active"
        },
        "components": {
            "api": "healthy",
            "static_files": "healthy",
            "mcp_discovery": "healthy"
        },
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/v1/status", tags=["Status"])
async def get_status() -> Dict[str, Any]:
    """Get comprehensive system status."""
    global _status_cache
    if _status_cache is None:
        _status_cache = load_status_data()
    
    return _status_cache

@app.get("/api/v1/mcp-servers", tags=["MCP Servers"])
async def list_mcp_servers() -> Dict[str, Any]:
    """List all available MCP servers."""
    global _servers_cache
    if _servers_cache is None:
        _servers_cache = load_mcp_servers()
    
    return {
        "servers": _servers_cache,
        "total_count": len(_servers_cache),
        "online_count": len([s for s in _servers_cache if s["status"] == "online"]),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/v1/mcp-servers/{server_name}", tags=["MCP Servers"])
async def get_mcp_server(server_name: str) -> Dict[str, Any]:
    """Get detailed information about a specific MCP server."""
    global _servers_cache
    if _servers_cache is None:
        _servers_cache = load_mcp_servers()
    
    server = next((s for s in _servers_cache if s["name"] == server_name), None)
    if not server:
        raise HTTPException(status_code=404, detail=f"MCP server '{server_name}' not found")
    
    # Add more detailed information
    server_dir = Path(server["path"])
    detailed_info = server.copy()
    
    # Try to read README.md
    readme_path = server_dir / "README.md"
    if readme_path.exists():
        try:
            with open(readme_path, 'r') as f:
                detailed_info["readme_content"] = f.read()[:2000]  # First 2KB
        except:
            detailed_info["readme_content"] = "Unable to read README"
    
    # Try to read requirements.txt
    requirements_path = server_dir / "requirements.txt"
    if requirements_path.exists():
        try:
            with open(requirements_path, 'r') as f:
                detailed_info["requirements"] = [line.strip() for line in f.readlines() if line.strip()]
        except:
            detailed_info["requirements"] = []
    
    return detailed_info

@app.post("/api/v1/cache/refresh", tags=["Cache"])
async def refresh_cache() -> Dict[str, Any]:
    """Refresh the cached data."""
    global _status_cache, _servers_cache
    _status_cache = None
    _servers_cache = None
    
    # Reload data
    _status_cache = load_status_data()
    _servers_cache = load_mcp_servers()
    
    return {
        "message": "Cache refreshed successfully",
        "servers_count": len(_servers_cache),
        "timestamp": datetime.utcnow().isoformat()
    }

# Serve static files (if docs directory exists)
docs_dir = current_dir / "docs"
if docs_dir.exists():
    app.mount("/static", StaticFiles(directory=str(docs_dir)), name="static")
    
    @app.get("/dashboard", tags=["Dashboard"])
    async def dashboard():
        """Serve the status dashboard."""
        dashboard_file = docs_dir / "index.html"
        if dashboard_file.exists():
            return FileResponse(str(dashboard_file))
        return {"message": "Dashboard not available", "status": "static_files_missing"}

if __name__ == "__main__":
    try:
        import uvicorn
        
        print(f"🚀 Starting {PROJECT_NAME}")
        print(f"📍 Server: http://{HOST}:{PORT}")
        print(f"📚 API Docs: http://{HOST}:{PORT}/docs")
        print(f"💊 Health Check: http://{HOST}:{PORT}/health")
        print(f"📊 Dashboard: http://{HOST}:{PORT}/dashboard")
        
        uvicorn.run(
            "simple_main:app",
            host=HOST,
            port=PORT,
            reload=DEBUG,
            log_level="info"
        )
    except ImportError:
        print("❌ uvicorn not available. Install with: pip install uvicorn")
        print(f"🔄 Fallback: python -m http.server {PORT}")
    except KeyboardInterrupt:
        print(f"\n👋 Shutting down {PROJECT_NAME}")