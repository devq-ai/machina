"""
MCP Tools Implementation
"""

from typing import Dict, Any, List
import mcp.types as types
from datetime import datetime
from bright_data import BrightData
import os

def get_brightdata_client():
    """Get a BrightData client."""
    return BrightData(
        api_key=os.environ.get("BRIGHTDATA_API_KEY")
    )

def get_tools() -> List[types.Tool]:
    """Define available tools"""
    return [
        types.Tool(
            name="web_search",
            description="Searches the web for a given query.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The query to search for."
                    }
                },
                "required": ["query"]
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
    brightdata = get_brightdata_client()
    if name == "web_search":
        try:
            results = brightdata.search(arguments["query"])
            return {
                "status": "success",
                "results": results,
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
            "service": "brightdata-mcp",
            "timestamp": str(datetime.now())
        }
    else:
        return {"error": f"Unknown tool: {name}"}
