"""
MCP Tools Implementation
"""

from typing import Dict, Any, List
import mcp.types as types
from datetime import datetime
import os
import subprocess

def get_tools() -> List[types.Tool]:
    """Define available tools"""
    return [
        types.Tool(
            name="create_ui_component",
            description="Create a UI component by describing it in natural language.",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "A natural language description of the component to create."
                    }
                },
                "required": ["prompt"]
            }
        ),
        types.Tool(
            name="health_check",
            description="Check server health",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]


async def handle_tool_call(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Handle tool execution"""
    if name == "create_ui_component":
        try:
            api_key = os.environ.get("21STDEV_API_KEY")
            if not api_key:
                return {
                    "status": "error",
                    "message": "21STDEV_API_KEY not found in environment variables.",
                    "timestamp": str(datetime.now())
                }
            
            command = [
                "npx",
                "-y",
                "@21st-dev/magic@latest",
                f"API_KEY=\"{api_key}\"",
                "--prompt",
                arguments["prompt"]
            ]
            
            result = subprocess.run(command, capture_output=True, text=True)
            
            if result.returncode != 0:
                return {
                    "status": "error",
                    "message": result.stderr,
                    "timestamp": str(datetime.now())
                }
            
            return {
                "status": "success",
                "result": result.stdout,
                "timestamp": str(datetime.now())
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "timestamp": str(datetime.now())
            }
    elif name == "health_check":
        return {
            "status": "healthy",
            "service": "magic-mcp",
            "timestamp": str(datetime.now())
        }
    else:
        return {"error": f"Unknown tool: {name}"}