"""
MCP Tools Implementation
"""

from typing import Dict, Any, List
import mcp.types as types
from datetime import datetime
import pytz


def get_tools() -> List[types.Tool]:
    """Define available tools"""
    return [
        types.Tool(
            name="get_current_time",
            description="Gets the current time in a specified timezone.",
            inputSchema={
                "type": "object",
                "properties": {
                    "timezone": {
                        "type": "string",
                        "description": "The timezone to get the current time in."
                    }
                },
                "required": ["timezone"]
            }
        ),
        types.Tool(
            name="convert_time",
            description="Converts a time from one timezone to another.",
            inputSchema={
                "type": "object",
                "properties": {
                    "time": {
                        "type": "string",
                        "description": "The time to convert."
                    },
                    "from_timezone": {
                        "type": "string",
                        "description": "The timezone to convert from."
                    },
                    "to_timezone": {
                        "type": "string",
                        "description": "The timezone to convert to."
                    }
                },
                "required": ["time", "from_timezone", "to_timezone"]
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
    if name == "get_current_time":
        try:
            tz = pytz.timezone(arguments["timezone"])
            return {
                "status": "success",
                "time": datetime.now(tz).isoformat(),
                "timestamp": str(datetime.now())
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "timestamp": str(datetime.now())
            }
    elif name == "convert_time":
        try:
            from_tz = pytz.timezone(arguments["from_timezone"])
            to_tz = pytz.timezone(arguments["to_timezone"])
            time = from_tz.localize(datetime.fromisoformat(arguments["time"]))
            return {
                "status": "success",
                "time": time.astimezone(to_tz).isoformat(),
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
            "service": "time-mcp",
            "timestamp": str(datetime.now())
        }
    else:
        return {"error": f"Unknown tool: {name}"}
