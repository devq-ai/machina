# Machina MCP Registry for Ptolemies Knowledge Management

## Overview

The Machina MCP Registry provides essential infrastructure for the Ptolemies knowledge management platform, offering specialized MCP servers for document processing, vector search, graph relationships, and sub-100ms query performance. This integration enables Ptolemies to leverage 13 production-ready MCP servers for advanced knowledge operations.

## Quick Start for Ptolemies

### 1. Registry Setup

```bash
# Navigate to the registry from Ptolemies
cd /Users/dionedge/devqai/machina

# Validate Ptolemies-specific environment
python -c "
import os
required = ['OPENAI_API_KEY', 'SURREALDB_URL', 'UPSTASH_REDIS_REST_URL']
missing = [var for var in required if not os.getenv(var)]
print('✅ Ptolemies Ready' if not missing else f'❌ Missing: {missing}')
"

# Start registry with Ptolemies focus
python registry/main.py
```

### 2. Ptolemies-Optimized Server Selection

For Ptolemies knowledge management, prioritize these servers:

```bash
# Essential servers for Ptolemies
PTOLEMIES_SERVERS=(
    "context7-mcp"           # Document management & vector search
    "surrealdb-mcp"          # Multi-model database operations
    "memory-mcp"             # Knowledge persistence
    "sequential-thinking-mcp" # Complex reasoning chains
    "crawl4ai-mcp"           # Web content extraction
)
```

## Ptolemies-Specific MCP Server Configuration

### Core Knowledge Servers

| Server | Tools | Ptolemies Use Case |
|--------|-------|-------------------|
| **context7-mcp** | 15 | Primary document ingestion, vector embeddings, semantic search for 784-page knowledge base |
| **surrealdb-mcp** | 2 | Multi-model database for document storage, graph relationships, vector operations |
| **memory-mcp** | 8 | Session persistence, query history, user context management |
| **sequential-thinking-mcp** | 3 | Complex analysis chains for multi-document reasoning |

### Supporting Infrastructure

| Server | Tools | Ptolemies Use Case |
|--------|-------|-------------------|
| **crawl4ai-mcp** | 3 | Web documentation ingestion, real-time content updates |
| **github-mcp** | 3 | Source code documentation extraction, repository analysis |
| **logfire-mcp** | 12 | Performance monitoring, sub-100ms query tracking |
| **pytest-mcp** | 7 | Knowledge base testing, quality assurance |

## Ptolemies Integration Patterns

### 1. Document Ingestion Pipeline

```python
# ptolemies_ingestion.py
import asyncio
from fastmcp import MCPRegistry
import logfire

class PtolemiesDocumentPipeline:
    """Document ingestion pipeline using MCP servers"""

    def __init__(self):
        self.registry = MCPRegistry()

    async def ingest_document(self, document_path: str, metadata: dict = None):
        """Ingest document through MCP pipeline"""

        with logfire.span("Document Ingestion", document=document_path):
            # Step 1: Extract content (if web URL)
            if document_path.startswith('http'):
                content = await self.registry.fastmcp._call_tool_safe(
                    "crawl_url",
                    {"url": document_path, "extract_content": True}
                )
            else:
                with open(document_path, 'r') as f:
                    content = f.read()

            # Step 2: Store in context7 with embeddings
            context_result = await self.registry.fastmcp._call_tool_safe(
                "store_document",
                {
                    "content": content,
                    "metadata": metadata or {},
                    "generate_embeddings": True
                }
            )

            # Step 3: Store in SurrealDB for graph relationships
            db_result = await self.registry.fastmcp._call_tool_safe(
                "create_record",
                {
                    "table": "documents",
                    "data": {
                        "content": content,
                        "metadata": metadata,
                        "context7_id": context_result.get("document_id"),
                        "ingested_at": "datetime.now()"
                    }
                }
            )

            # Step 4: Store processing memory
            await self.registry.fastmcp._call_tool_safe(
                "store_memory",
                {
                    "key": f"ingestion_{db_result.get('id')}",
                    "value": {
                        "document_path": document_path,
                        "processing_time": "timestamp",
                        "status": "completed"
                    }
                }
            )

            return {
                "document_id": db_result.get("id"),
                "context7_id": context_result.get("document_id"),
                "status": "ingested"
            }
```

### 2. Sub-100ms Query Engine

```python
# ptolemies_query.py
import asyncio
import time
from fastmcp import MCPRegistry
import logfire

class PtolemiesQueryEngine:
    """High-performance query engine targeting sub-100ms response"""

    def __init__(self):
        self.registry = MCPRegistry()

    async def fast_query(self, query: str, max_results: int = 10):
        """Execute sub-100ms knowledge base query"""

        start_time = time.time()

        with logfire.span("Fast Query", query=query, target="<100ms"):
            # Parallel execution for speed
            tasks = [
                # Vector search in context7
                self.registry.fastmcp._call_tool_safe(
                    "semantic_search",
                    {"query": query, "limit": max_results, "threshold": 0.7}
                ),

                # Memory-based context retrieval
                self.registry.fastmcp._call_tool_safe(
                    "search_memories",
                    {"query": query, "limit": 5}
                ),

                # Graph relationship search in SurrealDB
                self.registry.fastmcp._call_tool_safe(
                    "query_database",
                    {
                        "query": f"SELECT * FROM documents WHERE string::contains(content, '{query}') LIMIT {max_results}"
                    }
                )
            ]

            # Execute searches in parallel
            vector_results, memory_results, graph_results = await asyncio.gather(*tasks)

            # Combine and rank results
            combined_results = self._combine_results(
                vector_results, memory_results, graph_results, query
            )

            execution_time = (time.time() - start_time) * 1000  # Convert to ms

            logfire.info(
                "Query executed",
                execution_time_ms=execution_time,
                results_count=len(combined_results),
                target_met=execution_time < 100
            )

            return {
                "results": combined_results,
                "execution_time_ms": execution_time,
                "target_met": execution_time < 100,
                "sources": {
                    "vector_search": len(vector_results.get("results", [])),
                    "memory_search": len(memory_results.get("results", [])),
                    "graph_search": len(graph_results.get("results", []))
                }
            }

    def _combine_results(self, vector_results, memory_results, graph_results, query):
        """Intelligent result combination and ranking"""
        # Implementation for combining and ranking results
        # Priority: vector similarity > memory relevance > graph relationships
        combined = []

        # Add vector results with high priority
        for result in vector_results.get("results", [])[:5]:
            combined.append({
                "content": result.get("content"),
                "score": result.get("similarity", 0) * 1.0,  # Full weight
                "source": "vector_search",
                "metadata": result.get("metadata", {})
            })

        # Add memory results with medium priority
        for result in memory_results.get("results", [])[:3]:
            combined.append({
                "content": result.get("value"),
                "score": 0.8,  # Fixed medium score
                "source": "memory_search",
                "metadata": {"key": result.get("key")}
            })

        # Add graph results with lower priority
        for result in graph_results.get("results", [])[:2]:
            combined.append({
                "content": result.get("content"),
                "score": 0.6,  # Fixed lower score
                "source": "graph_search",
                "metadata": result.get("metadata", {})
            })

        # Sort by score and return top results
        return sorted(combined, key=lambda x: x["score"], reverse=True)[:10]
```

### 3. Knowledge Graph Operations

```python
# ptolemies_graph.py
import asyncio
from fastmcp import MCPRegistry

class PtolemiesKnowledgeGraph:
    """Knowledge graph operations using SurrealDB MCP"""

    def __init__(self):
        self.registry = MCPRegistry()

    async def create_document_relationships(self, doc_id: str, related_concepts: list):
        """Create graph relationships between documents and concepts"""

        for concept in related_concepts:
            # Create relationship edge
            await self.registry.fastmcp._call_tool_safe(
                "create_record",
                {
                    "table": "document_concepts",
                    "data": {
                        "document_id": doc_id,
                        "concept": concept["name"],
                        "relevance_score": concept.get("score", 0.8),
                        "relationship_type": concept.get("type", "mentions")
                    }
                }
            )

    async def find_related_documents(self, concept: str, limit: int = 10):
        """Find documents related to a concept via graph traversal"""

        query = f"""
        SELECT document_id, relevance_score
        FROM document_concepts
        WHERE concept = '{concept}'
        ORDER BY relevance_score DESC
        LIMIT {limit}
        """

        result = await self.registry.fastmcp._call_tool_safe(
            "query_database",
            {"query": query}
        )

        return result.get("results", [])
```

## Environment Configuration for Ptolemies

### Required Variables

```bash
# Core API Keys for Knowledge Processing
OPENAI_API_KEY=sk-...                    # For embeddings and vector search
ANTHROPIC_API_KEY=sk-ant-...             # For reasoning and analysis

# Database Configuration
SURREALDB_URL=ws://localhost:8000/rpc    # Multi-model database
SURREALDB_USERNAME=root
SURREALDB_PASSWORD=root

# Redis for Context7 (Vector Search)
UPSTASH_REDIS_REST_URL=https://...       # Vector storage and retrieval
UPSTASH_REDIS_REST_TOKEN=...
```

### Optional Variables for Enhanced Features

```bash
# GitHub Integration (for source code docs)
GITHUB_TOKEN=ghp_...

# Observability (for performance monitoring)
LOGFIRE_TOKEN=pylf_v1_us_...

# Web Crawling (for real-time updates)
PERPLEXITY_API_KEY=pplx-...
```

## Ptolemies-Specific Server Management

### Start Ptolemies-Optimized Registry

```python
# ptolemies_registry.py
import asyncio
import sys
sys.path.insert(0, '.')
from fastmcp import MCPRegistry
from registry.main import validate_environment
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def start_ptolemies_registry():
    """Start registry optimized for Ptolemies knowledge management"""

    # Validate environment
    if not await validate_environment():
        print("❌ Environment validation failed")
        return

    # Create registry
    registry = MCPRegistry()

    # Essential servers for Ptolemies
    ptolemies_servers = [
        {
            "name": "context7-mcp",
            "endpoint": "stdio://devqai/mcp/mcp-servers/context7-mcp/context7_mcp/server.py",
            "framework": "FastMCP",
            "tools": ["store_document", "semantic_search", "get_context", "calculate_embeddings"],
            "description": "Vector search and document management for 784-page knowledge base",
            "environment_vars": ["OPENAI_API_KEY", "UPSTASH_REDIS_REST_URL", "UPSTASH_REDIS_REST_TOKEN"]
        },
        {
            "name": "surrealdb-mcp",
            "endpoint": "stdio://devqai/mcp/mcp-servers/surrealdb-mcp/surrealdb_mcp/server.py",
            "framework": "Standard MCP",
            "tools": ["create_record", "query_database"],
            "description": "Multi-model database for graph relationships and document storage",
            "environment_vars": ["SURREALDB_URL", "SURREALDB_USERNAME", "SURREALDB_PASSWORD"]
        },
        {
            "name": "memory-mcp",
            "endpoint": "stdio://devqai/mcp/mcp-servers/memory-mcp/memory_mcp/server.py",
            "framework": "FastMCP",
            "tools": ["store_memory", "retrieve_memory", "search_memories"],
            "description": "Session persistence and query history management",
            "environment_vars": []
        },
        {
            "name": "logfire-mcp",
            "endpoint": "stdio://devqai/mcp/mcp-servers/logfire-mcp/logfire_mcp/server.py",
            "framework": "FastMCP",
            "tools": ["create_span", "log_info", "get_metrics"],
            "description": "Performance monitoring for sub-100ms query tracking",
            "environment_vars": ["LOGFIRE_TOKEN"]
        }
    ]

    # Register Ptolemies-specific servers
    for server_config in ptolemies_servers:
        try:
            result = await registry.fastmcp._call_tool_safe("register_server", server_config)
            logger.info(f"✅ Registered: {server_config['name']}")
        except Exception as e:
            logger.error(f"❌ Failed to register {server_config['name']}: {e}")

    print("🚀 Ptolemies-optimized registry started")
    print("📊 Essential servers for knowledge management registered")
    print("⚡ Ready for sub-100ms query performance")

    # Start the server
    await registry.run()

if __name__ == "__main__":
    asyncio.run(start_ptolemies_registry())
```

### Run Ptolemies Registry

```bash
# Start Ptolemies-optimized registry
python ptolemies_registry.py

# Or start full registry and use selective tools
python registry/main.py
```

## Performance Optimization for Ptolemies

### 1. Sub-100ms Query Configuration

```python
# ptolemies_performance.py
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

class PtolemiesPerformanceOptimizer:
    """Performance optimization for sub-100ms queries"""

    def __init__(self, registry):
        self.registry = registry
        self.executor = ThreadPoolExecutor(max_workers=4)

    async def optimize_vector_search(self, query: str):
        """Optimized vector search with caching"""

        # Check memory cache first
        cached_result = await self.registry.fastmcp._call_tool_safe(
            "retrieve_memory",
            {"key": f"query_cache_{hash(query)}"}
        )

        if cached_result.get("value"):
            return cached_result["value"]

        # Execute vector search with timeout
        try:
            result = await asyncio.wait_for(
                self.registry.fastmcp._call_tool_safe(
                    "semantic_search",
                    {"query": query, "limit": 10}
                ),
                timeout=0.05  # 50ms timeout
            )

            # Cache result for future queries
            await self.registry.fastmcp._call_tool_safe(
                "store_memory",
                {
                    "key": f"query_cache_{hash(query)}",
                    "value": result,
                    "ttl": 300  # 5 minute cache
                }
            )

            return result

        except asyncio.TimeoutError:
            # Return cached or default result if timeout
            return {"results": [], "timeout": True}
```

### 2. Monitoring and Metrics

```python
# ptolemies_monitoring.py
import asyncio
import time
from fastmcp import MCPRegistry

class PtolemiesMonitoring:
    """Performance monitoring for Ptolemies knowledge base"""

    def __init__(self):
        self.registry = MCPRegistry()

    async def track_query_performance(self, query_func, *args, **kwargs):
        """Track query performance with Logfire"""

        start_time = time.time()

        try:
            result = await query_func(*args, **kwargs)
            execution_time = (time.time() - start_time) * 1000

            # Log performance metrics
            await self.registry.fastmcp._call_tool_safe(
                "log_info",
                {
                    "message": "Query executed",
                    "execution_time_ms": execution_time,
                    "target_met": execution_time < 100,
                    "query_type": query_func.__name__
                }
            )

            return result

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000

            await self.registry.fastmcp._call_tool_safe(
                "log_error",
                {
                    "message": "Query failed",
                    "error": str(e),
                    "execution_time_ms": execution_time
                }
            )

            raise
```

## Testing Ptolemies Integration

### 1. Knowledge Base Validation

```bash
# Test Ptolemies-specific functionality
python -c "
import asyncio
import sys
sys.path.insert(0, '.')
from fastmcp import MCPRegistry

async def test_ptolemies():
    registry = MCPRegistry()

    # Test vector search capability
    result = await registry.fastmcp._call_tool_safe(
        'semantic_search',
        {'query': 'API authentication patterns', 'limit': 5}
    )
    print('Vector Search:', '✅' if result else '❌')

    # Test database operations
    result = await registry.fastmcp._call_tool_safe(
        'query_database',
        {'query': 'SELECT count() FROM documents GROUP ALL'}
    )
    print('Database Query:', '✅' if result else '❌')

    # Test memory operations
    result = await registry.fastmcp._call_tool_safe(
        'store_memory',
        {'key': 'test_key', 'value': 'test_value'}
    )
    print('Memory Storage:', '✅' if result else '❌')

asyncio.run(test_ptolemies())
"
```

### 2. Performance Benchmarking

```bash
# Benchmark sub-100ms query performance
python -c "
import asyncio
import time
import sys
sys.path.insert(0, '.')
from fastmcp import MCPRegistry

async def benchmark_queries():
    registry = MCPRegistry()

    queries = [
        'FastAPI authentication',
        'database design patterns',
        'API rate limiting',
        'testing strategies',
        'deployment best practices'
    ]

    results = []

    for query in queries:
        start_time = time.time()

        result = await registry.fastmcp._call_tool_safe(
            'semantic_search',
            {'query': query, 'limit': 10}
        )

        execution_time = (time.time() - start_time) * 1000
        results.append(execution_time)

        status = '✅' if execution_time < 100 else '❌'
        print(f'{status} {query}: {execution_time:.2f}ms')

    avg_time = sum(results) / len(results)
    print(f'\\n📊 Average query time: {avg_time:.2f}ms')
    print(f'🎯 Sub-100ms target: {\"✅ Met\" if avg_time < 100 else \"❌ Missed\"}')

asyncio.run(benchmark_queries())
"
```

## Troubleshooting for Ptolemies

### Common Issues

1. **Slow Query Performance**
   ```bash
   # Check vector search configuration
   python -c "
   import os
   print('OpenAI API Key:', '✅' if os.getenv('OPENAI_API_KEY') else '❌')
   print('Redis URL:', '✅' if os.getenv('UPSTASH_REDIS_REST_URL') else '❌')
   "
   ```

2. **Database Connection Issues**
   ```bash
   # Test SurrealDB connection
   python -c "
   import asyncio
   import surrealdb

   async def test_db():
       try:
           db = surrealdb.Surreal()
           await db.connect('ws://localhost:8000/rpc')
           await db.signin({'user': 'root', 'pass': 'root'})
           print('✅ SurrealDB connected')
       except Exception as e:
           print(f'❌ SurrealDB error: {e}')

   asyncio.run(test_db())
   "
   ```

3. **Memory Management Issues**
   ```bash
   # Clear cached queries if needed
   python -c "
   import asyncio, sys
   sys.path.insert(0, '.')
   from fastmcp import MCPRegistry

   async def clear_cache():
       registry = MCPRegistry()
       result = await registry.fastmcp._call_tool_safe('clear_all_memories', {})
       print('Cache cleared:', result)

   asyncio.run(clear_cache())
   "
   ```

## Best Practices for Ptolemies

### 1. Document Ingestion
- Batch process documents for efficiency
- Use semantic chunking for better search results
- Generate embeddings during ingestion, not query time
- Maintain document metadata for filtering

### 2. Query Optimization
- Implement query result caching
- Use parallel search across multiple servers
- Optimize vector similarity thresholds
- Monitor and log query performance

### 3. Knowledge Graph Management
- Create meaningful relationships during ingestion
- Use graph traversal for complex queries
- Maintain concept hierarchies
- Regular graph cleanup and optimization

### 4. Performance Monitoring
- Track all queries with Logfire
- Monitor sub-100ms target achievement
- Alert on performance degradation
- Regular performance benchmarking

---

**Ptolemies Integration Status**: ✅ Knowledge servers ready for 784-page documentation processing
**Performance Target**: ⚡ Sub-100ms query response with vector search and graph relationships
**Documentation**: Updated January 15, 2025
**Support**: See `TESTING_GUIDE.md` for comprehensive testing procedures
