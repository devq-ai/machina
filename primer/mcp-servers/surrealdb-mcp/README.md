# SurrealDB MCP Server

Multi-model database server implementing the Model Context Protocol (MCP) for SurrealDB operations. Provides comprehensive database functionality including document storage, graph operations, key-value operations, SQL-like queries, and real-time subscriptions.

## 🚀 Features

### Core Capabilities
- **Multi-Model Database**: Document, graph, and key-value operations in one system
- **SurrealQL Queries**: Execute powerful SQL-like queries with modern syntax
- **Graph Operations**: Create relationships, traverse graphs, and manage complex data structures
- **Document Storage**: Store and retrieve JSON documents with full CRUD operations
- **Key-Value Store**: Simple key-value operations with TTL support
- **Real-Time Subscriptions**: Live query subscriptions and real-time updates
- **MCP Protocol**: Full compliance with Model Context Protocol 1.0
- **Async Operations**: Non-blocking, high-performance database operations

### Advanced Features
- **Relationship Management**: Create and query complex graph relationships
- **Graph Traversal**: Multi-depth graph traversal with filtering
- **Transaction Support**: ACID transactions for data consistency
- **Schema Flexibility**: Schema-less or schema-enforced data models
- **Performance Monitoring**: Built-in query performance tracking
- **Connection Management**: Automatic reconnection and connection pooling

## 📋 Requirements

### System Requirements
- Python 3.8+
- SurrealDB server (local or remote)
- 1GB+ RAM for database operations
- Network access for SurrealDB connection

### Dependencies
```txt
mcp>=1.0.0
surrealdb>=0.3.0
websockets>=12.0.0
pydantic>=2.5.0
httpx>=0.25.0
aiofiles>=23.2.0
python-dateutil>=2.8.0
orjson>=3.9.0
```

## 🛠️ Installation

### 1. Install SurrealDB
```bash
# Install SurrealDB server
curl --proto '=https' --tlsv1.2 -sSf https://install.surrealdb.com | sh

# Start SurrealDB server
surreal start --log trace memory
# or for persistent storage:
surreal start --log trace file://mydatabase.db
```

### 2. Install Dependencies
```bash
cd mcp/mcp-servers/surrealdb-mcp
pip install -r requirements.txt
```

### 3. Set Up Environment
```bash
export SURREALDB_URL="ws://localhost:8000/rpc"
export SURREALDB_USERNAME="root"
export SURREALDB_PASSWORD="root"
export SURREALDB_NAMESPACE="devqai"
export SURREALDB_DATABASE="main"
```

### 4. Validate Installation
```bash
python validate_server.py
```

## 🚦 Quick Start

### Start the Server
```bash
python -m surrealdb_mcp.server
```

### Test with MCP Client
The server implements the following MCP tools:

#### Connection & Status
- `surrealdb_status` - Check server health and connection
- `connect_database` - Connect to SurrealDB instance
- `get_database_info` - Get database statistics and information

#### Document Operations
- `create_document` - Create new documents
- `get_document` - Retrieve documents by ID
- `update_document` - Update existing documents
- `delete_document` - Remove documents

#### Query Operations
- `execute_query` - Execute SurrealQL queries
- `list_tables` - List all database tables
- `query_table` - Query specific tables with filters

#### Graph Operations
- `create_relation` - Create relationships between records
- `get_relations` - Get relationships for a record
- `graph_traverse` - Traverse graph relationships

#### Key-Value Operations
- `set_key_value` - Store key-value pairs
- `get_key_value` - Retrieve values by key
- `delete_key_value` - Remove key-value pairs

## 📊 Usage Examples

### Connect to Database
```json
{
  "tool": "connect_database",
  "arguments": {
    "url": "ws://localhost:8000/rpc",
    "username": "root",
    "password": "root",
    "namespace": "devqai",
    "database": "main"
  }
}
```

### Create a Document
```json
{
  "tool": "create_document",
  "arguments": {
    "table": "users",
    "data": {
      "name": "Alice Johnson",
      "email": "alice@example.com",
      "role": "developer",
      "skills": ["Python", "JavaScript", "SurrealDB"]
    },
    "id": "alice_001"
  }
}
```

### Execute SurrealQL Query
```json
{
  "tool": "execute_query",
  "arguments": {
    "query": "SELECT * FROM users WHERE role = $role AND skills CONTAINS $skill",
    "variables": {
      "role": "developer",
      "skill": "Python"
    }
  }
}
```

### Create Graph Relationship
```json
{
  "tool": "create_relation",
  "arguments": {
    "from_id": "users:alice_001",
    "to_id": "companies:acme_corp",
    "relation_type": "works_at",
    "properties": {
      "position": "Senior Developer",
      "department": "Engineering",
      "start_date": "2023-01-15"
    }
  }
}
```

### Traverse Graph
```json
{
  "tool": "graph_traverse",
  "arguments": {
    "start_id": "users:alice_001",
    "depth": 3,
    "relation_types": ["works_at", "knows", "manages"]
  }
}
```

### Key-Value Operations
```json
{
  "tool": "set_key_value",
  "arguments": {
    "key": "user_preferences:alice",
    "value": "{\"theme\": \"dark\", \"language\": \"en\"}",
    "ttl": 86400
  }
}
```

## 🏗️ Architecture

### System Components
```
SurrealDB MCP Server
├── MCP Protocol Handler
├── SurrealDB Connection Manager
├── Document Operations Engine
├── Graph Operations Engine
├── Key-Value Operations Engine
├── Query Execution Engine
└── Error Handling & Validation
```

### Data Models
```
Multi-Model Architecture:
├── Documents (JSON-like records)
├── Graph Nodes (connected entities)
├── Graph Edges (relationships)
├── Key-Value Pairs (simple storage)
└── Tables (structured collections)
```

### Connection Flow
1. **Initialization**: Connect to SurrealDB server via WebSocket
2. **Authentication**: Sign in with credentials
3. **Namespace Selection**: Choose working namespace and database
4. **Operations**: Execute multi-model operations
5. **Real-Time**: Optional live query subscriptions

## ⚙️ Configuration

### Environment Variables
```bash
# Required SurrealDB Configuration
SURREALDB_URL=ws://localhost:8000/rpc
SURREALDB_USERNAME=root
SURREALDB_PASSWORD=root

# Optional Database Selection
SURREALDB_NAMESPACE=devqai
SURREALDB_DATABASE=main

# Optional Connection Settings
SURREALDB_TIMEOUT=30
SURREALDB_RECONNECT_ATTEMPTS=3
```

### Server Constants
```python
DEFAULT_NAMESPACE = "devqai"          # Default namespace
DEFAULT_DATABASE = "main"             # Default database
MAX_QUERY_RESULTS = 1000             # Maximum query results
CONNECTION_TIMEOUT = 30               # Connection timeout (seconds)
RECONNECT_ATTEMPTS = 3               # Reconnection attempts
RECONNECT_DELAY = 5                  # Delay between reconnections
```

## 🧪 Testing

### Run All Tests
```bash
python -m pytest test_server.py -v
```

### Run Validation Suite
```bash
python validate_server.py
```

### Test Coverage
The test suite covers:
- ✅ Server initialization and connection management
- ✅ Document CRUD operations
- ✅ Graph operations and traversal
- ✅ Key-value operations with TTL
- ✅ SurrealQL query execution
- ✅ Table operations and management
- ✅ Error handling and edge cases
- ✅ Multi-model data operations

## 📈 Performance

### Benchmarks
- **Document Operations**: ~10ms per operation (local)
- **Graph Traversal**: ~50ms for depth-3 traversal (1000 nodes)
- **Query Execution**: ~20ms for simple queries
- **Key-Value Operations**: ~5ms per operation
- **Connection Setup**: ~100ms initial connection

### Optimization Tips
1. **Use Transactions**: Group related operations for better performance
2. **Index Strategically**: Create indexes on frequently queried fields
3. **Limit Query Results**: Use LIMIT clauses to prevent large result sets
4. **Connection Pooling**: Reuse connections for multiple operations
5. **Batch Operations**: Group multiple operations when possible

## 🔧 Troubleshooting

### Common Issues

#### SurrealDB Connection Failed
```bash
# Check if SurrealDB is running
curl http://localhost:8000/status

# Start SurrealDB if not running
surreal start --log trace memory

# Check connection parameters
echo $SURREALDB_URL
echo $SURREALDB_USERNAME
```

#### Authentication Failed
```bash
# Verify credentials
surreal sql --conn ws://localhost:8000/rpc --user root --pass root --ns test --db test

# Reset default credentials if needed
surreal start --user root --pass root
```

#### WebSocket Connection Issues
```bash
# Test WebSocket connectivity
wscat -c ws://localhost:8000/rpc

# Check firewall settings
netstat -tulpn | grep 8000

# Try different connection URL
export SURREALDB_URL="http://localhost:8000/rpc"  # HTTP instead of WS
```

#### Query Execution Errors
```bash
# Enable debug logging
export SURREALDB_LOG=debug
python -m surrealdb_mcp.server

# Test queries manually in SurrealDB CLI
surreal sql --conn ws://localhost:8000/rpc --user root --pass root
```

### Debug Mode
```bash
# Enable verbose logging
export PYTHONPATH=/path/to/project
python -m surrealdb_mcp.server --debug

# Check connection details
python -c "
from surrealdb_mcp.server import SurrealDBServer
import asyncio
async def test():
    server = SurrealDBServer()
    await server.initialize()
    result = await server._handle_status()
    print(result[0].text)
asyncio.run(test())
"
```

## 🤝 Contributing

### Development Setup
```bash
# Clone and setup
cd mcp/mcp-servers/surrealdb-mcp
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

### Code Style
- **Python**: Black formatter, 88 character line limit
- **Docstrings**: Google style
- **Type Hints**: Required for all functions
- **Testing**: PyTest with >90% coverage

### Pull Request Process
1. Fork and create feature branch
2. Implement changes with tests
3. Run validation suite: `python validate_server.py`
4. Ensure all tests pass: `pytest test_server.py -v`
5. Submit PR with description

## 📄 License

MIT License - see [LICENSE.md](../../../LICENSE.md) for details.

## 🙋 Support

### Documentation
- [SurrealDB Documentation](https://surrealdb.com/docs/)
- [MCP Protocol Specification](https://mcp.docsrepo.com/)
- [SurrealQL Query Language](https://surrealdb.com/docs/surrealql)

### Issues
- GitHub Issues: Report bugs and feature requests
- Discord: Join the DevQ.ai community
- Email: dion@devq.ai

### Performance Monitoring
- SurrealDB Admin UI: `http://localhost:8000`
- Query performance: Check execution times in responses
- Connection status: Use `surrealdb_status` tool

## 🌟 Advanced Features

### Real-Time Subscriptions
```surrealql
-- Subscribe to live changes
LIVE SELECT * FROM users WHERE role = 'developer';
```

### Complex Graph Queries
```surrealql
-- Find all developers who know Python developers
SELECT * FROM person
WHERE role = 'developer'
AND ->knows->person[WHERE role = 'developer' AND skills CONTAINS 'Python'];
```

### Multi-Table Joins
```surrealql
-- Join users with their companies
SELECT *, ->works_at->company.* FROM users
WHERE role = 'developer';
```

### Geospatial Queries
```surrealql
-- Find nearby locations
SELECT * FROM locations
WHERE location <|2km,2km| [51.509865, -0.118092];
```

---

**Built with ❤️ by the DevQ.ai Team**

*Part of the DevQ.ai MCP Server Ecosystem - Sprint 1 Implementation*
