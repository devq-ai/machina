# Context7 MCP Server

Advanced context management and semantic search server implementing the Model Context Protocol (MCP). Provides intelligent context storage, retrieval, semantic search with vector embeddings, and Redis-backed persistence for AI-enhanced development workflows.

## 🚀 Features

### Core Capabilities
- **Semantic Search**: Intelligent document search using vector embeddings
- **Vector Embeddings**: Powered by Sentence Transformers (all-MiniLM-L6-v2)
- **Redis Persistence**: High-performance caching and storage
- **Document Management**: Store, retrieve, update, and delete documents
- **Tag Filtering**: Organize and filter documents by tags
- **Similarity Search**: Find documents similar to a reference document
- **Async Operations**: Non-blocking, high-performance operations
- **MCP Protocol**: Full compliance with Model Context Protocol 1.0

### Advanced Features
- **Token Counting**: Accurate token counting with tiktoken
- **Snippet Generation**: Intelligent content snippets for search results
- **Error Handling**: Comprehensive error handling and validation
- **Statistics**: Detailed context and performance statistics
- **Batch Operations**: Efficient bulk document operations

## 📋 Requirements

### System Requirements
- Python 3.8+
- Redis server (local or Upstash)
- 2GB+ RAM for embedding model
- Network access for model downloads

### Dependencies
```txt
mcp>=1.0.0
redis[hiredis]>=5.0.0
sentence-transformers>=2.2.2
numpy>=1.24.0
scikit-learn>=1.3.0
tiktoken>=0.5.0
pydantic>=2.5.0
httpx>=0.25.0
aiofiles>=23.2.0
```

## 🛠️ Installation

### 1. Install Dependencies
```bash
cd mcp/mcp-servers/context7-mcp
pip install -r requirements.txt
```

### 2. Set Up Redis
**Option A: Upstash Redis (Recommended for Production)**
```bash
export UPSTASH_REDIS_REST_URL="https://your-redis-url.upstash.io"
export UPSTASH_REDIS_REST_TOKEN="your-redis-token"
```

**Option B: Local Redis (Development)**
```bash
# Install and start Redis locally
brew install redis  # macOS
redis-server
```

### 3. Validate Installation
```bash
python validate_server.py
```

## 🚦 Quick Start

### Start the Server
```bash
python -m context7_mcp.server
```

### Test with MCP Client
The server implements the following MCP tools:

#### Core Operations
- `context7_status` - Check server health
- `store_document` - Store documents with embeddings
- `search_context` - Semantic search across documents
- `get_document` - Retrieve specific documents
- `list_documents` - List all stored documents

#### Management Operations
- `delete_document` - Remove documents
- `update_document` - Modify existing documents
- `clear_context` - Remove all documents (with confirmation)
- `get_context_stats` - System statistics
- `similar_documents` - Find similar documents

## 📊 Usage Examples

### Store a Document
```json
{
  "tool": "store_document",
  "arguments": {
    "content": "Machine learning is a subset of artificial intelligence that focuses on algorithms.",
    "metadata": {"source": "wikipedia", "category": "ai"},
    "tags": ["machine-learning", "ai", "algorithms"],
    "document_id": "ml-basics-001"
  }
}
```

### Search for Content
```json
{
  "tool": "search_context",
  "arguments": {
    "query": "artificial intelligence algorithms",
    "max_results": 5,
    "min_similarity": 0.7,
    "tags": ["ai"]
  }
}
```

### Get Document Statistics
```json
{
  "tool": "get_context_stats",
  "arguments": {}
}
```

## 🏗️ Architecture

### System Components
```
Context7 MCP Server
├── MCP Protocol Handler
├── Redis Connection Manager
├── Sentence Transformer Model
├── Vector Similarity Engine
├── Document Storage System
└── Token Counting Service
```

### Data Flow
1. **Document Ingestion**: Content → Tokenization → Embedding → Redis Storage
2. **Search Process**: Query → Embedding → Similarity Calculation → Ranked Results
3. **Retrieval**: Document ID → Redis Lookup → Content Return

### Storage Schema
```
Redis Keys:
- context7:doc:{id}        # Document data with embeddings
- context7:documents       # Set of all document IDs
- context7:tag:{tag}       # Set of documents with specific tag
```

## ⚙️ Configuration

### Environment Variables
```bash
# Redis Configuration
UPSTASH_REDIS_REST_URL=https://your-redis-url.upstash.io
UPSTASH_REDIS_REST_TOKEN=your-redis-token

# Optional: Model Configuration
EMBEDDING_MODEL=all-MiniLM-L6-v2
MAX_DOCUMENT_SIZE=10000
SIMILARITY_THRESHOLD=0.7
```

### Server Constants
```python
MAX_CONTEXT_SIZE = 32000     # Maximum context size in tokens
MAX_DOCUMENT_SIZE = 10000    # Maximum document size in tokens
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # Sentence transformer model
VECTOR_DIMENSION = 384       # Embedding dimension
SIMILARITY_THRESHOLD = 0.7   # Default similarity threshold
MAX_RESULTS = 10            # Default maximum search results
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
- ✅ Server initialization and health checks
- ✅ Redis connection and operations
- ✅ Embedding model functionality
- ✅ Document CRUD operations
- ✅ Semantic search accuracy
- ✅ Error handling and edge cases
- ✅ Performance benchmarks

## 📈 Performance

### Benchmarks
- **Document Storage**: ~100ms per document (with embedding generation)
- **Search Performance**: ~50ms for 1000 documents
- **Memory Usage**: ~500MB baseline + ~1MB per 1000 documents
- **Embedding Generation**: ~200ms per document (CPU), ~50ms (GPU)

### Optimization Tips
1. **Use GPU**: Install PyTorch with CUDA for faster embeddings
2. **Redis Optimization**: Use Redis clustering for large datasets
3. **Batch Operations**: Store multiple documents in batches
4. **Similarity Threshold**: Higher thresholds = faster searches

## 🔧 Troubleshooting

### Common Issues

#### Redis Connection Failed
```bash
# Check Redis status
redis-cli ping

# Verify environment variables
echo $UPSTASH_REDIS_REST_URL
echo $UPSTASH_REDIS_REST_TOKEN
```

#### Embedding Model Download Issues
```bash
# Clear model cache
rm -rf ~/.cache/huggingface/transformers/

# Reinstall sentence-transformers
pip uninstall sentence-transformers
pip install sentence-transformers
```

#### Memory Issues
```bash
# Monitor memory usage
python -c "import psutil; print(f'Memory: {psutil.virtual_memory().percent}%')"

# Reduce batch size or use smaller model
export EMBEDDING_MODEL="all-MiniLM-L12-v2"  # Smaller alternative
```

### Debug Mode
```bash
# Enable debug logging
export PYTHONPATH=/path/to/project
python -m context7_mcp.server --debug
```

## 🤝 Contributing

### Development Setup
```bash
# Clone and setup
cd mcp/mcp-servers/context7-mcp
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
4. Submit PR with description

## 📄 License

MIT License - see [LICENSE.md](../../../LICENSE.md) for details.

## 🙋 Support

### Documentation
- [MCP Protocol Specification](https://mcp.docsrepo.com/)
- [Sentence Transformers Guide](https://www.sbert.net/)
- [Redis Documentation](https://redis.io/docs/)

### Issues
- GitHub Issues: Report bugs and feature requests
- Discord: Join the DevQ.ai community
- Email: dion@devq.ai

### Performance Monitoring
- View metrics in Redis: `redis-cli monitor`
- Check logs: `tail -f /var/log/context7.log`
- Memory profiling: `python -m memory_profiler validate_server.py`

---

**Built with ❤️ by the DevQ.ai Team**

*Part of the DevQ.ai MCP Server Ecosystem - Sprint 1 Implementation*
