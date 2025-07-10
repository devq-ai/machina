#!/usr/bin/env python3
"""
Upstash MCP Server - Production Implementation
Provides Redis and vector database operations through Upstash cloud services.
"""

import os
import json
import asyncio
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import hashlib

try:
    import httpx
    import numpy as np
    from pydantic import BaseModel, Field
except ImportError:
    print("Installing required dependencies...")
    import subprocess
    subprocess.check_call(["pip", "install", "httpx", "numpy", "pydantic"])
    import httpx
    import numpy as np
    from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MCP Protocol Constants
JSONRPC_VERSION = "2.0"
MCP_VERSION = "2024-11-05"


class MCPError:
    """Standard MCP error codes"""
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603


class UpstashConfig(BaseModel):
    """Upstash configuration"""
    redis_url: str = Field(default="", description="Upstash Redis REST URL")
    redis_token: str = Field(default="", description="Upstash Redis REST token")
    vector_url: str = Field(default="", description="Upstash Vector REST URL")
    vector_token: str = Field(default="", description="Upstash Vector REST token")

    @classmethod
    def from_env(cls) -> "UpstashConfig":
        """Load configuration from environment variables"""
        return cls(
            redis_url=os.getenv("UPSTASH_REDIS_REST_URL", ""),
            redis_token=os.getenv("UPSTASH_REDIS_REST_TOKEN", ""),
            vector_url=os.getenv("UPSTASH_VECTOR_REST_URL", ""),
            vector_token=os.getenv("UPSTASH_VECTOR_REST_TOKEN", "")
        )


class UpstashClient:
    """Upstash REST API client"""

    def __init__(self, config: UpstashConfig):
        self.config = config
        self.http_client = httpx.AsyncClient(timeout=30.0)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.http_client.aclose()

    def _get_redis_headers(self) -> Dict[str, str]:
        """Get headers for Redis REST API"""
        return {
            "Authorization": f"Bearer {self.config.redis_token}",
            "Content-Type": "application/json"
        }

    def _get_vector_headers(self) -> Dict[str, str]:
        """Get headers for Vector REST API"""
        return {
            "Authorization": f"Bearer {self.config.vector_token}",
            "Content-Type": "application/json"
        }

    async def redis_command(self, command: List[str]) -> Any:
        """Execute Redis command via REST API"""
        try:
            response = await self.http_client.post(
                self.config.redis_url,
                headers=self._get_redis_headers(),
                json=command
            )
            response.raise_for_status()
            data = response.json()
            return data.get("result")
        except Exception as e:
            logger.error(f"Redis command error: {e}")
            raise

    async def vector_upsert(self, vectors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Upsert vectors to Upstash Vector"""
        try:
            response = await self.http_client.post(
                f"{self.config.vector_url}/upsert",
                headers=self._get_vector_headers(),
                json={"vectors": vectors}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Vector upsert error: {e}")
            raise

    async def vector_query(self, vector: List[float], top_k: int = 10,
                          include_metadata: bool = True) -> Dict[str, Any]:
        """Query vectors from Upstash Vector"""
        try:
            response = await self.http_client.post(
                f"{self.config.vector_url}/query",
                headers=self._get_vector_headers(),
                json={
                    "vector": vector,
                    "topK": top_k,
                    "includeMetadata": include_metadata
                }
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Vector query error: {e}")
            raise


class UpstashMCPServer:
    """Upstash MCP Server implementation"""

    def __init__(self):
        self.config = UpstashConfig.from_env()
        self.client: Optional[UpstashClient] = None
        self.server_info = {
            "name": "upstash-mcp",
            "version": "1.0.0",
            "description": "Upstash Redis and Vector database operations",
            "author": "DevQ.ai Team"
        }

    async def initialize(self):
        """Initialize the server"""
        self.client = UpstashClient(self.config)
        await self.client.__aenter__()
        logger.info("Upstash MCP Server initialized")

    async def cleanup(self):
        """Cleanup resources"""
        if self.client:
            await self.client.__aexit__(None, None, None)

    def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools"""
        return [
            {
                "name": "redis_set",
                "description": "Set a key-value pair in Redis",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string", "description": "Redis key"},
                        "value": {"type": "string", "description": "Value to store"},
                        "ttl": {"type": "integer", "description": "TTL in seconds (optional)"}
                    },
                    "required": ["key", "value"]
                }
            },
            {
                "name": "redis_get",
                "description": "Get value by key from Redis",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string", "description": "Redis key"}
                    },
                    "required": ["key"]
                }
            },
            {
                "name": "redis_delete",
                "description": "Delete key(s) from Redis",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "keys": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Keys to delete"
                        }
                    },
                    "required": ["keys"]
                }
            },
            {
                "name": "redis_list_push",
                "description": "Push values to a Redis list",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string", "description": "List key"},
                        "values": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Values to push"
                        },
                        "direction": {
                            "type": "string",
                            "enum": ["left", "right"],
                            "description": "Push direction (default: right)"
                        }
                    },
                    "required": ["key", "values"]
                }
            },
            {
                "name": "redis_hash_set",
                "description": "Set fields in a Redis hash",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string", "description": "Hash key"},
                        "fields": {
                            "type": "object",
                            "description": "Field-value pairs to set"
                        }
                    },
                    "required": ["key", "fields"]
                }
            },
            {
                "name": "vector_store",
                "description": "Store vectors with metadata",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "vectors": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string"},
                                    "vector": {
                                        "type": "array",
                                        "items": {"type": "number"}
                                    },
                                    "metadata": {"type": "object"}
                                },
                                "required": ["id", "vector"]
                            }
                        }
                    },
                    "required": ["vectors"]
                }
            },
            {
                "name": "vector_search",
                "description": "Search similar vectors",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query_vector": {
                            "type": "array",
                            "items": {"type": "number"},
                            "description": "Query vector"
                        },
                        "top_k": {
                            "type": "integer",
                            "description": "Number of results (default: 10)"
                        },
                        "include_metadata": {
                            "type": "boolean",
                            "description": "Include metadata (default: true)"
                        }
                    },
                    "required": ["query_vector"]
                }
            },
            {
                "name": "create_embedding",
                "description": "Create embedding from text (mock implementation)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Text to embed"},
                        "dimension": {
                            "type": "integer",
                            "description": "Embedding dimension (default: 384)"
                        }
                    },
                    "required": ["text"]
                }
            }
        ]

    async def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tool execution"""
        try:
            if tool_name == "redis_set":
                return await self._redis_set(arguments)
            elif tool_name == "redis_get":
                return await self._redis_get(arguments)
            elif tool_name == "redis_delete":
                return await self._redis_delete(arguments)
            elif tool_name == "redis_list_push":
                return await self._redis_list_push(arguments)
            elif tool_name == "redis_hash_set":
                return await self._redis_hash_set(arguments)
            elif tool_name == "vector_store":
                return await self._vector_store(arguments)
            elif tool_name == "vector_search":
                return await self._vector_search(arguments)
            elif tool_name == "create_embedding":
                return await self._create_embedding(arguments)
            else:
                raise ValueError(f"Unknown tool: {tool_name}")
        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return {"error": str(e)}

    async def _redis_set(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Set key-value in Redis"""
        key = args["key"]
        value = args["value"]
        ttl = args.get("ttl")

        if ttl:
            result = await self.client.redis_command(["SETEX", key, str(ttl), value])
        else:
            result = await self.client.redis_command(["SET", key, value])

        return {
            "success": result == "OK",
            "key": key,
            "ttl": ttl
        }

    async def _redis_get(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get value from Redis"""
        key = args["key"]
        value = await self.client.redis_command(["GET", key])

        return {
            "key": key,
            "value": value,
            "exists": value is not None
        }

    async def _redis_delete(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Delete keys from Redis"""
        keys = args["keys"]
        deleted = await self.client.redis_command(["DEL"] + keys)

        return {
            "deleted": deleted,
            "keys": keys
        }

    async def _redis_list_push(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Push to Redis list"""
        key = args["key"]
        values = args["values"]
        direction = args.get("direction", "right")

        command = "LPUSH" if direction == "left" else "RPUSH"
        length = await self.client.redis_command([command, key] + values)

        return {
            "key": key,
            "length": length,
            "pushed": len(values)
        }

    async def _redis_hash_set(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Set hash fields in Redis"""
        key = args["key"]
        fields = args["fields"]

        # Flatten fields dict for HSET command
        field_args = []
        for field, value in fields.items():
            field_args.extend([field, str(value)])

        result = await self.client.redis_command(["HSET", key] + field_args)

        return {
            "key": key,
            "fields_set": result,
            "fields": list(fields.keys())
        }

    async def _vector_store(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Store vectors in Upstash Vector"""
        vectors = args["vectors"]

        # Validate and prepare vectors
        prepared_vectors = []
        for v in vectors:
            prepared_vectors.append({
                "id": v["id"],
                "vector": v["vector"],
                "metadata": v.get("metadata", {})
            })

        result = await self.client.vector_upsert(prepared_vectors)

        return {
            "stored": len(prepared_vectors),
            "result": result
        }

    async def _vector_search(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Search vectors in Upstash Vector"""
        query_vector = args["query_vector"]
        top_k = args.get("top_k", 10)
        include_metadata = args.get("include_metadata", True)

        result = await self.client.vector_query(
            query_vector,
            top_k,
            include_metadata
        )

        return {
            "results": result.get("result", []),
            "count": len(result.get("result", [])),
            "top_k": top_k
        }

    async def _create_embedding(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create text embedding (mock implementation)"""
        text = args["text"]
        dimension = args.get("dimension", 384)

        # Mock embedding generation using hash
        hash_bytes = hashlib.sha256(text.encode()).digest()
        # Generate deterministic pseudo-random values
        np.random.seed(int.from_bytes(hash_bytes[:4], 'big'))
        embedding = np.random.randn(dimension).tolist()

        # Normalize
        norm = np.linalg.norm(embedding)
        embedding = (np.array(embedding) / norm).tolist()

        return {
            "text": text[:50] + "..." if len(text) > 50 else text,
            "embedding": embedding,
            "dimension": dimension,
            "model": "mock-embedding"
        }

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle JSON-RPC request"""
        request_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})

        try:
            if method == "initialize":
                result = {
                    "protocolVersion": MCP_VERSION,
                    "serverInfo": self.server_info,
                    "capabilities": {
                        "tools": True,
                        "resources": False,
                        "prompts": False,
                        "logging": False
                    },
                    "instructions": "Upstash MCP server for Redis and Vector operations"
                }
            elif method == "tools/list":
                result = {"tools": self.list_tools()}
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                result = await self.handle_tool_call(tool_name, arguments)
            elif method == "health":
                result = {
                    "status": "healthy",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "redis_configured": bool(self.config.redis_url),
                    "vector_configured": bool(self.config.vector_url)
                }
            else:
                return {
                    "jsonrpc": JSONRPC_VERSION,
                    "id": request_id,
                    "error": {
                        "code": MCPError.METHOD_NOT_FOUND,
                        "message": f"Method not found: {method}"
                    }
                }

            return {
                "jsonrpc": JSONRPC_VERSION,
                "id": request_id,
                "result": result
            }

        except Exception as e:
            logger.error(f"Request handling error: {e}")
            return {
                "jsonrpc": JSONRPC_VERSION,
                "id": request_id,
                "error": {
                    "code": MCPError.INTERNAL_ERROR,
                    "message": str(e)
                }
            }

    async def run_stdio(self):
        """Run the server in stdio mode"""
        logger.info("Starting Upstash MCP Server in stdio mode")
        await self.initialize()

        try:
            while True:
                # Read request from stdin
                line = await asyncio.get_event_loop().run_in_executor(
                    None, input
                )

                if not line:
                    continue

                try:
                    request = json.loads(line)
                    response = await self.handle_request(request)

                    # Write response to stdout
                    print(json.dumps(response))

                except json.JSONDecodeError as e:
                    error_response = {
                        "jsonrpc": JSONRPC_VERSION,
                        "id": None,
                        "error": {
                            "code": MCPError.PARSE_ERROR,
                            "message": f"Parse error: {e}"
                        }
                    }
                    print(json.dumps(error_response))

        except KeyboardInterrupt:
            logger.info("Server shutdown requested")
        except Exception as e:
            logger.error(f"Server error: {e}")
        finally:
            await self.cleanup()


async def main():
    """Main entry point"""
    server = UpstashMCPServer()
    await server.run_stdio()


if __name__ == "__main__":
    asyncio.run(main())
