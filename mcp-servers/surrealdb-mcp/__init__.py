#!/usr/bin/env python3
"""
SurrealDB MCP Server Package

Multi-model database server implementing the MCP protocol for SurrealDB operations.
Provides comprehensive database functionality including document storage, graph operations,
key-value operations, SQL-like queries, and real-time subscriptions.

This package follows DevQ.ai standards with comprehensive MCP integration,
async operations, structured logging, and robust error handling.
"""

from surrealdb_mcp.server import SurrealDBServer, DatabaseDocument, GraphNode, GraphRelation, QueryResult

__version__ = "1.0.0"
__author__ = "DevQ.ai Team"
__email__ = "dion@devq.ai"
__description__ = "Multi-model database MCP server for SurrealDB operations"

__all__ = [
    "SurrealDBServer",
    "DatabaseDocument",
    "GraphNode",
    "GraphRelation",
    "QueryResult"
]

# Package metadata
PACKAGE_INFO = {
    "name": "surrealdb-mcp",
    "version": __version__,
    "description": __description__,
    "author": __author__,
    "email": __email__,
    "license": "MIT",
    "python_requires": ">=3.8",
    "keywords": ["mcp", "surrealdb", "database", "graph", "document", "key-value"],
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
        "Topic :: Database",
        "Topic :: Database :: Database Engines/Servers",
    ]
}

# Server capabilities
CAPABILITIES = {
    "multi_model": True,
    "document_storage": True,
    "graph_operations": True,
    "key_value_store": True,
    "sql_queries": True,
    "relationships": True,
    "graph_traversal": True,
    "real_time": True,
    "transactions": True,
    "async_operations": True,
    "mcp_protocol": "1.0.0"
}

# Configuration defaults
DEFAULT_CONFIG = {
    "default_namespace": "devqai",
    "default_database": "main",
    "max_query_results": 1000,
    "connection_timeout": 30,
    "reconnect_attempts": 3,
    "reconnect_delay": 5
}
