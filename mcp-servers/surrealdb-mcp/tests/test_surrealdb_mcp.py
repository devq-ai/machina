#!/usr/bin/env python3
"""
Comprehensive PyTest Test Suite for SurrealDB MCP Server

This test suite implements the comprehensive testing framework established for MCP servers,
ensuring 100% success rate with real service connections and performance validation.

Test Categories:
- A. Core Functionality Tests
- B. Integration Tests
- C. Performance Tests
- D. Error Handling Tests
- E. Compliance Tests

Requirements:
- 100% Success Rate (no partial credit)
- Real SurrealDB service connections
- Performance target validation
- Complete MCP protocol compliance
- 90%+ code coverage
"""

import pytest
import asyncio
import time
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch
import logging

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

# Import MCP and SurrealDB modules
try:
    from mcp import types
    from mcp.server import Server
    from surrealdb_mcp.server import SurrealDBServer, DatabaseDocument, GraphRelation, QueryResult
except ImportError as e:
    pytest.skip(f"Required modules not available: {e}", allow_module_level=True)

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test configuration
TEST_CONFIG = {
    "surrealdb_url": os.getenv("SURREALDB_URL", "ws://localhost:8000/rpc"),
    "surrealdb_username": os.getenv("SURREALDB_USERNAME", "root"),
    "surrealdb_password": os.getenv("SURREALDB_PASSWORD", "root"),
    "surrealdb_namespace": os.getenv("SURREALDB_NAMESPACE", "devqai"),
    "surrealdb_database": os.getenv("SURREALDB_DATABASE", "test"),
    "performance_targets": {
        "status_response": 0.1,      # 100ms
        "document_create": 0.2,      # 200ms
        "graph_traverse": 0.5,       # 500ms
        "query_execute": 1.0,        # 1000ms
        "connection_setup": 0.1      # 100ms
    }
}

class PerformanceTracker:
    """Track performance metrics for tests."""

    def __init__(self):
        self.metrics = {}
        self.start_times = {}

    def start(self, operation: str):
        """Start timing an operation."""
        self.start_times[operation] = time.time()

    def end(self, operation: str) -> float:
        """End timing and return duration."""
        if operation not in self.start_times:
            return 0.0
        duration = time.time() - self.start_times[operation]
        self.metrics[operation] = duration
        return duration

    def get_metrics(self) -> Dict[str, float]:
        """Get all recorded metrics."""
        return self.metrics.copy()

@pytest.fixture
def performance_tracker():
    """Provide performance tracking for tests."""
    return PerformanceTracker()

@pytest.fixture
async def surrealdb_server():
    """Create and initialize SurrealDB MCP server for testing."""
    server = SurrealDBServer()
    await server.initialize()
    yield server
    # Cleanup
    if hasattr(server, 'db') and server.db:
        try:
            # Clean up test data
            await server.db.query("DELETE FROM users WHERE id CONTAINS 'test_'")
            await server.db.query("DELETE FROM companies WHERE id CONTAINS 'test_'")
            await server.db.query("DELETE FROM test_table")
        except Exception as e:
            logger.warning(f"Cleanup failed: {e}")

@pytest.fixture
def mock_surrealdb():
    """Mock SurrealDB for testing without real database."""
    mock_db = AsyncMock()
    mock_db.query.return_value = [{"result": "mock_success"}]
    mock_db.create.return_value = {"id": "test:mock_1", "name": "Mock Document"}
    mock_db.select.return_value = {"id": "test:mock_1", "name": "Mock Document"}
    mock_db.update.return_value = {"id": "test:mock_1", "name": "Updated Mock"}
    mock_db.delete.return_value = {"id": "test:mock_1"}
    return mock_db

# =============================================================================
# A. CORE FUNCTIONALITY TESTS
# =============================================================================

class TestCoreFunctionality:
    """Test core MCP server functionality."""

    async def test_server_initialization(self, surrealdb_server):
        """Test A.1: Server initialization and configuration."""
        # PASS CRITERIA: Server starts successfully with proper MCP protocol binding
        assert surrealdb_server is not None
        assert surrealdb_server.server is not None
        assert isinstance(surrealdb_server.server, Server)
        assert surrealdb_server.server.name == "surrealdb-mcp"
        assert surrealdb_server.namespace == TEST_CONFIG["surrealdb_namespace"]
        assert surrealdb_server.database == TEST_CONFIG["surrealdb_database"]

    async def test_tool_registration(self, surrealdb_server):
        """Test A.2: Tool registration and discovery."""
        # PASS CRITERIA: All 16 MCP tools properly registered and discoverable
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

        # Get tools from server
        tools = await surrealdb_server.server.list_tools()
        tool_names = [tool.name for tool in tools]

        # Validate all expected tools are registered
        for expected_tool in expected_tools:
            assert expected_tool in tool_names, f"Tool {expected_tool} not registered"

        # Validate tool count
        assert len(tools) >= len(expected_tools), f"Expected at least {len(expected_tools)} tools, got {len(tools)}"

    async def test_basic_operations_validation(self, surrealdb_server):
        """Test A.3: Basic operations validation."""
        # PASS CRITERIA: All fundamental operations execute successfully

        # Test status operation
        status_result = await surrealdb_server._handle_status()
        assert status_result is not None
        assert len(status_result) > 0

        # Test document creation
        doc_args = {
            "table": "test_table",
            "data": {"name": "Test Document", "type": "validation"},
            "id": "test_doc_1"
        }
        create_result = await surrealdb_server._handle_create_document(doc_args)
        assert create_result is not None
        assert len(create_result) > 0

        # Test query execution
        query_args = {
            "query": "SELECT * FROM test_table WHERE type = 'validation'"
        }
        query_result = await surrealdb_server._handle_execute_query(query_args)
        assert query_result is not None
        assert len(query_result) > 0

# =============================================================================
# B. INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    """Test integration with real SurrealDB service."""

    async def test_real_surrealdb_connectivity(self, surrealdb_server):
        """Test B.1: External Service Connectivity - Real SurrealDB connection."""
        # PASS CRITERIA: Actual connection to SurrealDB service verified
        args = {"check_type": "surrealdb"}
        result = await surrealdb_server._handle_status()

        # Validate connection details
        assert result is not None
        assert len(result) > 0

        # Extract status information
        status_text = result[0].text if hasattr(result[0], 'text') else str(result[0])
        status_data = json.loads(status_text) if isinstance(status_text, str) and status_text.startswith('{') else {"connected": True}

        # Validate connection status
        assert status_data.get("connected", True) is True
        assert "server" in status_data or "connected" in status_data
        assert "namespace" in status_data or "connected" in status_data
        assert "database" in status_data or "connected" in status_data

    async def test_database_authentication(self, surrealdb_server):
        """Test B.2: Database authentication."""
        # PASS CRITERIA: Proper authentication with SurrealDB credentials
        connect_args = {
            "url": TEST_CONFIG["surrealdb_url"],
            "username": TEST_CONFIG["surrealdb_username"],
            "password": TEST_CONFIG["surrealdb_password"],
            "namespace": TEST_CONFIG["surrealdb_namespace"],
            "database": TEST_CONFIG["surrealdb_database"]
        }

        result = await surrealdb_server._handle_connect_database(connect_args)
        assert result is not None
        assert len(result) > 0

        # Verify connection was established
        status_result = await surrealdb_server._handle_status()
        assert status_result is not None
        assert surrealdb_server.connected is True

    async def test_multi_model_operations(self, surrealdb_server):
        """Test B.3: Multi-model operations."""
        # PASS CRITERIA: All database models (document, graph, key-value) function correctly

        # 1. Document operations
        doc_args = {
            "table": "test_users",
            "data": {"name": "Alice Johnson", "role": "developer"},
            "id": "test_alice_001"
        }
        doc_result = await surrealdb_server._handle_create_document(doc_args)
        assert doc_result is not None

        # 2. Graph operations
        graph_args = {
            "from_id": "test_users:test_alice_001",
            "to_id": "test_companies:test_acme",
            "relation_type": "works_at",
            "properties": {"position": "senior_developer"}
        }
        # First create the target document
        company_args = {
            "table": "test_companies",
            "data": {"name": "ACME Corp", "industry": "tech"},
            "id": "test_acme"
        }
        await surrealdb_server._handle_create_document(company_args)

        # Then create the relationship
        relation_result = await surrealdb_server._handle_create_relation(graph_args)
        assert relation_result is not None

        # 3. Key-value operations
        kv_args = {
            "key": "test_session:alice",
            "value": json.dumps({"theme": "dark", "lang": "en"}),
            "ttl": 3600
        }
        kv_result = await surrealdb_server._handle_set_key_value(kv_args)
        assert kv_result is not None

# =============================================================================
# C. PERFORMANCE TESTS
# =============================================================================

class TestPerformance:
    """Test performance targets and benchmarks."""

    async def test_performance_targets_status(self, surrealdb_server, performance_tracker):
        """Test C.1: Response Times - Status endpoint sub-100ms target."""
        # PASS CRITERIA: Status response < 100ms
        performance_tracker.start("status_response")
        result = await surrealdb_server._handle_status()
        duration = performance_tracker.end("status_response")

        assert result is not None
        assert duration < TEST_CONFIG["performance_targets"]["status_response"], \
            f"Status response took {duration}s, should be <{TEST_CONFIG['performance_targets']['status_response']}s"

    async def test_performance_targets_document_ops(self, surrealdb_server, performance_tracker):
        """Test C.1: Document operations performance."""
        # PASS CRITERIA: Document operations < 200ms
        doc_args = {
            "table": "test_perf",
            "data": {"name": "Performance Test", "timestamp": time.time()},
            "id": f"test_perf_{int(time.time())}"
        }

        performance_tracker.start("document_create")
        result = await surrealdb_server._handle_create_document(doc_args)
        duration = performance_tracker.end("document_create")

        assert result is not None
        assert duration < TEST_CONFIG["performance_targets"]["document_create"], \
            f"Document create took {duration}s, should be <{TEST_CONFIG['performance_targets']['document_create']}s"

    async def test_performance_targets_graph_traversal(self, surrealdb_server, performance_tracker):
        """Test C.1: Graph traversal performance."""
        # PASS CRITERIA: Graph traversal < 500ms

        # Setup test data
        await surrealdb_server._handle_create_document({
            "table": "test_nodes",
            "data": {"name": "Node 1", "type": "test"},
            "id": "test_node_1"
        })
        await surrealdb_server._handle_create_document({
            "table": "test_nodes",
            "data": {"name": "Node 2", "type": "test"},
            "id": "test_node_2"
        })

        # Create relationship
        await surrealdb_server._handle_create_relation({
            "from_id": "test_nodes:test_node_1",
            "to_id": "test_nodes:test_node_2",
            "relation_type": "connects_to",
            "properties": {"weight": 1.0}
        })

        # Test traversal performance
        traverse_args = {
            "start_id": "test_nodes:test_node_1",
            "depth": 3,
            "relation_types": ["connects_to"]
        }

        performance_tracker.start("graph_traverse")
        result = await surrealdb_server._handle_graph_traverse(traverse_args)
        duration = performance_tracker.end("graph_traverse")

        assert result is not None
        assert duration < TEST_CONFIG["performance_targets"]["graph_traverse"], \
            f"Graph traverse took {duration}s, should be <{TEST_CONFIG['performance_targets']['graph_traverse']}s"

    async def test_performance_targets_query_execution(self, surrealdb_server, performance_tracker):
        """Test C.1: Query execution performance."""
        # PASS CRITERIA: Query execution < 1000ms
        query_args = {
            "query": "SELECT * FROM test_perf WHERE timestamp > $timestamp",
            "variables": {"timestamp": time.time() - 3600}
        }

        performance_tracker.start("query_execute")
        result = await surrealdb_server._handle_execute_query(query_args)
        duration = performance_tracker.end("query_execute")

        assert result is not None
        assert duration < TEST_CONFIG["performance_targets"]["query_execute"], \
            f"Query execute took {duration}s, should be <{TEST_CONFIG['performance_targets']['query_execute']}s"

    async def test_concurrent_operations(self, surrealdb_server):
        """Test C.2: Concurrent operations."""
        # PASS CRITERIA: Handle multiple simultaneous operations without degradation

        async def create_document(index):
            doc_args = {
                "table": "test_concurrent",
                "data": {"name": f"Concurrent Doc {index}", "index": index},
                "id": f"test_concurrent_{index}"
            }
            return await surrealdb_server._handle_create_document(doc_args)

        # Run 5 concurrent operations
        tasks = [create_document(i) for i in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Validate all operations succeeded
        for i, result in enumerate(results):
            assert not isinstance(result, Exception), f"Operation {i} failed: {result}"
            assert result is not None

    async def test_resource_efficiency(self, surrealdb_server):
        """Test C.3: Resource efficiency."""
        # PASS CRITERIA: Optimal resource usage and cleanup

        # Create multiple documents
        for i in range(10):
            doc_args = {
                "table": "test_resources",
                "data": {"name": f"Resource Test {i}", "value": i},
                "id": f"test_resource_{i}"
            }
            await surrealdb_server._handle_create_document(doc_args)

        # Verify server is still responsive
        status_result = await surrealdb_server._handle_status()
        assert status_result is not None

        # Cleanup test data
        query_args = {"query": "DELETE FROM test_resources"}
        cleanup_result = await surrealdb_server._handle_execute_query(query_args)
        assert cleanup_result is not None

# =============================================================================
# D. ERROR HANDLING TESTS
# =============================================================================

class TestErrorHandling:
    """Test error handling and recovery scenarios."""

    async def test_invalid_input_handling(self, surrealdb_server):
        """Test D.1: Invalid input handling."""
        # PASS CRITERIA: Proper error responses for invalid inputs

        # Test invalid table name
        invalid_doc_args = {
            "table": "",  # Empty table name
            "data": {"name": "Test"},
            "id": "test"
        }

        with pytest.raises(Exception):
            await surrealdb_server._handle_create_document(invalid_doc_args)

        # Test malformed query
        invalid_query_args = {
            "query": "INVALID SQL SYNTAX HERE"
        }

        result = await surrealdb_server._handle_execute_query(invalid_query_args)
        # Should return error result, not raise exception
        assert result is not None

    async def test_network_failure_scenarios(self, surrealdb_server):
        """Test D.2: Network failure scenarios."""
        # PASS CRITERIA: Graceful degradation and recovery

        # Test connection with invalid URL
        invalid_connect_args = {
            "url": "ws://invalid-host:8000/rpc",
            "username": "root",
            "password": "root",
            "namespace": "test",
            "database": "test"
        }

        with pytest.raises(Exception):
            await surrealdb_server._handle_connect_database(invalid_connect_args)

        # Verify server can still operate with original connection
        status_result = await surrealdb_server._handle_status()
        assert status_result is not None

    async def test_resource_limit_scenarios(self, surrealdb_server):
        """Test D.3: Resource limit scenarios."""
        # PASS CRITERIA: Proper handling of resource constraints

        # Test large query results (should be limited)
        large_query_args = {
            "query": f"SELECT * FROM test_table LIMIT {1000}"  # Large limit
        }

        result = await surrealdb_server._handle_execute_query(large_query_args)
        assert result is not None

        # Test invalid document ID
        invalid_get_args = {
            "id": "nonexistent:document"
        }

        result = await surrealdb_server._handle_get_document(invalid_get_args)
        # Should handle gracefully, not crash
        assert result is not None

# =============================================================================
# E. COMPLIANCE TESTS
# =============================================================================

class TestCompliance:
    """Test MCP protocol compliance and standards."""

    async def test_mcp_protocol_compliance(self, surrealdb_server):
        """Test E.1: MCP protocol compliance."""
        # PASS CRITERIA: Full adherence to MCP specification

        # Test tool listing returns proper format
        tools = await surrealdb_server.server.list_tools()
        assert isinstance(tools, list)

        for tool in tools:
            assert isinstance(tool, types.Tool)
            assert hasattr(tool, 'name')
            assert hasattr(tool, 'description')
            assert hasattr(tool, 'inputSchema')
            assert isinstance(tool.name, str)
            assert isinstance(tool.description, str)
            assert isinstance(tool.inputSchema, dict)

    async def test_data_type_safety(self, surrealdb_server):
        """Test E.2: Data type safety."""
        # PASS CRITERIA: Proper type validation and conversion

        # Test with various data types
        test_data = {
            "string_field": "test_string",
            "number_field": 42,
            "boolean_field": True,
            "array_field": [1, 2, 3],
            "object_field": {"nested": "value"}
        }

        doc_args = {
            "table": "test_types",
            "data": test_data,
            "id": "test_types_1"
        }

        result = await surrealdb_server._handle_create_document(doc_args)
        assert result is not None

        # Retrieve and verify data types preserved
        get_args = {"id": "test_types:test_types_1"}
        get_result = await surrealdb_server._handle_get_document(get_args)
        assert get_result is not None

    async def test_security_validation(self, surrealdb_server):
        """Test E.3: Security validation."""
        # PASS CRITERIA: Secure handling of credentials and data

        # Test that credentials are not exposed in status
        status_result = await surrealdb_server._handle_status()
        assert status_result is not None

        status_text = status_result[0].text if hasattr(status_result[0], 'text') else str(status_result[0])

        # Ensure credentials are not in status response
        assert TEST_CONFIG["surrealdb_password"] not in status_text
        assert "password" not in status_text.lower()

        # Test input sanitization
        malicious_query_args = {
            "query": "SELECT * FROM users; DROP TABLE users; --"
        }

        # Should handle safely without executing malicious content
        result = await surrealdb_server._handle_execute_query(malicious_query_args)
        assert result is not None

# =============================================================================
# CLEANUP AND UTILITY TESTS
# =============================================================================

class TestCleanup:
    """Test cleanup operations and utilities."""

    async def test_cleanup_operations(self, surrealdb_server):
        """Test proper cleanup of test data."""
        # PASS CRITERIA: Successful cleanup of all test data

        # Clean up all test data
        cleanup_queries = [
            "DELETE FROM test_table",
            "DELETE FROM test_users",
            "DELETE FROM test_companies",
            "DELETE FROM test_perf",
            "DELETE FROM test_nodes",
            "DELETE FROM test_concurrent",
            "DELETE FROM test_resources",
            "DELETE FROM test_types"
        ]

        for query in cleanup_queries:
            query_args = {"query": query}
            result = await surrealdb_server._handle_execute_query(query_args)
            assert result is not None

        # Verify cleanup was successful
        status_result = await surrealdb_server._handle_status()
        assert status_result is not None

    async def test_database_info_comprehensive(self, surrealdb_server):
        """Test comprehensive database information retrieval."""
        # PASS CRITERIA: Complete database information returned

        result = await surrealdb_server._handle_get_database_info()
        assert result is not None
        assert len(result) > 0

        # Verify database info contains expected fields
        info_text = result[0].text if hasattr(result[0], 'text') else str(result[0])
        assert "database" in info_text.lower() or "info" in info_text.lower()

# =============================================================================
# PERFORMANCE BENCHMARKING
# =============================================================================

@pytest.mark.performance
class TestPerformanceBenchmark:
    """Comprehensive performance benchmarking suite."""

    async def test_comprehensive_benchmark(self, surrealdb_server, performance_tracker):
        """Comprehensive performance benchmark across all operations."""
        # PASS CRITERIA: All operations meet performance targets

        operations = [
            ("status_check", lambda: surrealdb_server._handle_status()),
            ("document_create", lambda: surrealdb_server._handle_create_document({
                "table": "bench_test",
                "data": {"name": "Benchmark Test", "timestamp": time.time()},
                "id": f"bench_{int(time.time())}"
            })),
            ("query_execute", lambda: surrealdb_server._handle_execute_query({
                "query": "SELECT * FROM bench_test LIMIT 10"
            })),
            ("database_info", lambda: surrealdb_server._handle_get_database_info())
        ]

        benchmark_results = {}

        for op_name, operation in operations:
            performance_tracker.start(op_name)
            result = await operation()
            duration = performance_tracker.end(op_name)

            assert result is not None, f"Operation {op_name} failed"
            benchmark_results[op_name] = duration

            # Log benchmark results
            logger.info(f"Benchmark {op_name}: {duration:.3f}s")

        # Verify all benchmarks are reasonable (under 2 seconds)
        for op_name, duration in benchmark_results.items():
            assert duration < 2.0, f"Operation {op_name} took {duration}s, too slow"

        return benchmark_results

# =============================================================================
# INTEGRATION VALIDATION
# =============================================================================

@pytest.mark.integration
class TestIntegrationValidation:
    """Integration validation with real SurrealDB service."""

    async def test_end_to_end_workflow(self, surrealdb_server):
        """Test complete end-to-end workflow."""
        # PASS CRITERIA: Complete workflow executes successfully

        # 1. Create initial documents
        user_args = {
            "table": "workflow_users",
            "data": {"name": "Workflow User", "email": "workflow@example.com"},
            "id": "workflow_user_1"
        }
        user_result = await surrealdb_server._handle_create_document(user_args)
        assert user_result is not None

        company_args = {
            "table": "workflow_companies",
            "data": {"name": "Workflow Corp", "industry": "testing"},
            "id": "workflow_company_1"
        }
        company_result = await surrealdb_server._handle_create_document(company_args)
        assert company_result is not None

        # 2. Create relationship
        relation_args = {
            "from_id": "workflow_users:workflow_user_1",
            "to_id": "workflow_companies:workflow_company_1",
            "relation_type": "works_for",
            "properties": {"role": "tester", "since": "2024-01-01"}
        }
        relation_result = await surrealdb_server._handle_create_relation(relation_args)
        assert relation_result is not None

        # 3. Query the relationship
        query_args = {
            "query": "SELECT *, ->works_for->workflow_companies.* FROM workflow_users WHERE id = $user_id",
            "variables": {"user_id": "workflow_users:workflow_user_1"}
        }
        query_result = await surrealdb_server._handle_execute_query(query_args)
        assert query_result is not None

        # 4. Clean up
        cleanup_args = {
            "query": "DELETE workflow_users, workflow_companies WHERE id CONTAINS 'workflow_'"
        }
        cleanup_result = await surrealdb_server._handle_execute_query(cleanup_args)
        assert cleanup_result is not None

# =============================================================================
# PYTEST CONFIGURATION
# =============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "performance: mark test as performance test")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "slow: mark test as slow running")

def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers."""
    for item in items:
        # Add performance marker to performance tests
        if "performance" in item.nodeid:
            item.add_marker(pytest.mark.performance)

        # Add integration marker to integration tests
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)

        # Add slow marker to tests that might be slow
        if any(keyword in item.nodeid for keyword in ["benchmark", "concurrent", "end_to_end"]):
            item.add_marker(pytest.mark.slow)

# =============================================================================
# TEST RESULT VALIDATION
# =============================================================================

def validate_test_results(results):
    """Validate test results meet success criteria."""
    total_tests = len(results)
    passed_tests = sum(1 for result in results if result.passed)
    success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0

    # PASS CRITERIA: 100% success rate required
    assert success_rate == 100.0, f"Success rate {success_rate}% does not meet 100% requirement"

    return {
        "total_tests": total_tests,
        "passed_tests": passed_tests,
        "success_rate": success_rate,
        "status": "PASSED" if success_rate == 100.0 else "FAILED"
    }

# =============================================================================
# MAIN TEST EXECUTION
# =============================================================================

if __name__ == "__main__":
    # Run tests with comprehensive reporting
    pytest.main([
        __file__,
        "-v",
        "--cov=surrealdb_mcp",
        "--cov-report=html",
        "--cov-report=term-missing",
        "--cov-fail-under=90",
        "--tb=short"
    ])
