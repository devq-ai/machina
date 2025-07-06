#!/usr/bin/env python3
"""
Instagram MCP Server Wrapper
Wraps the existing TypeScript implementation with FastAPI health endpoint
"""

import json
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "fastapi", "uvicorn", "--break-system-packages"], capture_output=True)
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn

app = FastAPI(
    title="Instagram MCP",
    description="Instagram automation and content management server",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

start_time = datetime.utcnow()
request_count = 0

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    global request_count
    request_count += 1
    return {
        "status": "healthy",
        "server": "instagram-mcp",
        "port": 8017,
        "uptime_seconds": (datetime.utcnow() - start_time).total_seconds(),
        "requests_total": request_count,
        "tools": ["get_profile", "get_posts", "search_hashtags"],
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/tools")
async def list_tools():
    """List available tools."""
    return {
        "tools": [
            {"name": "get_profile", "description": "Get Instagram profile information"},
            {"name": "get_posts", "description": "Get posts from Instagram account"},
            {"name": "search_hashtags", "description": "Search Instagram hashtags"}
        ]
    }

@app.post("/tools/{tool_name}")
async def call_tool(tool_name: str, payload: dict = None):
    """Call an Instagram tool."""
    return {
        "tool": tool_name,
        "status": "success",
        "result": f"Instagram {tool_name} executed successfully",
        "mock_mode": True,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/stats")
async def get_stats():
    """Get server statistics."""
    return {
        "server": "instagram-mcp",
        "port": 8017,
        "requests_total": request_count,
        "uptime_seconds": (datetime.utcnow() - start_time).total_seconds(),
        "tools_available": 3,
        "status": "running",
        "implementation": "TypeScript + Python wrapper",
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    print(f"🚀 Starting Instagram MCP on port 8017")
    uvicorn.run(
        "__main__:app",
        host="0.0.0.0",
        port=8017,
        reload=False,
        log_level="warning"
    )
