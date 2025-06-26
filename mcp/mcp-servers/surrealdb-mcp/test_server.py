#!/usr/bin/env python3
"""
Test Suite for SurrealDB MCP Server

Comprehensive test coverage for the SurrealDB MCP Server including:
- Connection testing (SurrealDB)
- Document CRUD operations
- Graph operations and traversal
- Key-value operations
- Query execution
- MCP protocol compliance
- Error handling and edge cases
"""

import asyncio
import json
import os
import tempfile
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any
from unittest.mock import Mock, AsyncMock, patch
import pytest

# Import the server components
import sys
from pathlib import Path
# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from surrealdb_mcp.server import SurrealDBServer, DatabaseDocument, GraphNode, GraphRelation, QueryResult
from mcp import types


class TestSurrealDBServer:
    """Test cases for SurrealDB MCP Server."""

    @pytest.fixture
    async def server(self):
        """Create a test server instance."""
        server = SurrealDBServer()
        # Mock the SurrealDB connection
        server.db = AsyncMock()
        server.connected = True
        server.namespace = "test_ns"
        server.database = "test_db"
        return server

    @pytest.fixture
    def sample_document(self):
        """Create a sample document for testing."""
        return {
            "id": "users:test-1",
            "name": "Test User",
            "email": "test@example.com",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

    @pytest.fixture
    def sample_graph_data(self):
        """Create sample graph data for testing."""
        return {
            "nodes": [
                {"id": "person:alice", "name": "Alice", "type": "person"},
                {"id": "person:bob", "name": "Bob", "type": "person"},
                {"id": "company:acme", "name": "ACME Corp", "type": "company"}
            ],
            "relations": [
                {"from": "person:alice", "to": "company:acme", "type": "works_at"},
                {"from": "person:bob", "to": "company:acme", "type": "works_at"},
                {"from": "person:alice", "to": "person:bob", "type": "knows"}
            ]
        }

    @pytest.mark.asyncio
    async def test_server_initialization(self, server):
        """Test server initialization."""
        assert server.server.name == "surrealdb-mcp"
        assert server.namespace == "test_ns"
        assert server.database == "test_db"
        assert server.connected is True

    @pytest.mark.asyncio
    async def test_list_tools(self, server):
        """Test tool listing."""
        tools = await server.server._list_tools_handler()

        expected_tools = [
            "surrealdb_status",
            "connect_database",
            "execute_query",
            "create_document",
            "get_document",
            "update_document",
            "delete_document",
            "list_tables",
            "query_table",
            "create_relation",
            "get_relations",
            "graph_traverse",
            "set_key_value",
            "get_key_value",
            "delete_key_value",
            "get_database_info"
        ]

        tool_names = [tool.name for tool in tools]
        for expected_tool in expected_tools:
            assert expected_tool in tool_names

    @pytest.mark.asyncio
    async def test_status_check(self, server):
        """Test status check functionality."""
        # Mock successful database info query
        server.db.query = AsyncMock(return_value=[{"status": "ok"}])

        result = await server._handle_status()

        assert len(result) == 1
        status_data = json.loads(result[0].text)

        assert status_data["server"] == "SurrealDB MCP Server"
        assert status_data["connected"] is True
        assert status_data["namespace"] == "test_ns"
        assert status_data["database"] == "test_db"
        assert status_data["query_test"] == "Success"

    @pytest.mark.asyncio
    async def test_status_check_connection_error(self, server):
        """Test status check with connection error."""
        # Mock database query to raise exception
        server.db.query = AsyncMock(side_effect=Exception("Connection lost"))

        result = await server._handle_status()

        assert len(result) == 1
        status_data = json.loads(result[0].text)

        assert "Error: Connection lost" in status_data["database_info"]
        assert status_data["query_test"] == "Failed"

    @pytest.mark.asyncio
    async def test_connect_database(self, server):
        """Test database connection."""
        # Mock connection methods
        server.db = AsyncMock()
        server.db.connect = AsyncMock()
        server.db.signin = AsyncMock()
        server.db.use = AsyncMock()

        arguments = {
            "url": "ws://localhost:8000/rpc",
            "username": "test",
            "password": "test",
            "namespace": "test_namespace",
            "database": "test_database"
        }

        result = await server._handle_connect_database(arguments)

        assert len(result) == 1
        response_data = json.loads(result[0].text)

        assert response_data["success"] is True
        assert response_data["namespace"] == "test_namespace"
        assert response_data["database"] == "test_database"

    @pytest.mark.asyncio
    async def test_execute_query(self, server):
        """Test query execution."""
        # Mock query execution
        mock_result = [{"id": "users:1", "name": "Test User"}]
        server.db.query = AsyncMock(return_value=mock_result)

        arguments = {
            "query": "SELECT * FROM users WHERE name = 'Test User'",
            "variables": {"name": "Test User"}
        }

        result = await server._handle_execute_query(arguments)

        assert len(result) == 1
        response_data = json.loads(result[0].text)

        assert response_data["status"] == "success"
        assert response_data["result"] == mock_result
        assert response_data["result_count"] == 1

    @pytest.mark.asyncio
    async def test_execute_query_empty(self, server):
        """Test executing empty query."""
        arguments = {"query": ""}

        result = await server._handle_execute_query(arguments)

        assert len(result) == 1
        assert "Query cannot be empty" in result[0].text

    @pytest.mark.asyncio
    async def test_create_document(self, server, sample_document):
        """Test document creation."""
        # Mock document creation
        server.db.create = AsyncMock(return_value=sample_document)

        arguments = {
            "table": "users",
            "data": {"name": "Test User", "email": "test@example.com"},
            "id": "test-1"
        }

        result = await server._handle_create_document(arguments)

        assert len(result) == 1
        response_data = json.loads(result[0].text)

        assert response_data["success"] is True
        assert response_data["document"] == sample_document

    @pytest.mark.asyncio
    async def test_create_document_no_table(self, server):
        """Test creating document without table name."""
        arguments = {"data": {"name": "Test"}}

        result = await server._handle_create_document(arguments)

        assert len(result) == 1
        assert "Table name is required" in result[0].text

    @pytest.mark.asyncio
    async def test_get_document(self, server, sample_document):
        """Test document retrieval."""
        # Mock document retrieval
        server.db.select = AsyncMock(return_value=sample_document)

        arguments = {"id": "users:test-1"}

        result = await server._handle_get_document(arguments)

        assert len(result) == 1
        response_data = json.loads(result[0].text)

        assert response_data["success"] is True
        assert response_data["document"] == sample_document

    @pytest.mark.asyncio
    async def test_get_document_not_found(self, server):
        """Test retrieving non-existent document."""
        # Mock document not found
        server.db.select = AsyncMock(return_value=None)

        arguments = {"id": "users:nonexistent"}

        result = await server._handle_get_document(arguments)

        assert len(result) == 1
        response_data = json.loads(result[0].text)

        assert response_data["success"] is False
        assert "Document not found" in response_data["message"]

    @pytest.mark.asyncio
    async def test_update_document(self, server, sample_document):
        """Test document update."""
        # Mock document update
        updated_doc = sample_document.copy()
        updated_doc["name"] = "Updated User"
        server.db.merge = AsyncMock(return_value=updated_doc)

        arguments = {
            "id": "users:test-1",
            "data": {"name": "Updated User"},
            "merge": True
        }

        result = await server._handle_update_document(arguments)

        assert len(result) == 1
        response_data = json.loads(result[0].text)

        assert response_data["success"] is True
        assert response_data["document"]["name"] == "Updated User"

    @pytest.mark.asyncio
    async def test_update_document_replace(self, server, sample_document):
        """Test document replacement (non-merge update)."""
        # Mock document replacement
        server.db.update = AsyncMock(return_value=sample_document)

        arguments = {
            "id": "users:test-1",
            "data": {"name": "Replaced User"},
            "merge": False
        }

        result = await server._handle_update_document(arguments)

        assert len(result) == 1
        response_data = json.loads(result[0].text)

        assert response_data["success"] is True
        # Should use update method instead of merge
        server.db.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_document(self, server, sample_document):
        """Test document deletion."""
        # Mock document deletion
        server.db.delete = AsyncMock(return_value=sample_document)

        arguments = {"id": "users:test-1"}

        result = await server._handle_delete_document(arguments)

        assert len(result) == 1
        response_data = json.loads(result[0].text)

        assert response_data["success"] is True
        assert "deleted successfully" in response_data["message"]

    @pytest.mark.asyncio
    async def test_list_tables(self, server):
        """Test table listing."""
        # Mock table listing query
        mock_db_info = [{"tb": {"users": {}, "posts": {}, "comments": {}}}]
        server.db.query = AsyncMock(return_value=mock_db_info)

        result = await server._handle_list_tables()

        assert len(result) == 1
        response_data = json.loads(result[0].text)

        assert response_data["success"] is True
        assert "users" in response_data["tables"]
        assert "posts" in response_data["tables"]
        assert "comments" in response_data["tables"]
        assert response_data["count"] == 3

    @pytest.mark.asyncio
    async def test_query_table(self, server):
        """Test table querying."""
        # Mock table query
        mock_results = [
            {"id": "users:1", "name": "Alice"},
            {"id": "users:2", "name": "Bob"}
        ]
        server.db.query = AsyncMock(return_value=mock_results)

        arguments = {
            "table": "users",
            "where": "name CONTAINS 'A'",
            "limit": 10,
            "order_by": "name ASC"
        }

        result = await server._handle_query_table(arguments)

        assert len(result) == 1
        response_data = json.loads(result[0].text)

        assert response_data["success"] is True
        assert response_data["table"] == "users"
        assert response_data["results"] == mock_results
        assert response_data["count"] == 2

    @pytest.mark.asyncio
    async def test_query_table_no_table(self, server):
        """Test querying without table name."""
        arguments = {}

        result = await server._handle_query_table(arguments)

        assert len(result) == 1
        assert "Table name is required" in result[0].text

    @pytest.mark.asyncio
    async def test_create_relation(self, server):
        """Test relationship creation."""
        # Mock relationship creation
        mock_relation = {
            "id": "works_at:alice_acme",
            "in": "person:alice",
            "out": "company:acme"
        }
        server.db.query = AsyncMock(return_value=[mock_relation])

        arguments = {
            "from_id": "person:alice",
            "to_id": "company:acme",
            "relation_type": "works_at",
            "properties": {"role": "developer", "since": "2023-01-01"}
        }

        result = await server._handle_create_relation(arguments)

        assert len(result) == 1
        response_data = json.loads(result[0].text)

        assert response_data["success"] is True
        assert response_data["from_id"] == "person:alice"
        assert response_data["to_id"] == "company:acme"
        assert response_data["relation_type"] == "works_at"

    @pytest.mark.asyncio
    async def test_create_relation_missing_params(self, server):
        """Test creating relationship with missing parameters."""
        arguments = {"from_id": "person:alice"}

        result = await server._handle_create_relation(arguments)

        assert len(result) == 1
        assert "from_id, to_id, and relation_type are required" in result[0].text

    @pytest.mark.asyncio
    async def test_get_relations(self, server):
        """Test relationship retrieval."""
        # Mock relationship query
        mock_relations = [
            {"id": "works_at:alice_acme", "out": "company:acme"},
            {"id": "knows:alice_bob", "out": "person:bob"}
        ]
        server.db.query = AsyncMock(return_value=mock_relations)

        arguments = {
            "record_id": "person:alice",
            "direction": "out",
            "relation_type": "works_at"
        }

        result = await server._handle_get_relations(arguments)

        assert len(result) == 1
        response_data = json.loads(result[0].text)

        assert response_data["success"] is True
        assert response_data["record_id"] == "person:alice"
        assert response_data["direction"] == "out"
        assert response_data["relation_type"] == "works_at"

    @pytest.mark.asyncio
    async def test_graph_traverse(self, server):
        """Test graph traversal."""
        # Mock traversal query
        mock_traversal = [
            {"id": "person:alice", "connections": ["company:acme", "person:bob"]}
        ]
        server.db.query = AsyncMock(return_value=mock_traversal)

        arguments = {
            "start_id": "person:alice",
            "depth": 2,
            "relation_types": ["works_at", "knows"]
        }

        result = await server._handle_graph_traverse(arguments)

        assert len(result) == 1
        response_data = json.loads(result[0].text)

        assert response_data["success"] is True
        assert response_data["start_id"] == "person:alice"
        assert response_data["depth"] == 2
        assert response_data["relation_types"] == ["works_at", "knows"]

    @pytest.mark.asyncio
    async def test_set_key_value(self, server):
        """Test key-value setting."""
        # Mock key-value creation
        mock_kv = {
            "id": "kv:test_key",
            "key": "test_key",
            "value": "test_value"
        }
        server.db.create = AsyncMock(return_value=mock_kv)

        arguments = {
            "key": "test_key",
            "value": "test_value",
            "ttl": 3600
        }

        result = await server._handle_set_key_value(arguments)

        assert len(result) == 1
        response_data = json.loads(result[0].text)

        assert response_data["success"] is True
        assert response_data["key"] == "test_key"
        assert response_data["value"] == "test_value"
        assert response_data["ttl"] == 3600

    @pytest.mark.asyncio
    async def test_set_key_value_no_key(self, server):
        """Test setting key-value without key."""
        arguments = {"value": "test_value"}

        result = await server._handle_set_key_value(arguments)

        assert len(result) == 1
        assert "Key is required" in result[0].text

    @pytest.mark.asyncio
    async def test_get_key_value(self, server):
        """Test key-value retrieval."""
        # Mock key-value retrieval
        mock_kv = {
            "key": "test_key",
            "value": "test_value",
            "created_at": datetime.utcnow().isoformat()
        }
        server.db.select = AsyncMock(return_value=mock_kv)

        arguments = {"key": "test_key"}

        result = await server._handle_get_key_value(arguments)

        assert len(result) == 1
        response_data = json.loads(result[0].text)

        assert response_data["success"] is True
        assert response_data["key"] == "test_key"
        assert response_data["value"] == "test_value"

    @pytest.mark.asyncio
    async def test_get_key_value_expired(self, server):
        """Test retrieving expired key-value."""
        # Mock expired key-value
        mock_kv = {
            "key": "test_key",
            "value": "test_value",
            "expires_at": (datetime.utcnow() - timedelta(hours=1)).isoformat()
        }
        server.db.select = AsyncMock(return_value=mock_kv)
        server.db.delete = AsyncMock()

        arguments = {"key": "test_key"}

        result = await server._handle_get_key_value(arguments)

        assert len(result) == 1
        response_data = json.loads(result[0].text)

        assert response_data["success"] is False
        assert "Key expired" in response_data["message"]
        # Should have deleted the expired key
        server.db.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_key_value_not_found(self, server):
        """Test retrieving non-existent key."""
        server.db.select = AsyncMock(return_value=None)

        arguments = {"key": "nonexistent_key"}

        result = await server._handle_get_key_value(arguments)

        assert len(result) == 1
        response_data = json.loads(result[0].text)

        assert response_data["success"] is False
        assert "Key not found" in response_data["message"]

    @pytest.mark.asyncio
    async def test_delete_key_value(self, server):
        """Test key-value deletion."""
        # Mock key-value deletion
        mock_deleted = {"id": "kv:test_key"}
        server.db.delete = AsyncMock(return_value=mock_deleted)

        arguments = {"key": "test_key"}

        result = await server._handle_delete_key_value(arguments)

        assert len(result) == 1
        response_data = json.loads(result[0].text)

        assert response_data["success"] is True
        assert "deleted successfully" in response_data["message"]

    @pytest.mark.asyncio
    async def test_get_database_info(self, server):
        """Test database information retrieval."""
        # Mock database info queries
        mock_db_info = [{"tb": {"users": {}, "posts": {}}}]
        mock_ns_info = [{"ns": "test_namespace"}]

        def mock_query(query):
            if "INFO FOR DB" in query:
                return asyncio.create_future().set_result(mock_db_info)
            elif "INFO FOR NS" in query:
                return asyncio.create_future().set_result(mock_ns_info)
            elif "count()" in query:
                return asyncio.create_future().set_result([{"count": 10}])
            return asyncio.create_future().set_result([])

        server.db.query = AsyncMock(side_effect=mock_query)

        result = await server._handle_get_database_info()

        assert len(result) == 1
        response_data = json.loads(result[0].text)

        assert response_data["success"] is True
        assert response_data["namespace"] == "test_ns"
        assert response_data["database"] == "test_db"
        assert "database_info" in response_data
        assert "namespace_info" in response_data

    @pytest.mark.asyncio
    async def test_ensure_connected_not_connected(self, server):
        """Test _ensure_connected when not connected."""
        server.connected = False

        with pytest.raises(Exception, match="Not connected to SurrealDB"):
            await server._ensure_connected()

    @pytest.mark.asyncio
    async def test_connect_with_retry_max_attempts(self, server):
        """Test connection retry logic reaching max attempts."""
        server.db = AsyncMock()
        server.db.connect = AsyncMock(side_effect=Exception("Connection failed"))

        with pytest.raises(Exception, match="Failed to connect after"):
            await server._connect_with_retry(
                "ws://localhost:8000/rpc", "root", "root", "test", "test", max_retries=2
            )

    @pytest.mark.asyncio
    async def test_connect_with_retry_success_after_failure(self, server):
        """Test successful connection after initial failure."""
        server.db = AsyncMock()

        # First call fails, second succeeds
        connect_calls = [Exception("Connection failed"), None]
        server.db.connect = AsyncMock(side_effect=connect_calls)
        server.db.signin = AsyncMock()
        server.db.use = AsyncMock()

        await server._connect_with_retry(
            "ws://localhost:8000/rpc", "root", "root", "test", "test"
        )

        assert server.connected is True
        assert server.namespace == "test"
        assert server.database == "test"


class TestDatabaseDocument:
    """Test cases for DatabaseDocument model."""

    def test_document_creation(self):
        """Test creating a document."""
        doc = DatabaseDocument(
            id="users:test-1",
            table="users",
            data={"name": "Test User", "email": "test@example.com"},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        assert doc.id == "users:test-1"
        assert doc.table == "users"
        assert doc.data["name"] == "Test User"
        assert doc.data["email"] == "test@example.com"

    def test_document_defaults(self):
        """Test document with default values."""
        doc = DatabaseDocument(
            table="users",
            data={"name": "Test User"}
        )

        assert doc.id is None
        assert doc.created_at is None
        assert doc.updated_at is None


class TestGraphNode:
    """Test cases for GraphNode model."""

    def test_node_creation(self):
        """Test creating a graph node."""
        node = GraphNode(
            id="person:alice",
            table="person",
            properties={"name": "Alice", "age": 30}
        )

        assert node.id == "person:alice"
        assert node.table == "person"
        assert node.properties["name"] == "Alice"
        assert node.properties["age"] == 30

    def test_node_defaults(self):
        """Test node with default values."""
        node = GraphNode(
            id="person:bob",
            table="person"
        )

        assert node.properties == {}


class TestGraphRelation:
    """Test cases for GraphRelation model."""

    def test_relation_creation(self):
        """Test creating a graph relation."""
        relation = GraphRelation(
            from_node="person:alice",
            to_node="company:acme",
            relation_type="works_at",
            properties={"role": "developer", "since": "2023-01-01"}
        )

        assert relation.from_node == "person:alice"
        assert relation.to_node == "company:acme"
        assert relation.relation_type == "works_at"
        assert relation.properties["role"] == "developer"

    def test_relation_defaults(self):
        """Test relation with default values."""
        relation = GraphRelation(
            from_node="person:alice",
            to_node="person:bob",
            relation_type="knows"
        )

        assert relation.id is None
        assert relation.properties == {}


class TestQueryResult:
    """Test cases for QueryResult model."""

    def test_query_result_creation(self):
        """Test creating a query result."""
        result = QueryResult(
            status="success",
            time="0.123s",
            result=[{"id": "users:1", "name": "Alice"}],
            count=1
        )

        assert result.status == "success"
        assert result.time == "0.123s"
        assert result.result[0]["name"] == "Alice"
        assert result.count == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
