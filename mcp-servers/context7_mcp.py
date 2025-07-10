#!/usr/bin/env python3
"""
Context7 MCP Server
Advanced context management and semantic search with vector embeddings using FastMCP framework.
"""

import asyncio
import json
import os
import hashlib
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add parent directory to path for FastMCP imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastmcp import FastMCP
import logfire

try:
    import httpx
    import numpy as np
    from pydantic import BaseModel, Field
    CONTEXT7_DEPS_AVAILABLE = True
except ImportError:
    CONTEXT7_DEPS_AVAILABLE = False
    httpx = None
    np = None
    BaseModel = object
    def Field(*args, **kwargs):
        return None


class ContextEntry(BaseModel if CONTEXT7_DEPS_AVAILABLE else object):
    """Context entry model"""
    id: Optional[str] = Field(None, description="Unique context ID")
    content: str = Field(..., description="Context content")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Context metadata")
    tags: List[str] = Field(default_factory=list, description="Context tags")
    embedding: Optional[List[float]] = Field(None, description="Vector embedding")
    similarity_threshold: float = Field(0.8, description="Similarity threshold for matching")
    created_at: Optional[str] = Field(None, description="Creation timestamp")


class Context7MCP:
    """
    Context7 MCP Server using FastMCP framework

    Provides advanced context management operations including:
    - Vector-based semantic search
    - Context storage and retrieval
    - Similarity matching
    - Context clustering
    - Embedding generation
    - Context recommendation
    """

    def __init__(self):
        self.mcp = FastMCP("context7-mcp", version="1.0.0",
                          description="Advanced context management and semantic search with vector embeddings")
        self.redis_url = os.getenv("UPSTASH_REDIS_REST_URL")
        self.redis_token = os.getenv("UPSTASH_REDIS_REST_TOKEN")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002")
        self.http_client: Optional[httpx.AsyncClient] = None
        self.contexts: Dict[str, ContextEntry] = {}
        self._setup_tools()
        self._initialize_client()

    def _initialize_client(self):
        """Initialize Context7 client and connections"""
        if not CONTEXT7_DEPS_AVAILABLE:
            logfire.warning("Context7 dependencies not available. Install with: pip install httpx numpy pydantic")
            return

        try:
            # Initialize HTTP client for API calls
            self.http_client = httpx.AsyncClient(timeout=30.0)

            if self.redis_url and self.redis_token:
                logfire.info("Context7 with Redis backend initialized")
            else:
                logfire.warning("Redis credentials not provided. Using in-memory storage only")

            if self.openai_api_key:
                logfire.info("OpenAI embeddings available")
            else:
                logfire.warning("OpenAI API key not provided. Embedding features limited")

        except Exception as e:
            logfire.error(f"Failed to initialize Context7 client: {str(e)}")

    def _generate_id(self, content: str) -> str:
        """Generate unique ID for context entry"""
        return hashlib.sha256(f"{content}{datetime.utcnow().isoformat()}".encode()).hexdigest()[:16]

    async def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate vector embedding for text"""
        if not self.openai_api_key or not self.http_client:
            return None

        try:
            response = await self.http_client.post(
                "https://api.openai.com/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {self.openai_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "input": text,
                    "model": self.embedding_model
                }
            )
            response.raise_for_status()
            data = response.json()
            return data["data"][0]["embedding"]
        except Exception as e:
            logfire.error(f"Failed to generate embedding: {str(e)}")
            return None

    def _calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate cosine similarity between two embeddings"""
        if not embedding1 or not embedding2 or not np:
            return 0.0

        try:
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)

            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            return dot_product / (norm1 * norm2)
        except Exception as e:
            logfire.error(f"Failed to calculate similarity: {str(e)}")
            return 0.0

    async def _store_in_redis(self, key: str, data: Dict[str, Any]) -> bool:
        """Store data in Redis"""
        if not self.redis_url or not self.redis_token or not self.http_client:
            return False

        try:
            response = await self.http_client.post(
                f"{self.redis_url}/set/{key}",
                headers={"Authorization": f"Bearer {self.redis_token}"},
                json={"value": json.dumps(data)}
            )
            return response.status_code == 200
        except Exception as e:
            logfire.error(f"Failed to store in Redis: {str(e)}")
            return False

    async def _get_from_redis(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve data from Redis"""
        if not self.redis_url or not self.redis_token or not self.http_client:
            return None

        try:
            response = await self.http_client.get(
                f"{self.redis_url}/get/{key}",
                headers={"Authorization": f"Bearer {self.redis_token}"}
            )
            if response.status_code == 200:
                data = response.json()
                return json.loads(data.get("result", "{}"))
            return None
        except Exception as e:
            logfire.error(f"Failed to get from Redis: {str(e)}")
            return None

    def _setup_tools(self):
        """Setup Context7 MCP tools"""

        @self.mcp.tool(
            name="store_context",
            description="Store context with semantic search capabilities",
            input_schema={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Context content to store"},
                    "metadata": {"type": "object", "description": "Additional metadata"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Context tags"},
                    "similarity_threshold": {"type": "number", "description": "Similarity threshold for matching", "default": 0.8}
                },
                "required": ["content"]
            }
        )
        async def store_context(content: str, metadata: Dict[str, Any] = None,
                              tags: List[str] = None, similarity_threshold: float = 0.8) -> Dict[str, Any]:
            """Store context with vector embedding"""
            try:
                context_id = self._generate_id(content)
                created_at = datetime.utcnow().isoformat()

                # Generate embedding
                embedding = await self._generate_embedding(content)

                context_entry = {
                    "id": context_id,
                    "content": content,
                    "metadata": metadata or {},
                    "tags": tags or [],
                    "embedding": embedding,
                    "similarity_threshold": similarity_threshold,
                    "created_at": created_at
                }

                # Store in memory
                if CONTEXT7_DEPS_AVAILABLE:
                    self.contexts[context_id] = ContextEntry(**context_entry)
                else:
                    self.contexts[context_id] = context_entry

                # Store in Redis if available
                await self._store_in_redis(f"context:{context_id}", context_entry)

                return {
                    "context_id": context_id,
                    "status": "stored",
                    "content": content,
                    "has_embedding": embedding is not None,
                    "metadata": metadata or {},
                    "tags": tags or [],
                    "created_at": created_at
                }

            except Exception as e:
                logfire.error(f"Failed to store context: {str(e)}")
                return {"error": f"Context storage failed: {str(e)}"}

        @self.mcp.tool(
            name="search_contexts",
            description="Search contexts using semantic similarity",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "similarity_threshold": {"type": "number", "description": "Minimum similarity score", "default": 0.7},
                    "max_results": {"type": "integer", "description": "Maximum number of results", "default": 10},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Filter by tags"}
                },
                "required": ["query"]
            }
        )
        async def search_contexts(query: str, similarity_threshold: float = 0.7,
                                max_results: int = 10, tags: List[str] = None) -> Dict[str, Any]:
            """Search contexts using semantic similarity"""
            try:
                # Generate query embedding
                query_embedding = await self._generate_embedding(query)

                results = []

                for context_id, context_entry in self.contexts.items():
                    # Extract context data
                    if CONTEXT7_DEPS_AVAILABLE and hasattr(context_entry, 'content'):
                        content = context_entry.content
                        entry_tags = context_entry.tags
                        embedding = context_entry.embedding
                        metadata = context_entry.metadata
                        created_at = context_entry.created_at
                    else:
                        content = context_entry.get('content', '')
                        entry_tags = context_entry.get('tags', [])
                        embedding = context_entry.get('embedding')
                        metadata = context_entry.get('metadata', {})
                        created_at = context_entry.get('created_at')

                    # Filter by tags if specified
                    if tags:
                        if not any(tag in entry_tags for tag in tags):
                            continue

                    # Calculate similarity
                    similarity = 0.0
                    if query_embedding and embedding:
                        similarity = self._calculate_similarity(query_embedding, embedding)
                    else:
                        # Fallback to text-based similarity
                        similarity = 1.0 if query.lower() in content.lower() else 0.0

                    if similarity >= similarity_threshold:
                        results.append({
                            "context_id": context_id,
                            "content": content,
                            "similarity": similarity,
                            "metadata": metadata,
                            "tags": entry_tags,
                            "created_at": created_at
                        })

                # Sort by similarity and limit results
                results.sort(key=lambda x: x["similarity"], reverse=True)
                results = results[:max_results]

                return {
                    "query": query,
                    "results": results,
                    "total_found": len(results),
                    "similarity_threshold": similarity_threshold,
                    "has_embeddings": query_embedding is not None
                }

            except Exception as e:
                logfire.error(f"Failed to search contexts: {str(e)}")
                return {"error": f"Context search failed: {str(e)}"}

        @self.mcp.tool(
            name="get_context",
            description="Retrieve a specific context by ID",
            input_schema={
                "type": "object",
                "properties": {
                    "context_id": {"type": "string", "description": "Context ID to retrieve"}
                },
                "required": ["context_id"]
            }
        )
        async def get_context(context_id: str) -> Dict[str, Any]:
            """Retrieve a specific context by ID"""
            try:
                # Try memory first
                if context_id in self.contexts:
                    context_entry = self.contexts[context_id]

                    if CONTEXT7_DEPS_AVAILABLE and hasattr(context_entry, 'content'):
                        return {
                            "context_id": context_id,
                            "content": context_entry.content,
                            "metadata": context_entry.metadata,
                            "tags": context_entry.tags,
                            "has_embedding": context_entry.embedding is not None,
                            "similarity_threshold": context_entry.similarity_threshold,
                            "created_at": context_entry.created_at
                        }
                    else:
                        return {
                            "context_id": context_id,
                            "content": context_entry.get('content', ''),
                            "metadata": context_entry.get('metadata', {}),
                            "tags": context_entry.get('tags', []),
                            "has_embedding": context_entry.get('embedding') is not None,
                            "similarity_threshold": context_entry.get('similarity_threshold', 0.8),
                            "created_at": context_entry.get('created_at')
                        }

                # Try Redis if not in memory
                redis_data = await self._get_from_redis(f"context:{context_id}")
                if redis_data:
                    # Store back in memory
                    if CONTEXT7_DEPS_AVAILABLE:
                        self.contexts[context_id] = ContextEntry(**redis_data)
                    else:
                        self.contexts[context_id] = redis_data

                    return {
                        "context_id": context_id,
                        "content": redis_data.get('content', ''),
                        "metadata": redis_data.get('metadata', {}),
                        "tags": redis_data.get('tags', []),
                        "has_embedding": redis_data.get('embedding') is not None,
                        "similarity_threshold": redis_data.get('similarity_threshold', 0.8),
                        "created_at": redis_data.get('created_at')
                    }

                return {"error": f"Context with ID '{context_id}' not found"}

            except Exception as e:
                logfire.error(f"Failed to get context: {str(e)}")
                return {"error": f"Context retrieval failed: {str(e)}"}

        @self.mcp.tool(
            name="delete_context",
            description="Delete a specific context",
            input_schema={
                "type": "object",
                "properties": {
                    "context_id": {"type": "string", "description": "Context ID to delete"}
                },
                "required": ["context_id"]
            }
        )
        async def delete_context(context_id: str) -> Dict[str, Any]:
            """Delete a specific context"""
            try:
                # Remove from memory
                if context_id in self.contexts:
                    del self.contexts[context_id]

                    # Remove from Redis if available
                    if self.redis_url and self.redis_token and self.http_client:
                        await self.http_client.delete(
                            f"{self.redis_url}/del/context:{context_id}",
                            headers={"Authorization": f"Bearer {self.redis_token}"}
                        )

                    return {
                        "context_id": context_id,
                        "status": "deleted"
                    }
                else:
                    return {"error": f"Context with ID '{context_id}' not found"}

            except Exception as e:
                logfire.error(f"Failed to delete context: {str(e)}")
                return {"error": f"Context deletion failed: {str(e)}"}

        @self.mcp.tool(
            name="find_similar_contexts",
            description="Find contexts similar to a given context",
            input_schema={
                "type": "object",
                "properties": {
                    "context_id": {"type": "string", "description": "Reference context ID"},
                    "similarity_threshold": {"type": "number", "description": "Minimum similarity score", "default": 0.8},
                    "max_results": {"type": "integer", "description": "Maximum number of results", "default": 5}
                },
                "required": ["context_id"]
            }
        )
        async def find_similar_contexts(context_id: str, similarity_threshold: float = 0.8,
                                      max_results: int = 5) -> Dict[str, Any]:
            """Find contexts similar to a given context"""
            try:
                # Get reference context
                if context_id not in self.contexts:
                    return {"error": f"Reference context '{context_id}' not found"}

                reference_context = self.contexts[context_id]

                if CONTEXT7_DEPS_AVAILABLE and hasattr(reference_context, 'embedding'):
                    reference_embedding = reference_context.embedding
                else:
                    reference_embedding = reference_context.get('embedding')

                if not reference_embedding:
                    return {"error": "Reference context has no embedding for similarity calculation"}

                similar_contexts = []

                for other_id, other_context in self.contexts.items():
                    if other_id == context_id:
                        continue

                    if CONTEXT7_DEPS_AVAILABLE and hasattr(other_context, 'embedding'):
                        other_embedding = other_context.embedding
                        content = other_context.content
                        metadata = other_context.metadata
                        tags = other_context.tags
                    else:
                        other_embedding = other_context.get('embedding')
                        content = other_context.get('content', '')
                        metadata = other_context.get('metadata', {})
                        tags = other_context.get('tags', [])

                    if other_embedding:
                        similarity = self._calculate_similarity(reference_embedding, other_embedding)

                        if similarity >= similarity_threshold:
                            similar_contexts.append({
                                "context_id": other_id,
                                "content": content,
                                "similarity": similarity,
                                "metadata": metadata,
                                "tags": tags
                            })

                # Sort by similarity and limit results
                similar_contexts.sort(key=lambda x: x["similarity"], reverse=True)
                similar_contexts = similar_contexts[:max_results]

                return {
                    "reference_context_id": context_id,
                    "similar_contexts": similar_contexts,
                    "total_found": len(similar_contexts),
                    "similarity_threshold": similarity_threshold
                }

            except Exception as e:
                logfire.error(f"Failed to find similar contexts: {str(e)}")
                return {"error": f"Similar context search failed: {str(e)}"}

        @self.mcp.tool(
            name="list_contexts",
            description="List all stored contexts with optional filtering",
            input_schema={
                "type": "object",
                "properties": {
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Filter by tags"},
                    "limit": {"type": "integer", "description": "Maximum number of results", "default": 50}
                }
            }
        )
        async def list_contexts(tags: List[str] = None, limit: int = 50) -> Dict[str, Any]:
            """List all stored contexts"""
            try:
                contexts_list = []

                for context_id, context_entry in self.contexts.items():
                    if CONTEXT7_DEPS_AVAILABLE and hasattr(context_entry, 'content'):
                        content = context_entry.content
                        entry_tags = context_entry.tags
                        metadata = context_entry.metadata
                        created_at = context_entry.created_at
                        has_embedding = context_entry.embedding is not None
                    else:
                        content = context_entry.get('content', '')
                        entry_tags = context_entry.get('tags', [])
                        metadata = context_entry.get('metadata', {})
                        created_at = context_entry.get('created_at')
                        has_embedding = context_entry.get('embedding') is not None

                    # Filter by tags if specified
                    if tags:
                        if not any(tag in entry_tags for tag in tags):
                            continue

                    contexts_list.append({
                        "context_id": context_id,
                        "content": content[:200] + "..." if len(content) > 200 else content,
                        "tags": entry_tags,
                        "metadata": metadata,
                        "has_embedding": has_embedding,
                        "created_at": created_at
                    })

                # Sort by creation date (newest first) and limit
                contexts_list.sort(key=lambda x: x.get("created_at", ""), reverse=True)
                contexts_list = contexts_list[:limit]

                return {
                    "contexts": contexts_list,
                    "total_count": len(contexts_list),
                    "total_stored": len(self.contexts),
                    "filter_tags": tags
                }

            except Exception as e:
                logfire.error(f"Failed to list contexts: {str(e)}")
                return {"error": f"Context listing failed: {str(e)}"}

        @self.mcp.tool(
            name="get_context_stats",
            description="Get Context7 system statistics",
            input_schema={
                "type": "object",
                "properties": {}
            }
        )
        async def get_context_stats() -> Dict[str, Any]:
            """Get Context7 system statistics"""
            try:
                total_contexts = len(self.contexts)
                contexts_with_embeddings = 0
                unique_tags = set()

                for context_entry in self.contexts.values():
                    if CONTEXT7_DEPS_AVAILABLE and hasattr(context_entry, 'embedding'):
                        if context_entry.embedding:
                            contexts_with_embeddings += 1
                        unique_tags.update(context_entry.tags)
                    else:
                        if context_entry.get('embedding'):
                            contexts_with_embeddings += 1
                        unique_tags.update(context_entry.get('tags', []))

                return {
                    "total_contexts": total_contexts,
                    "contexts_with_embeddings": contexts_with_embeddings,
                    "embedding_coverage_percent": round((contexts_with_embeddings / total_contexts * 100), 2) if total_contexts > 0 else 0,
                    "unique_tags": list(unique_tags),
                    "total_unique_tags": len(unique_tags),
                    "redis_connected": self.redis_url is not None and self.redis_token is not None,
                    "openai_available": self.openai_api_key is not None,
                    "embedding_model": self.embedding_model
                }

            except Exception as e:
                logfire.error(f"Failed to get context stats: {str(e)}")
                return {"error": f"Context stats query failed: {str(e)}"}

    def _check_client(self) -> bool:
        """Check if Context7 client is available"""
        return CONTEXT7_DEPS_AVAILABLE

    async def run(self):
        """Run the Context7 MCP server"""
        try:
            await self.mcp.run_stdio()
        finally:
            if self.http_client:
                await self.http_client.aclose()


async def main():
    """Main entry point"""
    server = Context7MCP()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
