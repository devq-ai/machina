"""
MCP Tools Implementation
"""

from typing import Dict, Any, List
import mcp.types as types
from datetime import datetime
import agentql
import asyncio
import logging
import os
from playwright.async_api import async_playwright

def get_tools() -> List[types.Tool]:
    """Define available tools"""
    return [
        types.Tool(
            name="agentql_query",
            description="Executes an AgentQL query.",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to start the session on."
                    },
                    "query": {
                        "type": "string",
                        "description": "The AgentQL query to execute."
                    }
                },
                "required": ["url", "query"]
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
    if name == "agentql_query":
        try:
            agentql.configure(api_key=os.environ.get("AGENTQL_API_KEY"))
            async with agentql.Agent() as agent:
                page = await agent.get_page(arguments["url"])
                response = await page.query_data(arguments["query"])
                return {
                    "status": "success",
                    "result": response,
                    "timestamp": str(datetime.now())
                }
        except Exception as e:
            logging.error(e)
            return {
                "status": "error",
                "message": str(e),
                "timestamp": str(datetime.now())
            }
    elif name == "health_check":
        return {
            "status": "healthy",
            "service": "agentql-mcp",
            "timestamp": str(datetime.now())
        }
    else:
        return {"error": f"Unknown tool: {name}"}
