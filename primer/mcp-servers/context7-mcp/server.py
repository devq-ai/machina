#!/usr/bin/env python3
"""
Context7 MCP Server

Advanced context management and semantic search server implementing the MCP protocol.
Provides intelligent context storage, retrieval, semantic search with vector embeddings,
and Redis-backed persistence for AI-enhanced development workflows.

This implementation follows DevQ.ai standards with comprehensive MCP integration,
async operations, structured logging, and robust error handling.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import sys
import os
from urllib.parse import urlparse

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

try:
    from mcp import types
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from pydantic import BaseModel, Field, field_validator
    import aiofiles
    import asyncio
    import httpx
    import redis.asyncio as redis
    from sentence_transformers import SentenceTransformer
    import numpy as np
    from sklearn.metrics.pairwise import cosine_similarity
    import tiktoken
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Please ensure redis, sentence-transformers, scikit-learn, tiktoken, and other dependencies are installed")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
MAX_CONTEXT_SIZE = 32000  # Token limit for context
MAX_DOCUMENT_SIZE = 10000  # Maximum document size in tokens
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # Lightweight, fast embedding model
REDIS_KEY_PREFIX = "context7:"
VECTOR_DIMENSION = 384  # Dimension for all-MiniLM-L6-v2 model
SIMILARITY_THRESHOLD = 0.7  # Minimum similarity for relevant results
MAX_RESULTS = 10  # Maximum number of search results to return

class ContextDocument(BaseModel):
    """Represents a document stored in the context system."""
    id: str = Field(description="Unique document identifier")
    content: str = Field(description="Document content")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Document metadata")
    embedding: Optional[List[float]] = Field(default=None, description="Vector embedding")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    tags: List[str] = Field(default_factory=list, description="Document tags")
    token_count: int = Field(default=0, description="Token count of content")

class SearchResult(BaseModel):
    """Represents a search result with similarity score."""
    document: ContextDocument
    similarity: float
    snippet: str = Field(description="Relevant snippet from document")

class ContextQuery(BaseModel):
    """Represents a context query with parameters."""
    query: str = Field(description="Search query")
    max_results: int = Field(default=5, description="Maximum number of results")
    min_similarity: float = Field(default=0.7, description="Minimum similarity threshold")
    tags: List[str] = Field(default_factory=list, description="Filter by tags")
    include_metadata: bool = Field(default=True, description="Include metadata in results")

class Context7Server:
    """Context7 MCP Server implementation."""

    def __init__(self):
        self.server = Server("context7-mcp")
        self.redis_client: Optional[redis.Redis] = None
        self.embedding_model: Optional[SentenceTransformer] = None
        self.tokenizer = None
        self.setup_handlers()

    def setup_handlers(self):
        """Set up MCP message handlers."""

        @self.server.list_tools()
        async def list_tools() -> List[types.Tool]:
            """List available tools."""
            return [
                types.Tool(
                    name="context7_status",
                    description="Check Context7 server status and connection health",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                types.Tool(
                    name="store_document",
                    description="Store a document with semantic embeddings for later retrieval",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "content": {
                                "type": "string",
                                "description": "Document content to store"
                            },
                            "metadata": {
                                "type": "object",
                                "description": "Optional metadata for the document",
                                "default": {}
                            },
                            "tags": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Tags for categorizing the document",
                                "default": []
                            },
                            "document_id": {
                                "type": "string",
                                "description": "Optional custom document ID",
                                "default": None
                            }
                        },
                        "required": ["content"]
                    }
                ),
                types.Tool(
                    name="search_context",
                    description="Search stored documents using semantic similarity",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query"
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum number of results to return",
                                "default": 5,
                                "minimum": 1,
                                "maximum": 20
                            },
                            "min_similarity": {
                                "type": "number",
                                "description": "Minimum similarity threshold (0.0-1.0)",
                                "default": 0.7,
                                "minimum": 0.0,
                                "maximum": 1.0
                            },
                            "tags": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Filter results by tags",
                                "default": []
                            }
                        },
                        "required": ["query"]
                    }
                ),
                types.Tool(
                    name="get_document",
                    description="Retrieve a specific document by ID",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "document_id": {
                                "type": "string",
                                "description": "Document ID to retrieve"
                            }
                        },
                        "required": ["document_id"]
                    }
                ),
                types.Tool(
                    name="list_documents",
                    description="List all stored documents with optional filtering",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "tags": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Filter by tags",
                                "default": []
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of documents to return",
                                "default": 50,
                                "minimum": 1,
                                "maximum": 100
                            }
                        },
                        "required": []
                    }
                ),
                types.Tool(
                    name="delete_document",
                    description="Delete a document by ID",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "document_id": {
                                "type": "string",
                                "description": "Document ID to delete"
                            }
                        },
                        "required": ["document_id"]
                    }
                ),
                types.Tool(
                    name="update_document",
                    description="Update an existing document",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "document_id": {
                                "type": "string",
                                "description": "Document ID to update"
                            },
                            "content": {
                                "type": "string",
                                "description": "New content (optional)"
                            },
                            "metadata": {
                                "type": "object",
                                "description": "New metadata (optional)"
                            },
                            "tags": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "New tags (optional)"
                            }
                        },
                        "required": ["document_id"]
                    }
                ),
                types.Tool(
                    name="clear_context",
                    description="Clear all stored documents (use with caution)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "confirm": {
                                "type": "boolean",
                                "description": "Confirmation flag to prevent accidental deletion",
                                "default": False
                            }
                        },
                        "required": ["confirm"]
                    }
                ),
                types.Tool(
                    name="get_context_stats",
                    description="Get statistics about stored context",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                types.Tool(
                    name="similar_documents",
                    description="Find documents similar to a given document ID",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "document_id": {
                                "type": "string",
                                "description": "Reference document ID"
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum number of results",
                                "default": 5,
                                "minimum": 1,
                                "maximum": 20
                            },
                            "min_similarity": {
                                "type": "number",
                                "description": "Minimum similarity threshold",
                                "default": 0.7,
                                "minimum": 0.0,
                                "maximum": 1.0
                            }
                        },
                        "required": ["document_id"]
                    }
                )
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> List[types.TextContent]:
            """Handle tool calls."""
            try:
                logger.info(f"Tool called: {name} with arguments: {arguments}")

                if name == "context7_status":
                    return await self._handle_status()
                elif name == "store_document":
                    return await self._handle_store_document(arguments)
                elif name == "search_context":
                    return await self._handle_search_context(arguments)
                elif name == "get_document":
                    return await self._handle_get_document(arguments)
                elif name == "list_documents":
                    return await self._handle_list_documents(arguments)
                elif name == "delete_document":
                    return await self._handle_delete_document(arguments)
                elif name == "update_document":
                    return await self._handle_update_document(arguments)
                elif name == "clear_context":
                    return await self._handle_clear_context(arguments)
                elif name == "get_context_stats":
                    return await self._handle_get_context_stats()
                elif name == "similar_documents":
                    return await self._handle_similar_documents(arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")

            except Exception as e:
                logger.error(f"Error in tool {name}: {str(e)}", exc_info=True)
                return [types.TextContent(
                    type="text",
                    text=f"Error executing {name}: {str(e)}"
                )]

    async def initialize(self):
        """Initialize the server with required components."""
        try:
            # Initialize Redis connection
            redis_url = os.getenv("UPSTASH_REDIS_REST_URL")
            redis_token = os.getenv("UPSTASH_REDIS_REST_TOKEN")

            if not redis_url or not redis_token:
                logger.warning("Redis credentials not found in environment variables")
                # Try local Redis for development
                try:
                    self.redis_client = redis.from_url("redis://localhost:6379", decode_responses=True)
                    await self.redis_client.ping()
                    logger.info("Connected to local Redis")
                except Exception as e:
                    logger.error(f"Failed to connect to local Redis: {e}")
                    self.redis_client = None
            else:
                # Use Upstash Redis
                try:
                    # Parse Upstash URL and create connection
                    parsed_url = urlparse(redis_url)
                    self.redis_client = redis.Redis(
                        host=parsed_url.hostname,
                        port=parsed_url.port or 6379,
                        password=redis_token,
                        ssl=parsed_url.scheme == "https",
                        decode_responses=True
                    )
                    await self.redis_client.ping()
                    logger.info("Connected to Upstash Redis")
                except Exception as e:
                    logger.error(f"Failed to connect to Upstash Redis: {e}")
                    self.redis_client = None

            # Initialize embedding model
            try:
                logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
                self.embedding_model = SentenceTransformer(EMBEDDING_MODEL)
                logger.info("Embedding model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load embedding model: {e}")
                self.embedding_model = None

            # Initialize tokenizer
            try:
                self.tokenizer = tiktoken.get_encoding("cl100k_base")
                logger.info("Tokenizer initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize tokenizer: {e}")
                self.tokenizer = None

            logger.info("Context7 server initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Context7 server: {e}", exc_info=True)
            raise

    def _count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        if not self.tokenizer:
            # Fallback: rough estimation
            return len(text.split()) * 1.3
        try:
            return len(self.tokenizer.encode(text))
        except Exception:
            return len(text.split()) * 1.3

    def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for text."""
        if not self.embedding_model:
            return None
        try:
            embedding = self.embedding_model.encode(text)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None

    def _calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate cosine similarity between two embeddings."""
        try:
            emb1 = np.array(embedding1).reshape(1, -1)
            emb2 = np.array(embedding2).reshape(1, -1)
            return cosine_similarity(emb1, emb2)[0][0]
        except Exception as e:
            logger.error(f"Failed to calculate similarity: {e}")
            return 0.0

    def _create_snippet(self, content: str, query: str, max_length: int = 200) -> str:
        """Create a relevant snippet from content based on query."""
        # Simple implementation - find the most relevant sentence
        sentences = content.split('.')
        if not sentences:
            return content[:max_length]

        query_lower = query.lower()
        best_sentence = ""
        best_score = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # Simple relevance scoring based on keyword overlap
            sentence_lower = sentence.lower()
            score = sum(1 for word in query_lower.split() if word in sentence_lower)

            if score > best_score:
                best_score = score
                best_sentence = sentence

        if best_sentence:
            return best_sentence[:max_length]
        else:
            return content[:max_length]

    async def _handle_status(self) -> List[types.TextContent]:
        """Handle status check."""
        status = {
            "server": "Context7 MCP Server",
            "version": "1.0.0",
            "timestamp": datetime.utcnow().isoformat(),
            "redis_connected": self.redis_client is not None,
            "embedding_model_loaded": self.embedding_model is not None,
            "tokenizer_initialized": self.tokenizer is not None
        }

        if self.redis_client:
            try:
                await self.redis_client.ping()
                status["redis_status"] = "Connected"
            except Exception as e:
                status["redis_status"] = f"Error: {str(e)}"
        else:
            status["redis_status"] = "Not connected"

        return [types.TextContent(
            type="text",
            text=json.dumps(status, indent=2)
        )]

    async def _handle_store_document(self, arguments: dict) -> List[types.TextContent]:
        """Handle document storage."""
        if not self.redis_client:
            return [types.TextContent(
                type="text",
                text="Error: Redis connection not available"
            )]

        content = arguments.get("content", "")
        metadata = arguments.get("metadata", {})
        tags = arguments.get("tags", [])
        document_id = arguments.get("document_id") or str(uuid.uuid4())

        # Count tokens
        token_count = self._count_tokens(content)
        if token_count > MAX_DOCUMENT_SIZE:
            return [types.TextContent(
                type="text",
                text=f"Error: Document too large ({token_count} tokens, max {MAX_DOCUMENT_SIZE})"
            )]

        # Generate embedding
        embedding = self._generate_embedding(content)
        if not embedding:
            return [types.TextContent(
                type="text",
                text="Error: Failed to generate embedding"
            )]

        # Create document
        document = ContextDocument(
            id=document_id,
            content=content,
            metadata=metadata,
            embedding=embedding,
            tags=tags,
            token_count=token_count
        )

        try:
            # Store in Redis
            document_key = f"{REDIS_KEY_PREFIX}doc:{document_id}"
            document_data = document.model_dump()

            # Convert datetime objects to ISO strings for JSON serialization
            document_data["created_at"] = document.created_at.isoformat()
            document_data["updated_at"] = document.updated_at.isoformat()

            await self.redis_client.set(document_key, json.dumps(document_data))

            # Add to document list
            await self.redis_client.sadd(f"{REDIS_KEY_PREFIX}documents", document_id)

            # Add tags to tag index
            for tag in tags:
                await self.redis_client.sadd(f"{REDIS_KEY_PREFIX}tag:{tag}", document_id)

            logger.info(f"Document stored successfully: {document_id}")

            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "document_id": document_id,
                    "token_count": token_count,
                    "embedding_dimensions": len(embedding),
                    "tags": tags
                }, indent=2)
            )]

        except Exception as e:
            logger.error(f"Failed to store document: {e}")
            return [types.TextContent(
                type="text",
                text=f"Error storing document: {str(e)}"
            )]

    async def _handle_search_context(self, arguments: dict) -> List[types.TextContent]:
        """Handle context search."""
        if not self.redis_client:
            return [types.TextContent(
                type="text",
                text="Error: Redis connection not available"
            )]

        query = arguments.get("query", "")
        max_results = arguments.get("max_results", 5)
        min_similarity = arguments.get("min_similarity", 0.7)
        tags = arguments.get("tags", [])

        if not query:
            return [types.TextContent(
                type="text",
                text="Error: Query cannot be empty"
            )]

        # Generate query embedding
        query_embedding = self._generate_embedding(query)
        if not query_embedding:
            return [types.TextContent(
                type="text",
                text="Error: Failed to generate query embedding"
            )]

        try:
            # Get document IDs to search
            if tags:
                # Get intersection of documents with all specified tags
                tag_keys = [f"{REDIS_KEY_PREFIX}tag:{tag}" for tag in tags]
                if len(tag_keys) == 1:
                    document_ids = await self.redis_client.smembers(tag_keys[0])
                else:
                    document_ids = await self.redis_client.sinter(*tag_keys)
            else:
                # Get all documents
                document_ids = await self.redis_client.smembers(f"{REDIS_KEY_PREFIX}documents")

            if not document_ids:
                return [types.TextContent(
                    type="text",
                    text="No documents found matching the criteria"
                )]

            # Search through documents
            results = []
            for doc_id in document_ids:
                document_key = f"{REDIS_KEY_PREFIX}doc:{doc_id}"
                document_data = await self.redis_client.get(document_key)

                if not document_data:
                    continue

                try:
                    doc_dict = json.loads(document_data)
                    if "embedding" not in doc_dict or not doc_dict["embedding"]:
                        continue

                    # Calculate similarity
                    similarity = self._calculate_similarity(query_embedding, doc_dict["embedding"])

                    if similarity >= min_similarity:
                        # Parse datetime strings back to datetime objects
                        doc_dict["created_at"] = datetime.fromisoformat(doc_dict["created_at"])
                        doc_dict["updated_at"] = datetime.fromisoformat(doc_dict["updated_at"])

                        document = ContextDocument(**doc_dict)
                        snippet = self._create_snippet(document.content, query)

                        results.append(SearchResult(
                            document=document,
                            similarity=similarity,
                            snippet=snippet
                        ))

                except Exception as e:
                    logger.error(f"Error processing document {doc_id}: {e}")
                    continue

            # Sort by similarity
            results.sort(key=lambda x: x.similarity, reverse=True)
            results = results[:max_results]

            # Format results
            if not results:
                return [types.TextContent(
                    type="text",
                    text="No relevant documents found"
                )]

            result_data = {
                "query": query,
                "results_count": len(results),
                "results": []
            }

            for result in results:
                result_data["results"].append({
                    "document_id": result.document.id,
                    "similarity": result.similarity,
                    "snippet": result.snippet,
                    "tags": result.document.tags,
                    "token_count": result.document.token_count,
                    "created_at": result.document.created_at.isoformat(),
                    "metadata": result.document.metadata
                })

            return [types.TextContent(
                type="text",
                text=json.dumps(result_data, indent=2)
            )]

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return [types.TextContent(
                type="text",
                text=f"Error during search: {str(e)}"
            )]

    async def _handle_get_document(self, arguments: dict) -> List[types.TextContent]:
        """Handle document retrieval."""
        if not self.redis_client:
            return [types.TextContent(
                type="text",
                text="Error: Redis connection not available"
            )]

        document_id = arguments.get("document_id")
        if not document_id:
            return [types.TextContent(
                type="text",
                text="Error: document_id is required"
            )]

        try:
            document_key = f"{REDIS_KEY_PREFIX}doc:{document_id}"
            document_data = await self.redis_client.get(document_key)

            if not document_data:
                return [types.TextContent(
                    type="text",
                    text=f"Document not found: {document_id}"
                )]

            doc_dict = json.loads(document_data)
            # Remove embedding from output to reduce size
            if "embedding" in doc_dict:
                doc_dict["embedding_dimensions"] = len(doc_dict["embedding"])
                del doc_dict["embedding"]

            return [types.TextContent(
                type="text",
                text=json.dumps(doc_dict, indent=2)
            )]

        except Exception as e:
            logger.error(f"Failed to get document: {e}")
            return [types.TextContent(
                type="text",
                text=f"Error retrieving document: {str(e)}"
            )]

    async def _handle_list_documents(self, arguments: dict) -> List[types.TextContent]:
        """Handle document listing."""
        if not self.redis_client:
            return [types.TextContent(
                type="text",
                text="Error: Redis connection not available"
            )]

        tags = arguments.get("tags", [])
        limit = arguments.get("limit", 50)

        try:
            # Get document IDs
            if tags:
                tag_keys = [f"{REDIS_KEY_PREFIX}tag:{tag}" for tag in tags]
                if len(tag_keys) == 1:
                    document_ids = await self.redis_client.smembers(tag_keys[0])
                else:
                    document_ids = await self.redis_client.sinter(*tag_keys)
            else:
                document_ids = await self.redis_client.smembers(f"{REDIS_KEY_PREFIX}documents")

            document_ids = list(document_ids)[:limit]

            documents = []
            for doc_id in document_ids:
                document_key = f"{REDIS_KEY_PREFIX}doc:{doc_id}"
                document_data = await self.redis_client.get(document_key)

                if document_data:
                    try:
                        doc_dict = json.loads(document_data)
                        # Remove embedding to reduce size
                        if "embedding" in doc_dict:
                            doc_dict["embedding_dimensions"] = len(doc_dict["embedding"])
                            del doc_dict["embedding"]
                        documents.append(doc_dict)
                    except Exception as e:
                        logger.error(f"Error parsing document {doc_id}: {e}")

            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "total_documents": len(documents),
                    "documents": documents
                }, indent=2)
            )]

        except Exception as e:
            logger.error(f"Failed to list documents: {e}")
            return [types.TextContent(
                type="text",
                text=f"Error listing documents: {str(e)}"
            )]

    async def _handle_delete_document(self, arguments: dict) -> List[types.TextContent]:
        """Handle document deletion."""
        if not self.redis_client:
            return [types.TextContent(
                type="text",
                text="Error: Redis connection not available"
            )]

        document_id = arguments.get("document_id")
        if not document_id:
            return [types.TextContent(
                type="text",
                text="Error: document_id is required"
            )]

        try:
            document_key = f"{REDIS_KEY_PREFIX}doc:{document_id}"

            # Get document data to remove from tag indices
            document_data = await self.redis_client.get(document_key)
            if document_data:
                doc_dict = json.loads(document_data)
                tags = doc_dict.get("tags", [])

                # Remove from tag indices
                for tag in tags:
                    await self.redis_client.srem(f"{REDIS_KEY_PREFIX}tag:{tag}", document_id)

            # Delete document
            deleted = await self.redis_client.delete(document_key)

            # Remove from document list
            await self.redis_client.srem(f"{REDIS_KEY_PREFIX}documents", document_id)

            if deleted:
                return [types.TextContent(
                    type="text",
                    text=json.dumps({
                        "success": True,
                        "deleted_document_id": document_id
                    }, indent=2)
                )]
            else:
                return [types.TextContent(
                    type="text",
                    text=f"Document not found: {document_id}"
                )]

        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            return [types.TextContent(
                type="text",
                text=f"Error deleting document: {str(e)}"
            )]

    async def _handle_update_document(self, arguments: dict) -> List[types.TextContent]:
        """Handle document update."""
        if not self.redis_client:
            return [types.TextContent(
                type="text",
                text="Error: Redis connection not available"
            )]

        document_id = arguments.get("document_id")
        if not document_id:
            return [types.TextContent(
                type="text",
                text="Error: document_id is required"
            )]

        try:
            document_key = f"{REDIS_KEY_PREFIX}doc:{document_id}"
            document_data = await self.redis_client.get(document_key)

            if not document_data:
                return [types.TextContent(
                    type="text",
                    text=f"Document not found: {document_id}"
                )]

            doc_dict = json.loads(document_data)

            # Parse datetime strings back to datetime objects
            doc_dict["created_at"] = datetime.fromisoformat(doc_dict["created_at"])
            doc_dict["updated_at"] = datetime.fromisoformat(doc_dict["updated_at"])

            document = ContextDocument(**doc_dict)
            old_tags = document.tags.copy()

            # Update fields
            content_updated = False
            if "content" in arguments:
                document.content = arguments["content"]
                content_updated = True

            if "metadata" in arguments:
                document.metadata = arguments["metadata"]

            if "tags" in arguments:
                document.tags = arguments["tags"]

            # Update timestamp
            document.updated_at = datetime.utcnow()

            # Regenerate embedding if content changed
            if content_updated:
                document.token_count = self._count_tokens(document.content)
                if document.token_count > MAX_DOCUMENT_SIZE:
                    return [types.TextContent(
                        type="text",
                        text=f"Error: Updated document too large ({document.token_count} tokens, max {MAX_DOCUMENT_SIZE})"
                    )]

                new_embedding = self._generate_embedding(document.content)
                if not new_embedding:
                    return [types.TextContent(
                        type="text",
                        text="Error: Failed to generate embedding for updated content"
                    )]
                document.embedding = new_embedding

            # Update tag indices
            if document.tags != old_tags:
                # Remove from old tag indices
                for tag in old_tags:
                    await self.redis_client.srem(f"{REDIS_KEY_PREFIX}tag:{tag}", document_id)

                # Add to new tag indices
                for tag in document.tags:
                    await self.redis_client.sadd(f"{REDIS_KEY_PREFIX}tag:{tag}", document_id)

            # Save updated document
            document_data = document.model_dump()
            document_data["created_at"] = document.created_at.isoformat()
            document_data["updated_at"] = document.updated_at.isoformat()

            await self.redis_client.set(document_key, json.dumps(document_data))

            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "document_id": document_id,
                    "updated_at": document.updated_at.isoformat(),
                    "token_count": document.token_count,
                    "tags": document.tags
                }, indent=2)
            )]

        except Exception as e:
            logger.error(f"Failed to update document: {e}")
            return [types.TextContent(
                type="text",
                text=f"Error updating document: {str(e)}"
            )]

    async def _handle_clear_context(self, arguments: dict) -> List[types.TextContent]:
        """Handle context clearing."""
        if not self.redis_client:
            return [types.TextContent(
                type="text",
                text="Error: Redis connection not available"
            )]

        confirm = arguments.get("confirm", False)
        if not confirm:
            return [types.TextContent(
                type="text",
                text="Error: Must set confirm=true to clear all context"
            )]

        try:
            # Get all document IDs
            document_ids = await self.redis_client.smembers(f"{REDIS_KEY_PREFIX}documents")

            # Delete all documents
            deleted_count = 0
            for doc_id in document_ids:
                document_key = f"{REDIS_KEY_PREFIX}doc:{doc_id}"
                if await self.redis_client.delete(document_key):
                    deleted_count += 1

            # Clear document list
            await self.redis_client.delete(f"{REDIS_KEY_PREFIX}documents")

            # Clear all tag indices
            tag_keys = await self.redis_client.keys(f"{REDIS_KEY_PREFIX}tag:*")
            if tag_keys:
                await self.redis_client.delete(*tag_keys)

            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "deleted_documents": deleted_count,
                    "cleared_at": datetime.utcnow().isoformat()
                }, indent=2)
            )]

        except Exception as e:
            logger.error(f"Failed to clear context: {e}")
            return [types.TextContent(
                type="text",
                text=f"Error clearing context: {str(e)}"
            )]

    async def _handle_get_context_stats(self) -> List[types.TextContent]:
        """Handle context statistics."""
        if not self.redis_client:
            return [types.TextContent(
                type="text",
                text="Error: Redis connection not available"
            )]

        try:
            # Get document count
            document_count = await self.redis_client.scard(f"{REDIS_KEY_PREFIX}documents")

            # Get tag count
            tag_keys = await self.redis_client.keys(f"{REDIS_KEY_PREFIX}tag:*")
            tag_count = len(tag_keys)

            # Get total token count and memory usage
            total_tokens = 0
            document_ids = await self.redis_client.smembers(f"{REDIS_KEY_PREFIX}documents")

            for doc_id in document_ids:
                document_key = f"{REDIS_KEY_PREFIX}doc:{doc_id}"
                document_data = await self.redis_client.get(document_key)
                if document_data:
                    try:
                        doc_dict = json.loads(document_data)
                        total_tokens += doc_dict.get("token_count", 0)
                    except Exception:
                        continue

            # Get Redis memory info if available
            redis_info = {}
            try:
                info = await self.redis_client.info("memory")
                redis_info = {
                    "used_memory": info.get("used_memory", 0),
                    "used_memory_human": info.get("used_memory_human", "N/A")
                }
            except Exception:
                redis_info = {"error": "Redis memory info not available"}

            stats = {
                "document_count": document_count,
                "tag_count": tag_count,
                "total_tokens": total_tokens,
                "redis_info": redis_info,
                "embedding_model": EMBEDDING_MODEL,
                "vector_dimension": VECTOR_DIMENSION,
                "timestamp": datetime.utcnow().isoformat()
            }

            return [types.TextContent(
                type="text",
                text=json.dumps(stats, indent=2)
            )]

        except Exception as e:
            logger.error(f"Failed to get context stats: {e}")
            return [types.TextContent(
                type="text",
                text=f"Error getting context stats: {str(e)}"
            )]

    async def _handle_similar_documents(self, arguments: dict) -> List[types.TextContent]:
        """Handle finding similar documents."""
        if not self.redis_client:
            return [types.TextContent(
                type="text",
                text="Error: Redis connection not available"
            )]

        document_id = arguments.get("document_id")
        max_results = arguments.get("max_results", 5)
        min_similarity = arguments.get("min_similarity", 0.7)

        if not document_id:
            return [types.TextContent(
                type="text",
                text="Error: document_id is required"
            )]

        try:
            # Get reference document
            document_key = f"{REDIS_KEY_PREFIX}doc:{document_id}"
            document_data = await self.redis_client.get(document_key)

            if not document_data:
                return [types.TextContent(
                    type="text",
                    text=f"Reference document not found: {document_id}"
                )]

            ref_doc_dict = json.loads(document_data)
            ref_embedding = ref_doc_dict.get("embedding")

            if not ref_embedding:
                return [types.TextContent(
                    type="text",
                    text="Reference document has no embedding"
                )]

            # Get all other documents
            all_document_ids = await self.redis_client.smembers(f"{REDIS_KEY_PREFIX}documents")
            all_document_ids = [doc_id for doc_id in all_document_ids if doc_id != document_id]

            results = []
            for doc_id in all_document_ids:
                doc_key = f"{REDIS_KEY_PREFIX}doc:{doc_id}"
                doc_data = await self.redis_client.get(doc_key)

                if not doc_data:
                    continue

                try:
                    doc_dict = json.loads(doc_data)
                    doc_embedding = doc_dict.get("embedding")

                    if not doc_embedding:
                        continue

                    # Calculate similarity
                    similarity = self._calculate_similarity(ref_embedding, doc_embedding)

                    if similarity >= min_similarity:
                        # Parse datetime strings
                        doc_dict["created_at"] = datetime.fromisoformat(doc_dict["created_at"])
                        doc_dict["updated_at"] = datetime.fromisoformat(doc_dict["updated_at"])

                        document = ContextDocument(**doc_dict)
                        results.append({
                            "document_id": document.id,
                            "similarity": similarity,
                            "tags": document.tags,
                            "token_count": document.token_count,
                            "created_at": document.created_at.isoformat(),
                            "metadata": document.metadata,
                            "content_preview": document.content[:200] + "..." if len(document.content) > 200 else document.content
                        })

                except Exception as e:
                    logger.error(f"Error processing document {doc_id}: {e}")
                    continue

            # Sort by similarity
            results.sort(key=lambda x: x["similarity"], reverse=True)
            results = results[:max_results]

            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "reference_document_id": document_id,
                    "results_count": len(results),
                    "results": results
                }, indent=2)
            )]

        except Exception as e:
            logger.error(f"Failed to find similar documents: {e}")
            return [types.TextContent(
                type="text",
                text=f"Error finding similar documents: {str(e)}"
            )]

    async def run(self):
        """Run the server."""
        await self.initialize()
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


async def main():
    """Main entry point."""
    try:
        server = Context7Server()
        await server.run()
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
