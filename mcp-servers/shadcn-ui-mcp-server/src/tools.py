"""
MCP Tools Implementation
"""

from typing import Dict, Any, List
import mcp.types as types
from datetime import datetime
import httpx
from bs4 import BeautifulSoup

def get_tools() -> List[types.Tool]:
    """Define available tools"""
    return [
        types.Tool(
            name="get_component",
            description="Retrieves the source code for a given component.",
            inputSchema={
                "type": "object",
                "properties": {
                    "component_name": {
                        "type": "string",
                        "description": "The name of the component to retrieve."
                    }
                },
                "required": ["component_name"]
            }
        ),
        types.Tool(
            name="get_component_demo",
            description="Retrieves the demo implementation for a given component.",
            inputSchema={
                "type": "object",
                "properties": {
                    "component_name": {
                        "type": "string",
                        "description": "The name of the component to retrieve the demo for."
                    }
                },
                "required": ["component_name"]
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
    if name == "get_component":
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"https://ui.shadcn.com/docs/components/{arguments['component_name']}")
                soup = BeautifulSoup(response.text, "html.parser")
                source_code = soup.find("div", {"class": "language-tsx"}).text
                return {
                    "status": "success",
                    "source_code": source_code,
                    "timestamp": str(datetime.now())
                }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "timestamp": str(datetime.now())
            }
    elif name == "get_component_demo":
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"https://ui.shadcn.com/docs/components/{arguments['component_name']}")
                soup = BeautifulSoup(response.text, "html.parser")
                demo = soup.find("div", {"class": "component-demo"}).prettify()
                return {
                    "status": "success",
                    "demo": demo,
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
            "service": "shadcn-ui-mcp-server",
            "timestamp": str(datetime.now())
        }
    else:
        return {"error": f"Unknown tool: {name}"}
