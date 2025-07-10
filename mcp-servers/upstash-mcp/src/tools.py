"""
MCP Tools Implementation
"""

from typing import Dict, Any, List
import mcp.types as types
from datetime import datetime
from upstash_redis import Redis
from sentence_transformers import SentenceTransformer

def get_upstash_client():
    """Get an Upstash client."""
    return Redis.from_env()

def get_tools() -> List[types.Tool]:
    """Define available tools"""
    return [
        types.Tool(
            name="redis_set",
            description="Set a key-value pair in Redis",
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Redis key"},
                    "value": {"type": "string", "description": "Value to store"},
                },
                "required": ["key", "value"]
            }
        ),
        types.Tool(
            name="redis_get",
            description="Get value by key from Redis",
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Redis key"}
                },
                "required": ["key"]
            }
        ),
        types.Tool(
            name="create_embedding",
            description="Create embedding from text.",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to embed"}
                },
                "required": ["text"]
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
    upstash = get_upstash_client()
    if name == "redis_set":
        try:
            upstash.set(arguments["key"], arguments["value"])
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
    elif name == "redis_get":
        try:
            value = upstash.get(arguments["key"])
            return {
                "status": "success",
                "value": value,
                "timestamp": str(datetime.now())
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "timestamp": str(datetime.now())
            }
    elif name == "create_embedding":
        try:
            model = SentenceTransformer('all-MiniLM-L6-v2')
            embedding = model.encode(arguments["text"])
            return {
                "status": "success",
                "embedding": embedding.tolist(),
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
            "service": "upstash-mcp",
            "timestamp": str(datetime.now())
        }
    else:
        return {"error": f"Unknown tool: {name}"}
