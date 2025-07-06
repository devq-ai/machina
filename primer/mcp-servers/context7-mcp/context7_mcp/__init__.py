#!/usr/bin/env python3
"""
Context7 MCP Server Module

Advanced context management and semantic search server implementing the MCP protocol.
Provides intelligent context storage, retrieval, semantic search with vector embeddings,
and Redis-backed persistence for AI-enhanced development workflows.

This module follows DevQ.ai standards with comprehensive MCP integration,
async operations, structured logging, and robust error handling.
"""

from .server import Context7Server, ContextDocument, SearchResult, ContextQuery

__version__ = "1.0.0"
__author__ = "DevQ.ai Team"
__email__ = "dion@devq.ai"
__description__ = "Advanced context management and semantic search MCP server"

__all__ = [
    "Context7Server",
    "ContextDocument",
    "SearchResult",
    "ContextQuery"
]

# Module metadata
MODULE_INFO = {
    "name": "context7_mcp",
    "version": __version__,
    "description": __description__,
    "author": __author__,
    "email": __email__,
    "license": "MIT",
    "python_requires": ">=3.8",
    "keywords": ["mcp", "context", "semantic-search", "embeddings", "redis", "ai"],
    "classifiers": [
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ]
}

# Server capabilities
CAPABILITIES = {
    "semantic_search": True,
    "vector_embeddings": True,
    "redis_persistence": True,
    "document_management": True,
    "tag_filtering": True,
    "similarity_search": True,
    "async_operations": True,
    "mcp_protocol": "1.0.0"
}

# Configuration defaults
DEFAULT_CONFIG = {
    "max_context_size": 32000,
    "max_document_size": 10000,
    "embedding_model": "all-MiniLM-L6-v2",
    "vector_dimension": 384,
    "similarity_threshold": 0.7,
    "max_results": 10,
    "redis_key_prefix": "context7:"
}
