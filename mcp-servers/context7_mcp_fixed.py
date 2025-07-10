#!/usr/bin/env python3
"""
Context7 MCP Server - Fixed Version
Advanced context management and semantic search with vector embeddings using FastMCP framework.
FIXES: Embedding service configuration and error handling
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
    Context7 MCP Server using FastMCP framework - FIXED VERSION

    Provides advanced context management operations including:
    - Vector-based semantic search
    - Context storage and retrieval
    - Similarity matching with fallback
    - Context clustering
    - Embedding generation with error handling
    - Context recommendation
    """

    def __init__(self):
        self.mcp = FastMCP("context7-mcp-fixed", version="1.0.1",
                          description="Advanced context management with vector embeddings - FIXED")

        # Configuration with validation
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.redis_url = os.getenv("UPSTASH_REDIS_REST_URL")
        self.redis_token = os.getenv("UPSTASH_REDIS_REST_TOKEN")
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002")
        self.enable_embeddings = os.getenv("CONTEXT7_ENABLE_EMBEDDINGS", "true").lower() == "true"
        self.fallback_mode = os.getenv("CONTEXT7_FALLBACK_MODE", "true").lower() == "true"
        self.timeout_seconds = int(os.getenv("CONTEXT7_TIMEOUT_SECONDS", "30"))

        self.http_client: Optional[httpx.AsyncClient] = None
        self.contexts: Dict[str, ContextEntry] = {}
        self.embedding_cache: Dict[str, List[float]] = {}

        self._validate_configuration()
        self._setup_tools()
        self._initialize_client()

    def _validate_configuration(self):
        """Validate configuration and log status"""
        config_status = {
            "openai_api_key": "✅" if self.openai_api_key else "❌",
            "redis_url": "✅" if self.redis_url else "❌",
            "redis_token": "✅" if self.redis_token else "❌",
            "dependencies": "✅" if CONTEXT7_DEPS_AVAILABLE else "❌",
            "embeddings_enabled": "✅" if self.enable_embeddings else "⚠️",
            "fallback_mode": "✅" if self.fallback_mode else "⚠️"
        }

        logfire.info("Context7 Configuration Status", config=config_status)

        if not self.openai_api_key and self.enable_embeddings:
            logfire.warning("OpenAI API key not found - embedding features will be limited")
            if not self.fallback_mode:
                logfire.error("Embeddings enabled but no API key and fallback disabled")

        if not CONTEXT7_DEPS_AVAILABLE:
            logfire.error("Required dependencies not available: httpx, numpy, pydantic")

    async def _initialize_client(self):
        """Initialize HTTP client with proper timeout and error handling"""
        if CONTEXT7_DEPS_AVAILABLE:
            self.http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout_seconds),
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
            )
            logfire.info("Context7 HTTP client initialized with enhanced configuration")

    def _generate_id(self, content: str) -> str:
        """Generate unique ID for content"""
        return hashlib.sha256(f"{content}{datetime.utcnow().isoformat()}".encode()).hexdigest()[:16]

    async def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate vector embedding with comprehensive error handling and caching"""

        # Check cache first
        text_hash = hashlib.md5(text.encode()).hexdigest()
        if text_hash in self.embedding_cache:
            logfire.debug("Using cached embedding", text_hash=text_hash)
            return self.embedding_cache[text_hash]

        # Skip if embeddings disabled
        if not self.enable_embeddings:
            logfire.debug("Embeddings disabled, returning None")
            return None

        # Skip if no API key
        if not self.openai_api_key:
            logfire.warning("No OpenAI API key available for embedding generation")
            return None

        # Skip if no HTTP client
        if not self.http_client:
            logfire.warning("No HTTP client available for embedding generation")
            return None

        try:
            logfire.info("Generating embedding", model=self.embedding_model, text_length=len(text))

            response = await self.http_client.post(
                "https://api.openai.com/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {self.openai_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "input": text[:8000],  # Limit text length
                    "model": self.embedding_model
                }
            )

            response.raise_for_status()
            data = response.json()
            embedding = data["data"][0]["embedding"]

            # Cache the embedding
            self.embedding_cache[text_hash] = embedding

            logfire.info("Embedding generated successfully",
                        embedding_dim=len(embedding),
                        text_hash=text_hash)
            return embedding

        except httpx.TimeoutException:
            logfire.error("Embedding generation timed out", timeout=self.timeout_seconds)
            return None
        except httpx.HTTPStatusError as e:
            logfire.error("HTTP error during embedding generation",
                         status_code=e.response.status_code,
                         response_text=e.response.text)
            return None
        except Exception as e:
            logfire.error("Unexpected error during embedding generation", error=str(e))
            return None

    def _calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate cosine similarity with error handling"""
        if not embedding1 or not embedding2 or not np:
            return 0.0

        try:
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)

            # Handle zero vectors
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)

            if norm1 == 0 or norm2 == 0:
                logfire.warning("Zero norm vector encountered in similarity calculation")
                return 0.0

            # Calculate cosine similarity
            dot_product = np.dot(vec1, vec2)
            similarity = dot_product / (norm1 * norm2)

            # Ensure similarity is in valid range
            similarity = max(0.0, min(1.0, float(similarity)))

            return similarity

        except Exception as e:
            logfire.error("Error calculating similarity", error=str(e))
            return 0.0

    def _text_similarity(self, text1: str, text2: str) -> float:
        """Fallback text-based similarity calculation"""
        try:
            text1_lower = text1.lower()
            text2_lower = text2.lower()

            # Simple word overlap similarity
            words1 = set(text1_lower.split())
            words2 = set(text2_lower.split())

            if not words1 or not words2:
                return 0.0

            intersection = words1.intersection(words2)
            union = words1.union(words2)

            similarity = len(intersection) / len(union) if union else 0.0

            # Boost for exact substring matches
            if text1_lower in text2_lower or text2_lower in text1_lower:
                similarity = min(1.0, similarity + 0.2)

            return similarity

        except Exception as e:
            logfire.error("Error in text similarity calculation", error=str(e))
            return 0.0

    def _setup_tools(self):
        """Setup MCP tools with enhanced error handling"""

        @self.mcp.tool()
        async def store_context(content: str, metadata: Dict[str, Any] = None,
                              tags: List[str] = None, similarity_threshold: float = 0.8) -> Dict[str, Any]:
            """Store context with vector embedding and enhanced error handling"""
            try:
                context_id = self._generate_id(content)
                created_at = datetime.utcnow().isoformat()

                # Generate embedding with fallback
                embedding = None
                if self.enable_embeddings:
                    embedding = await self._generate_embedding(content)
                    if embedding is None and not self.fallback_mode:
                        return {
                            "error": "Failed to generate embedding and fallback mode disabled",
                            "context_id": context_id,
                            "status": "failed"
                        }

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

                logfire.info("Context stored successfully",
                           context_id=context_id,
                           has_embedding=embedding is not None,
                           content_length=len(content))

                return {
                    "context_id": context_id,
                    "status": "stored",
                    "content": content,
                    "has_embedding": embedding is not None,
                    "embedding_model": self.embedding_model if embedding else None,
                    "metadata": metadata or {},
                    "tags": tags or [],
                    "created_at": created_at
                }

            except Exception as e:
                logfire.error("Error storing context", error=str(e))
                return {
                    "error": f"Failed to store context: {str(e)}",
                    "status": "failed"
                }

        @self.mcp.tool()
        async def search_contexts(query: str, similarity_threshold: float = 0.7,
                                tags: List[str] = None, limit: int = 10) -> Dict[str, Any]:
            """Search contexts with embedding-based and text-based fallback"""
            try:
                logfire.info("Searching contexts",
                           query=query,
                           threshold=similarity_threshold,
                           tags=tags,
                           limit=limit)

                # Generate query embedding
                query_embedding = None
                if self.enable_embeddings:
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

                    # Tag filtering
                    if tags and not any(tag in entry_tags for tag in tags):
                        continue

                    # Calculate similarity
                    similarity = 0.0
                    similarity_method = "none"

                    if query_embedding and embedding:
                        similarity = self._calculate_similarity(query_embedding, embedding)
                        similarity_method = "embedding"
                    elif self.fallback_mode:
                        # Fallback to text-based similarity
                        similarity = self._text_similarity(query, content)
                        similarity_method = "text"

                    if similarity >= similarity_threshold:
                        results.append({
                            "context_id": context_id,
                            "content": content,
                            "similarity": similarity,
                            "similarity_method": similarity_method,
                            "metadata": metadata,
                            "tags": entry_tags,
                            "created_at": created_at
                        })

                # Sort by similarity and limit results
                results.sort(key=lambda x: x['similarity'], reverse=True)
                results = results[:limit]

                logfire.info("Search completed",
                           results_found=len(results),
                           query_has_embedding=query_embedding is not None)

                return {
                    "query": query,
                    "results": results,
                    "total_found": len(results),
                    "similarity_threshold": similarity_threshold,
                    "has_embeddings": query_embedding is not None,
                    "search_method": "embedding" if query_embedding else "text_fallback"
                }

            except Exception as e:
                logfire.error("Error searching contexts", error=str(e))
                return {
                    "error": f"Search failed: {str(e)}",
                    "query": query,
                    "results": [],
                    "total_found": 0
                }

        @self.mcp.tool()
        async def find_similar_contexts(context_id: str, similarity_threshold: float = 0.8,
                                      limit: int = 5) -> Dict[str, Any]:
            """Find similar contexts with enhanced error handling"""
            try:
                if context_id not in self.contexts:
                    return {"error": f"Reference context '{context_id}' not found"}

                reference_context = self.contexts[context_id]

                # Get reference embedding
                if CONTEXT7_DEPS_AVAILABLE and hasattr(reference_context, 'embedding'):
                    reference_embedding = reference_context.embedding
                    reference_content = reference_context.content
                else:
                    reference_embedding = reference_context.get('embedding')
                    reference_content = reference_context.get('content', '')

                similar_contexts = []

                for other_id, other_context in self.contexts.items():
                    if other_id == context_id:
                        continue

                    # Get other context data
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

                    # Calculate similarity
                    similarity = 0.0
                    similarity_method = "none"

                    if reference_embedding and other_embedding:
                        similarity = self._calculate_similarity(reference_embedding, other_embedding)
                        similarity_method = "embedding"
                    elif self.fallback_mode and reference_content and content:
                        similarity = self._text_similarity(reference_content, content)
                        similarity_method = "text"

                    if similarity >= similarity_threshold:
                        similar_contexts.append({
                            "context_id": other_id,
                            "content": content,
                            "similarity": similarity,
                            "similarity_method": similarity_method,
                            "metadata": metadata,
                            "tags": tags
                        })

                # Sort by similarity and limit
                similar_contexts.sort(key=lambda x: x['similarity'], reverse=True)
                similar_contexts = similar_contexts[:limit]

                logfire.info("Similar contexts found",
                           reference_id=context_id,
                           similar_count=len(similar_contexts),
                           has_reference_embedding=reference_embedding is not None)

                return {
                    "reference_context_id": context_id,
                    "similar_contexts": similar_contexts,
                    "total_found": len(similar_contexts),
                    "similarity_threshold": similarity_threshold,
                    "has_embeddings": reference_embedding is not None
                }

            except Exception as e:
                logfire.error("Error finding similar contexts",
                             context_id=context_id,
                             error=str(e))
                return {
                    "error": f"Failed to find similar contexts: {str(e)}",
                    "reference_context_id": context_id,
                    "similar_contexts": []
                }

        @self.mcp.tool()
        async def get_context7_stats() -> Dict[str, Any]:
            """Get comprehensive Context7 system statistics"""
            try:
                total_contexts = len(self.contexts)
                contexts_with_embeddings = sum(1 for ctx in self.contexts.values()
                                             if (hasattr(ctx, 'embedding') and ctx.embedding) or
                                                (isinstance(ctx, dict) and ctx.get('embedding')))

                config_status = {
                    "embeddings_enabled": self.enable_embeddings,
                    "fallback_mode": self.fallback_mode,
                    "api_key_configured": bool(self.openai_api_key),
                    "redis_configured": bool(self.redis_url and self.redis_token),
                    "dependencies_available": CONTEXT7_DEPS_AVAILABLE
                }

                return {
                    "total_contexts": total_contexts,
                    "contexts_with_embeddings": contexts_with_embeddings,
                    "embedding_coverage_percent": (contexts_with_embeddings / max(total_contexts, 1)) * 100,
                    "embedding_cache_size": len(self.embedding_cache),
                    "embedding_model": self.embedding_model,
                    "configuration": config_status,
                    "version": "1.0.1-fixed",
                    "status": "operational"
                }

            except Exception as e:
                logfire.error("Error getting Context7 stats", error=str(e))
                return {
                    "error": f"Failed to get stats: {str(e)}",
                    "status": "error"
                }

    async def run(self):
        """Run the Context7 MCP server"""
        try:
            logfire.info("Starting Context7 MCP Server - Fixed Version")
            await self.mcp.run()
        except Exception as e:
            logfire.error("Error running Context7 MCP server", error=str(e))
            raise


# Global server instance
context7_server = Context7MCP()

async def main():
    """Main entry point"""
    await context7_server.run()

if __name__ == "__main__":
    asyncio.run(main())
