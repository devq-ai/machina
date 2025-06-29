"""
MCP Tools Implementation
"""

from typing import Dict, Any, List
import mcp.types as types
from datetime import datetime
from scholarly import scholarly

def get_tools() -> List[types.Tool]:
    """Define available tools"""
    return [
        types.Tool(
            name="search_arxiv",
            description="Search arxiv for articles related to the given keyword.",
            inputSchema={
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "The keyword to search for."
                    }
                },
                "required": ["keyword"]
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
    if name == "search_arxiv":
        try:
            search_query = scholarly.search_pubs(arguments["keyword"])
            results = [next(search_query) for _ in range(5)]
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
            "service": "scholarly-mcp",
            "timestamp": str(datetime.now())
        }
    else:
        return {"error": f"Unknown tool: {name}"}
