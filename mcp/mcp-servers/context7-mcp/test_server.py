#!/usr/bin/env python3
"""
Test Suite for Context7 MCP Server

Comprehensive test coverage for the Context7 MCP Server including:
- Connection testing (Redis, embedding model)
- Document storage and retrieval
- Semantic search functionality
- Vector embedding operations
- MCP protocol compliance
- Error handling and edge cases
"""

import asyncio
import json
import os
import tempfile
import uuid
from datetime import datetime
from typing import Dict, List, Any
from unittest.mock import Mock, AsyncMock, patch
import pytest
import numpy as np

# Import the server components
import sys
from pathlib import Path
# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from context7_mcp.server import Context7Server, ContextDocument, SearchResult, ContextQuery
from mcp import types


class TestContext7Server:
    """Test cases for Context7 MCP Server."""

    @pytest.fixture
    async def server(self):
        """Create a test server instance."""
        server = Context7Server()
        # Mock the components for testing
        server.redis_client = AsyncMock()
        server.embedding_model = Mock()
        server.tokenizer = Mock()

        # Mock embedding model
        server.embedding_model.encode.return_value = np.random.rand(384)

        # Mock tokenizer
        server.tokenizer.encode.return_value = ["token1", "token2", "token3"]

        return server

    @pytest.fixture
    def sample_document(self):
        """Create a sample document for testing."""
        return ContextDocument(
            id="test-doc-1",
            content="This is a test document about machine learning and AI.",
            metadata={"source": "test", "category": "ai"},
            tags=["machine-learning", "ai", "test"],
            token_count=12,
            embedding=[0.1, 0.2, 0.3] * 128  # 384 dimensions
        )

    @pytest.fixture
    def sample_documents(self):
        """Create multiple sample documents for testing."""
        return [
            ContextDocument(
                id="doc-1",
                content="Machine learning is a subset of artificial intelligence.",
                metadata={"source": "wikipedia", "category": "ai"},
                tags=["machine-learning", "ai"],
                token_count=10,
                embedding=[0.8, 0.1, 0.1] * 128
            ),
            ContextDocument(
                id="doc-2",
                content="Deep learning uses neural networks with multiple layers.",
                metadata={"source": "textbook", "category": "ai"},
                tags=["deep-learning", "neural-networks"],
                token_count=9,
                embedding=[0.7, 0.2, 0.1] * 128
            ),
            ContextDocument(
                id="doc-3",
                content="Python is a popular programming language for data science.",
                metadata={"source": "tutorial", "category": "programming"},
                tags=["python", "programming", "data-science"],
                token_count=11,
                embedding=[0.1, 0.8, 0.1] * 128
            )
        ]

    async def test_server_initialization(self, server):
        """Test server initialization."""
        assert server.server.name == "context7-mcp"
        assert server.redis_client is not None
        assert server.embedding_model is not None
        assert server.tokenizer is not None

    async def test_list_tools(self, server):
        """Test tool listing."""
        tools = await server.server._list_tools_handler()

        expected_tools = [
            "context7_status",
            "store_document",
            "search_context",
            "get_document",
            "list_documents",
            "delete_document",
            "update_document",
            "clear_context",
            "get_context_stats",
            "similar_documents"
        ]

        tool_names = [tool.name for tool in tools]
        for expected_tool in expected_tools:
            assert expected_tool in tool_names

    async def test_status_check(self, server):
        """Test status check functionality."""
        # Mock Redis ping
        server.redis_client.ping = AsyncMock(return_value=True)

        result = await server._handle_status()

        assert len(result) == 1
        status_data = json.loads(result[0].text)

        assert status_data["server"] == "Context7 MCP Server"
        assert status_data["redis_connected"] is True
        assert status_data["embedding_model_loaded"] is True
        assert status_data["tokenizer_initialized"] is True

    async def test_status_check_redis_error(self, server):
        """Test status check with Redis error."""
        # Mock Redis ping to raise exception
        server.redis_client.ping = AsyncMock(side_effect=Exception("Connection failed"))

        result = await server._handle_status()

        assert len(result) == 1
        status_data = json.loads(result[0].text)

        assert "Error: Connection failed" in status_data["redis_status"]

    async def test_store_document(self, server):
        """Test document storage."""
        # Mock Redis operations
        server.redis_client.set = AsyncMock(return_value=True)
        server.redis_client.sadd = AsyncMock(return_value=1)

        arguments = {
            "content": "Test document content",
            "metadata": {"source": "test"},
            "tags": ["test", "document"],
            "document_id": "test-doc-1"
        }

        result = await server._handle_store_document(arguments)

        assert len(result) == 1
        response_data = json.loads(result[0].text)

        assert response_data["success"] is True
        assert response_data["document_id"] == "test-doc-1"
        assert "token_count" in response_data
        assert "embedding_dimensions" in response_data

    async def test_store_document_without_redis(self, server):
        """Test document storage without Redis connection."""
        server.redis_client = None

        arguments = {"content": "Test content"}
        result = await server._handle_store_document(arguments)

        assert len(result) == 1
        assert "Redis connection not available" in result[0].text

    async def test_store_document_too_large(self, server):
        """Test storing document that exceeds size limit."""
        # Mock token count to exceed limit
        server._count_tokens = Mock(return_value=50000)

        arguments = {"content": "Very large document content"}
        result = await server._handle_store_document(arguments)

        assert len(result) == 1
        assert "Document too large" in result[0].text

    async def test_search_context(self, server, sample_documents):
        """Test context search functionality."""
        # Mock Redis operations
        server.redis_client.smembers = AsyncMock(return_value={"doc-1", "doc-2", "doc-3"})

        # Mock document retrieval
        async def mock_get(key):
            doc_id = key.split(":")[-1]
            for doc in sample_documents:
                if doc.id == doc_id:
                    doc_data = doc.model_dump()
                    doc_data["created_at"] = doc.created_at.isoformat()
                    doc_data["updated_at"] = doc.updated_at.isoformat()
                    return json.dumps(doc_data)
            return None

        server.redis_client.get = AsyncMock(side_effect=mock_get)

        # Mock similarity calculation
        server._calculate_similarity = Mock(return_value=0.8)

        arguments = {
            "query": "machine learning",
            "max_results": 3,
            "min_similarity": 0.7
        }

        result = await server._handle_search_context(arguments)

        assert len(result) == 1
        response_data = json.loads(result[0].text)

        assert response_data["query"] == "machine learning"
        assert response_data["results_count"] > 0
        assert "results" in response_data

    async def test_search_context_no_results(self, server):
        """Test search with no matching results."""
        # Mock Redis to return no documents
        server.redis_client.smembers = AsyncMock(return_value=set())

        arguments = {"query": "nonexistent topic"}
        result = await server._handle_search_context(arguments)

        assert len(result) == 1
        assert "No documents found" in result[0].text

    async def test_search_context_with_tags(self, server, sample_documents):
        """Test search with tag filtering."""
        # Mock Redis operations for tag filtering
        server.redis_client.sinter = AsyncMock(return_value={"doc-1", "doc-2"})

        # Mock document retrieval
        async def mock_get(key):
            doc_id = key.split(":")[-1]
            for doc in sample_documents[:2]:  # Only first two docs
                if doc.id == doc_id:
                    doc_data = doc.model_dump()
                    doc_data["created_at"] = doc.created_at.isoformat()
                    doc_data["updated_at"] = doc.updated_at.isoformat()
                    return json.dumps(doc_data)
            return None

        server.redis_client.get = AsyncMock(side_effect=mock_get)
        server._calculate_similarity = Mock(return_value=0.8)

        arguments = {
            "query": "artificial intelligence",
            "tags": ["ai", "machine-learning"]
        }

        result = await server._handle_search_context(arguments)

        assert len(result) == 1
        response_data = json.loads(result[0].text)
        assert response_data["results_count"] <= 2

    async def test_get_document(self, server, sample_document):
        """Test document retrieval."""
        # Mock Redis get operation
        doc_data = sample_document.model_dump()
        doc_data["created_at"] = sample_document.created_at.isoformat()
        doc_data["updated_at"] = sample_document.updated_at.isoformat()

        server.redis_client.get = AsyncMock(return_value=json.dumps(doc_data))

        arguments = {"document_id": "test-doc-1"}
        result = await server._handle_get_document(arguments)

        assert len(result) == 1
        response_data = json.loads(result[0].text)

        assert response_data["id"] == "test-doc-1"
        assert response_data["content"] == sample_document.content
        assert "embedding_dimensions" in response_data
        assert "embedding" not in response_data  # Should be removed for size

    async def test_get_document_not_found(self, server):
        """Test retrieving non-existent document."""
        server.redis_client.get = AsyncMock(return_value=None)

        arguments = {"document_id": "nonexistent"}
        result = await server._handle_get_document(arguments)

        assert len(result) == 1
        assert "Document not found" in result[0].text

    async def test_list_documents(self, server, sample_documents):
        """Test document listing."""
        # Mock Redis operations
        server.redis_client.smembers = AsyncMock(return_value={"doc-1", "doc-2", "doc-3"})

        # Mock document retrieval
        async def mock_get(key):
            doc_id = key.split(":")[-1]
            for doc in sample_documents:
                if doc.id == doc_id:
                    doc_data = doc.model_dump()
                    doc_data["created_at"] = doc.created_at.isoformat()
                    doc_data["updated_at"] = doc.updated_at.isoformat()
                    return json.dumps(doc_data)
            return None

        server.redis_client.get = AsyncMock(side_effect=mock_get)

        arguments = {"limit": 10}
        result = await server._handle_list_documents(arguments)

        assert len(result) == 1
        response_data = json.loads(result[0].text)

        assert response_data["total_documents"] == 3
        assert len(response_data["documents"]) == 3

    async def test_list_documents_with_tags(self, server, sample_documents):
        """Test document listing with tag filtering."""
        # Mock Redis operations for tag filtering
        server.redis_client.sinter = AsyncMock(return_value={"doc-1"})

        # Mock document retrieval
        async def mock_get(key):
            doc_id = key.split(":")[-1]
            if doc_id == "doc-1":
                doc_data = sample_documents[0].model_dump()
                doc_data["created_at"] = sample_documents[0].created_at.isoformat()
                doc_data["updated_at"] = sample_documents[0].updated_at.isoformat()
                return json.dumps(doc_data)
            return None

        server.redis_client.get = AsyncMock(side_effect=mock_get)

        arguments = {"tags": ["ai", "machine-learning"]}
        result = await server._handle_list_documents(arguments)

        assert len(result) == 1
        response_data = json.loads(result[0].text)

        assert response_data["total_documents"] == 1

    async def test_delete_document(self, server, sample_document):
        """Test document deletion."""
        # Mock Redis operations
        doc_data = sample_document.model_dump()
        doc_data["created_at"] = sample_document.created_at.isoformat()
        doc_data["updated_at"] = sample_document.updated_at.isoformat()

        server.redis_client.get = AsyncMock(return_value=json.dumps(doc_data))
        server.redis_client.delete = AsyncMock(return_value=1)
        server.redis_client.srem = AsyncMock(return_value=1)

        arguments = {"document_id": "test-doc-1"}
        result = await server._handle_delete_document(arguments)

        assert len(result) == 1
        response_data = json.loads(result[0].text)

        assert response_data["success"] is True
        assert response_data["deleted_document_id"] == "test-doc-1"

    async def test_delete_document_not_found(self, server):
        """Test deleting non-existent document."""
        server.redis_client.get = AsyncMock(return_value=None)
        server.redis_client.delete = AsyncMock(return_value=0)
        server.redis_client.srem = AsyncMock(return_value=0)

        arguments = {"document_id": "nonexistent"}
        result = await server._handle_delete_document(arguments)

        assert len(result) == 1
        assert "Document not found" in result[0].text

    async def test_update_document(self, server, sample_document):
        """Test document update."""
        # Mock Redis operations
        doc_data = sample_document.model_dump()
        doc_data["created_at"] = sample_document.created_at.isoformat()
        doc_data["updated_at"] = sample_document.updated_at.isoformat()

        server.redis_client.get = AsyncMock(return_value=json.dumps(doc_data))
        server.redis_client.set = AsyncMock(return_value=True)
        server.redis_client.srem = AsyncMock(return_value=1)
        server.redis_client.sadd = AsyncMock(return_value=1)

        arguments = {
            "document_id": "test-doc-1",
            "content": "Updated content",
            "metadata": {"source": "updated"},
            "tags": ["updated", "test"]
        }

        result = await server._handle_update_document(arguments)

        assert len(result) == 1
        response_data = json.loads(result[0].text)

        assert response_data["success"] is True
        assert response_data["document_id"] == "test-doc-1"
        assert "updated_at" in response_data

    async def test_clear_context(self, server):
        """Test clearing all context."""
        # Mock Redis operations
        server.redis_client.smembers = AsyncMock(return_value={"doc-1", "doc-2"})
        server.redis_client.delete = AsyncMock(return_value=1)
        server.redis_client.keys = AsyncMock(return_value=["context7:tag:ai", "context7:tag:ml"])

        arguments = {"confirm": True}
        result = await server._handle_clear_context(arguments)

        assert len(result) == 1
        response_data = json.loads(result[0].text)

        assert response_data["success"] is True
        assert response_data["deleted_documents"] == 2

    async def test_clear_context_without_confirm(self, server):
        """Test clearing context without confirmation."""
        arguments = {"confirm": False}
        result = await server._handle_clear_context(arguments)

        assert len(result) == 1
        assert "Must set confirm=true" in result[0].text

    async def test_get_context_stats(self, server):
        """Test getting context statistics."""
        # Mock Redis operations
        server.redis_client.scard = AsyncMock(return_value=5)
        server.redis_client.keys = AsyncMock(return_value=["tag1", "tag2", "tag3"])
        server.redis_client.smembers = AsyncMock(return_value={"doc-1", "doc-2"})
        server.redis_client.get = AsyncMock(return_value='{"token_count": 100}')
        server.redis_client.info = AsyncMock(return_value={
            "used_memory": 1024,
            "used_memory_human": "1K"
        })

        result = await server._handle_get_context_stats()

        assert len(result) == 1
        response_data = json.loads(result[0].text)

        assert response_data["document_count"] == 5
        assert response_data["tag_count"] == 3
        assert response_data["total_tokens"] == 200  # 2 docs * 100 tokens each
        assert "redis_info" in response_data

    async def test_similar_documents(self, server, sample_documents):
        """Test finding similar documents."""
        # Mock Redis operations
        ref_doc = sample_documents[0]
        doc_data = ref_doc.model_dump()
        doc_data["created_at"] = ref_doc.created_at.isoformat()
        doc_data["updated_at"] = ref_doc.updated_at.isoformat()

        server.redis_client.get = AsyncMock(return_value=json.dumps(doc_data))
        server.redis_client.smembers = AsyncMock(return_value={"doc-1", "doc-2", "doc-3"})

        # Mock document retrieval for similarity comparison
        async def mock_get_similar(key):
            doc_id = key.split(":")[-1]
            for doc in sample_documents:
                if doc.id == doc_id:
                    doc_data = doc.model_dump()
                    doc_data["created_at"] = doc.created_at.isoformat()
                    doc_data["updated_at"] = doc.updated_at.isoformat()
                    return json.dumps(doc_data)
            return None

        server.redis_client.get = AsyncMock(side_effect=mock_get_similar)
        server._calculate_similarity = Mock(return_value=0.8)

        arguments = {
            "document_id": "doc-1",
            "max_results": 2,
            "min_similarity": 0.7
        }

        result = await server._handle_similar_documents(arguments)

        assert len(result) == 1
        response_data = json.loads(result[0].text)

        assert response_data["reference_document_id"] == "doc-1"
        assert response_data["results_count"] >= 0

    async def test_embedding_generation(self, server):
        """Test embedding generation."""
        # Mock the embedding model
        server.embedding_model.encode = Mock(return_value=np.array([0.1, 0.2, 0.3]))

        embedding = server._generate_embedding("test text")

        assert embedding is not None
        assert len(embedding) == 3
        assert embedding == [0.1, 0.2, 0.3]

    async def test_embedding_generation_failure(self, server):
        """Test embedding generation failure."""
        # Mock the embedding model to raise exception
        server.embedding_model.encode = Mock(side_effect=Exception("Model error"))

        embedding = server._generate_embedding("test text")

        assert embedding is None

    async def test_similarity_calculation(self, server):
        """Test similarity calculation."""
        embedding1 = [1.0, 0.0, 0.0]
        embedding2 = [1.0, 0.0, 0.0]

        similarity = server._calculate_similarity(embedding1, embedding2)

        assert similarity == 1.0  # Perfect similarity

    async def test_similarity_calculation_failure(self, server):
        """Test similarity calculation failure."""
        # Test with invalid embeddings
        embedding1 = []
        embedding2 = [1.0, 0.0, 0.0]

        similarity = server._calculate_similarity(embedding1, embedding2)

        assert similarity == 0.0  # Should return 0 on error

    async def test_token_counting(self, server):
        """Test token counting."""
        # Mock tokenizer
        server.tokenizer.encode = Mock(return_value=["token1", "token2", "token3"])

        count = server._count_tokens("test text")

        assert count == 3

    async def test_token_counting_fallback(self, server):
        """Test token counting fallback when tokenizer fails."""
        # Mock tokenizer to raise exception
        server.tokenizer.encode = Mock(side_effect=Exception("Tokenizer error"))

        count = server._count_tokens("test text with four words")

        # Should use fallback calculation
        assert count > 0

    async def test_snippet_creation(self, server):
        """Test snippet creation from content."""
        content = "This is a test. Machine learning is important. Python is useful."
        query = "machine learning"

        snippet = server._create_snippet(content, query)

        assert "Machine learning" in snippet

    async def test_snippet_creation_no_match(self, server):
        """Test snippet creation when no sentences match."""
        content = "This is a test document without the query terms."
        query = "nonexistent terms"

        snippet = server._create_snippet(content, query, max_length=20)

        assert len(snippet) <= 20
        assert snippet == content[:20]

    async def test_tool_call_unknown_tool(self, server):
        """Test calling unknown tool."""
        # This would normally be handled by the server's call_tool handler
        # We'll test the error handling directly

        with pytest.raises(ValueError, match="Unknown tool"):
            await server.server._call_tool_handler("unknown_tool", {})


class TestContextDocument:
    """Test cases for ContextDocument model."""

    def test_document_creation(self):
        """Test creating a document."""
        doc = ContextDocument(
            id="test-1",
            content="Test content",
            metadata={"source": "test"},
            tags=["test"],
            token_count=10
        )

        assert doc.id == "test-1"
        assert doc.content == "Test content"
        assert doc.metadata == {"source": "test"}
        assert doc.tags == ["test"]
        assert doc.token_count == 10
        assert doc.created_at is not None
        assert doc.updated_at is not None

    def test_document_defaults(self):
        """Test document with default values."""
        doc = ContextDocument(
            id="test-2",
            content="Test content"
        )

        assert doc.metadata == {}
        assert doc.tags == []
        assert doc.token_count == 0
        assert doc.embedding is None


class TestSearchResult:
    """Test cases for SearchResult model."""

    def test_search_result_creation(self):
        """Test creating a search result."""
        doc = ContextDocument(
            id="test-1",
            content="Test content"
        )

        result = SearchResult(
            document=doc,
            similarity=0.8,
            snippet="Test snippet"
        )

        assert result.document == doc
        assert result.similarity == 0.8
        assert result.snippet == "Test snippet"


class TestContextQuery:
    """Test cases for ContextQuery model."""

    def test_query_creation(self):
        """Test creating a query."""
        query = ContextQuery(
            query="test query",
            max_results=10,
            min_similarity=0.5,
            tags=["test"],
            include_metadata=False
        )

        assert query.query == "test query"
        assert query.max_results == 10
        assert query.min_similarity == 0.5
        assert query.tags == ["test"]
        assert query.include_metadata is False

    def test_query_defaults(self):
        """Test query with default values."""
        query = ContextQuery(query="test")

        assert query.max_results == 5
        assert query.min_similarity == 0.7
        assert query.tags == []
        assert query.include_metadata is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
