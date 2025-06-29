"""
MCP Tools Implementation
"""

from typing import Dict, Any, List
import mcp.types as types
from datetime import datetime
from pyppeteer import launch

async def get_browser():
    """Get a browser instance."""
    return await launch()

def get_tools() -> List[types.Tool]:
    """Define available tools"""
    return [
        types.Tool(
            name="puppeteer_navigate",
            description="Navigate to a URL.",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to navigate to."
                    }
                },
                "required": ["url"]
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
    if name == "puppeteer_navigate":
        try:
            browser = await get_browser()
            page = await browser.newPage()
            await page.goto(arguments["url"])
            await browser.close()
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
            "service": "puppeteer-mcp",
            "timestamp": str(datetime.now())
        }
    else:
        return {"error": f"Unknown tool: {name}"}
