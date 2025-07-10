"""
MCP Tools Implementation
"""

from typing import Dict, Any, List
import mcp.types as types
from datetime import datetime
import logfire
import os

def get_tools() -> List[types.Tool]:
    """Define available tools"""
    return [
        types.Tool(
            name="send_log",
            description="Send a log entry to Logfire.",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The log message."
                    },
                    "level": {
                        "type": "string",
                        "description": "The log level."
                    }
                },
                "required": ["message", "level"]
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
    if name == "send_log":
        try:
            logfire.configure(
                token=os.environ.get("LOGFIRE_TOKEN")
            )
            logfire.log(arguments["level"], arguments["message"])
            return {
                "status": "success",
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
            "service": "logfire-mcp",
            "timestamp": str(datetime.now())
        }
    else:
        return {"error": f"Unknown tool: {name}"}
