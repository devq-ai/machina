#!/usr/bin/env python3
"""
Anthropic Claude MCP Server
Real MCP protocol implementation with Anthropic API integration
"""

import json
import os
import sys
from typing import Any, Dict, List, Optional
import asyncio
import logging

try:
    import httpx
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
except ImportError:
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", 
                   "mcp", "httpx", "--break-system-packages"], 
                   capture_output=True)
    import httpx
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent

logger = logging.getLogger(__name__)

class AnthropicMCPServer:
    """Production Anthropic MCP Server with real Claude API integration."""
    
    def __init__(self):
        self.server = Server("anthropic-mcp")
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        self.base_url = "https://api.anthropic.com"
        
        # Register MCP tools
        self._register_tools()

    def _register_tools(self):
        """Register all Anthropic MCP tools."""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            return [
                Tool(
                    name="create_message",
                    description="Create a message with Claude",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "messages": {"type": "array", "description": "List of messages"},
                            "model": {"type": "string", "description": "Model to use", "default": "claude-3-sonnet-20240229"},
                            "max_tokens": {"type": "integer", "description": "Maximum tokens", "default": 1000},
                            "temperature": {"type": "number", "description": "Temperature", "default": 0.0},
                            "system": {"type": "string", "description": "System prompt"}
                        },
                        "required": ["messages"]
                    }
                ),
                Tool(
                    name="list_models",
                    description="List available Claude models",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="count_tokens",
                    description="Count tokens in text",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "text": {"type": "string", "description": "Text to count tokens for"},
                            "model": {"type": "string", "description": "Model to use for counting", "default": "claude-3-sonnet-20240229"}
                        },
                        "required": ["text"]
                    }
                )
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            try:
                if name == "create_message":
                    return await self._create_message(arguments)
                elif name == "list_models":
                    return await self._list_models(arguments)
                elif name == "count_tokens":
                    return await self._count_tokens(arguments)
                else:
                    return [TextContent(type="text", text=f"Unknown tool: {name}")]
                    
            except Exception as e:
                logger.error(f"Tool {name} error: {e}")
                return [TextContent(type="text", text=f"Error executing {name}: {str(e)}")]

    async def _create_message(self, args: Dict[str, Any]) -> List[TextContent]:
        """Create a message with Claude."""
        if not self.api_key:
            return [TextContent(type="text", text="ANTHROPIC_API_KEY environment variable not set")]
            
        messages = args["messages"]
        model = args.get("model", "claude-3-sonnet-20240229")
        max_tokens = args.get("max_tokens", 1000)
        temperature = args.get("temperature", 0.0)
        system = args.get("system")
        
        try:
            headers = {
                "x-api-key": self.api_key,
                "content-type": "application/json",
                "anthropic-version": "2023-06-01"
            }
            
            payload = {
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": messages
            }
            
            if system:
                payload["system"] = system
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/v1/messages",
                    headers=headers,
                    json=payload,
                    timeout=60.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    result = {
                        "id": data.get("id"),
                        "model": data.get("model"),
                        "role": data.get("role"),
                        "content": data.get("content"),
                        "stop_reason": data.get("stop_reason"),
                        "stop_sequence": data.get("stop_sequence"),
                        "usage": data.get("usage")
                    }
                else:
                    result = {
                        "error": f"API request failed: {response.status_code}",
                        "details": response.text
                    }
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Create message error: {str(e)}")]

    async def _list_models(self, args: Dict[str, Any]) -> List[TextContent]:
        """List available Claude models."""
        try:
            # Anthropic models as of 2024
            models = [
                {
                    "id": "claude-3-opus-20240229",
                    "name": "Claude 3 Opus",
                    "description": "Most capable Claude model for complex tasks",
                    "max_tokens": 4096,
                    "context_window": 200000
                },
                {
                    "id": "claude-3-sonnet-20240229", 
                    "name": "Claude 3 Sonnet",
                    "description": "Balanced model for most use cases",
                    "max_tokens": 4096,
                    "context_window": 200000
                },
                {
                    "id": "claude-3-haiku-20240307",
                    "name": "Claude 3 Haiku",
                    "description": "Fastest Claude model for simple tasks",
                    "max_tokens": 4096,
                    "context_window": 200000
                },
                {
                    "id": "claude-2.1",
                    "name": "Claude 2.1",
                    "description": "Previous generation Claude model",
                    "max_tokens": 4096,
                    "context_window": 200000
                },
                {
                    "id": "claude-2.0",
                    "name": "Claude 2.0", 
                    "description": "Earlier Claude model",
                    "max_tokens": 4096,
                    "context_window": 100000
                }
            ]
            
            result = {
                "models": models,
                "total_count": len(models),
                "api_key_configured": bool(self.api_key)
            }
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            return [TextContent(type="text", text=f"List models error: {str(e)}")]

    async def _count_tokens(self, args: Dict[str, Any]) -> List[TextContent]:
        """Count tokens in text (approximation)."""
        text = args["text"]
        model = args.get("model", "claude-3-sonnet-20240229")
        
        try:
            # Rough approximation: 1 token ≈ 4 characters for Claude
            char_count = len(text)
            estimated_tokens = char_count // 4
            
            # Account for different models having slightly different tokenization
            if "opus" in model.lower():
                estimated_tokens = int(estimated_tokens * 1.1)
            elif "haiku" in model.lower():
                estimated_tokens = int(estimated_tokens * 0.9)
            
            result = {
                "text": text[:100] + "..." if len(text) > 100 else text,
                "character_count": char_count,
                "estimated_tokens": estimated_tokens,
                "model": model,
                "note": "This is an approximation. Actual token count may vary."
            }
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Count tokens error: {str(e)}")]

async def main():
    """Run the Anthropic MCP server."""
    server = AnthropicMCPServer()
    
    async with stdio_server() as (read_stream, write_stream):
        await server.server.run(
            read_stream,
            write_stream,
            server.server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())