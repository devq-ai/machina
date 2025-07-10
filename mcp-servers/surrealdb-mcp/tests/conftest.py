#!/usr/bin/env python3
"""
Pytest Configuration and Fixtures for SurrealDB MCP Server Tests

This file provides comprehensive test fixtures and configuration for the SurrealDB MCP server
test suite, following DevQ.ai testing standards with 100% success rate requirements.

Features:
- Real SurrealDB service integration
- Performance tracking and validation
- Test data management and cleanup
- Environment validation
- Mock services for offline testing
"""

import asyncio
import json
import logging
import os
import sys
import time
import pytest
from pathlib import Path
from typing import Dict, List, Any, Optional, Generator
from unittest.mock import AsyncMock, MagicMock, patch
import subprocess
import signal

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
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test configuration constants
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
    },
    "test_timeout": 30,              # 30 seconds per test
    "cleanup_timeout": 5,            # 5 seconds for cleanup
    "max_retries": 3,                # Maximum retry attempts
    "retry_delay": 1.0               # Delay between retries
}

# Global test state
_surrealdb_process = None
_test_session_id = None

class PerformanceTracker:
    """Track performance metrics for tests."""

    def __init__(self):
        self.metrics = {}
        self.start_times = {}
        self.thresholds = TEST_CONFIG["performance_targets"]

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

    def validate_performance(self, operation: str, duration: float) -> bool:
        """Validate performance against targets."""
        threshold = self.thresholds.get(operation, 1.0)
        return duration <= threshold

    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report."""
        report = {
            "metrics": self.metrics,
            "thresholds": self.thresholds,
            "analysis": {}
        }

        for operation, duration in self.metrics.items():
            threshold = self.thresholds.get(operation, 1.0)
            report["analysis"][operation] = {
                "duration": duration,
                "threshold": threshold,
                "status": "PASS" if duration <= threshold else "FAIL",
                "margin": threshold - duration
            }

        return report

class TestDataManager:
    """Manage test data lifecycle."""

    def __init__(self, server: SurrealDBServer):
        self.server = server
        self.created_data = []
        self.test_tables = set()

    async def create_test_document(self, table: str, data: Dict[str, Any], doc_id: str = None) -> str:
        """Create a test document and track it for cleanup."""
        if doc_id is None:
            doc_id = f"test_{int(time.time() * 1000)}"

        full_id = f"{table}:{doc_id}"

        args = {
            "table": table,
            "data": data,
            "id": doc_id
        }

        result = await self.server._handle_create_document(args)

        if result:
            self.created_data.append(full_id)
            self.test_tables.add(table)

        return full_id

    async def create_test_relation(self, from_id: str, to_id: str, relation_type: str,
                                 properties: Dict[str, Any] = None) -> str:
        """Create a test relationship and track it for cleanup."""
        args = {
            "from_id": from_id,
            "to_id": to_id,
            "relation_type": relation_type,
            "properties": properties or {}
        }

        result = await self.server._handle_create_relation(args)

        if result:
            relation_id = f"{relation_type}:{from_id.split(':')[1]}_{to_id.split(':')[1]}"
            self.created_data.append(relation_id)

        return relation_id

    async def cleanup_test_data(self):
        """Clean up all test data."""
        try:
            # Clean up specific test tables
            cleanup_queries = []
            for table in self.test_tables:
                cleanup_queries.append(f"DELETE FROM {table} WHERE id CONTAINS 'test_'")

            # Add common test table cleanup
            test_table_patterns = [
                "test_table", "test_users", "test_companies", "test_perf",
                "test_nodes", "test_concurrent", "test_resources", "test_types",
                "workflow_users", "workflow_companies", "bench_test"
            ]

            for pattern in test_table_patterns:
                cleanup_queries.append(f"DELETE FROM {pattern}")

            # Execute cleanup queries
            for query in cleanup_queries:
                try:
                    args = {"query": query}
                    await self.server._handle_execute_query(args)
                except Exception as e:
                    logger.debug(f"Cleanup query failed: {query}, error: {e}")

            logger.info(f"Cleaned up {len(self.created_data)} test records")

        except Exception as e:
            logger.warning(f"Test data cleanup failed: {e}")
        finally:
            self.created_data.clear()
            self.test_tables.clear()

class SurrealDBTestManager:
    """Manage SurrealDB server for tests."""

    @staticmethod
    def check_surrealdb_availability() -> bool:
        """Check if SurrealDB server is running."""
        try:
            result = subprocess.run(
                ["curl", "-s", "http://localhost:8000/status"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    @staticmethod
    def start_surrealdb() -> subprocess.Popen:
        """Start SurrealDB server for testing."""
        try:
            process = subprocess.Popen([
                "surreal", "start",
                "--log", "warn",
                "--user", "root",
                "--pass", "root",
                "memory"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # Wait for server to start
            time.sleep(3)

            if SurrealDBTestManager.check_surrealdb_availability():
                logger.info("SurrealDB server started for tests")
                return process
            else:
                process.terminate()
                raise Exception("SurrealDB server failed to start properly")

        except Exception as e:
            logger.error(f"Failed to start SurrealDB server: {e}")
            raise

    @staticmethod
    def stop_surrealdb(process: subprocess.Popen):
        """Stop SurrealDB server."""
        if process:
            try:
                process.terminate()
                process.wait(timeout=5)
                logger.info("SurrealDB server stopped")
            except subprocess.TimeoutExpired:
                process.kill()
                logger.warning("SurrealDB server forcefully terminated")
            except Exception as e:
                logger.error(f"Error stopping SurrealDB server: {e}")

# =============================================================================
# SESSION FIXTURES
# =============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()

@pytest.fixture(scope="session")
def surrealdb_process():
    """Start SurrealDB server for the test session."""
    global _surrealdb_process

    # Check if SurrealDB is already running
    if not SurrealDBTestManager.check_surrealdb_availability():
        try:
            _surrealdb_process = SurrealDBTestManager.start_surrealdb()
        except Exception as e:
            pytest.skip(f"Could not start SurrealDB server: {e}")

    yield _surrealdb_process

    # Cleanup
    if _surrealdb_process:
        SurrealDBTestManager.stop_surrealdb(_surrealdb_process)

@pytest.fixture(scope="session")
def test_session_id():
    """Generate a unique test session ID."""
    global _test_session_id
    _test_session_id = f"test_session_{int(time.time())}"
    return _test_session_id

# =============================================================================
# FUNCTION FIXTURES
# =============================================================================

@pytest.fixture
def performance_tracker():
    """Provide performance tracking for tests."""
    return PerformanceTracker()

@pytest.fixture
async def surrealdb_server(surrealdb_process):
    """Create and initialize SurrealDB MCP server for testing."""
    server = SurrealDBServer()

    try:
        await server.initialize()
        yield server
    finally:
        # Server cleanup is handled by test data manager
        pass

@pytest.fixture
async def test_data_manager(surrealdb_server):
    """Provide test data management."""
    manager = TestDataManager(surrealdb_server)
    yield manager
    await manager.cleanup_test_data()

@pytest.fixture
def mock_surrealdb():
    """Mock SurrealDB for testing without real database."""
    mock_db = AsyncMock()

    # Configure mock responses
    mock_db.query.return_value = [{"result": "mock_success"}]
    mock_db.create.return_value = {"id": "test:mock_1", "name": "Mock Document"}
    mock_db.select.return_value = {"id": "test:mock_1", "name": "Mock Document"}
    mock_db.update.return_value = {"id": "test:mock_1", "name": "Updated Mock"}
    mock_db.delete.return_value = {"id": "test:mock_1"}
    mock_db.merge.return_value = {"id": "test:mock_1", "name": "Merged Mock"}

    return mock_db

@pytest.fixture
def environment_validator():
    """Validate test environment requirements."""
    def validate():
        missing_vars = []

        required_vars = [
            "SURREALDB_URL",
            "SURREALDB_USERNAME",
            "SURREALDB_PASSWORD"
        ]

        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)

        if missing_vars:
            pytest.skip(f"Missing required environment variables: {missing_vars}")

        return True

    return validate

@pytest.fixture
def test_config():
    """Provide test configuration."""
    return TEST_CONFIG.copy()

# =============================================================================
# PARAMETRIZED FIXTURES
# =============================================================================

@pytest.fixture(params=[
    {"name": "Alice", "role": "developer", "skills": ["Python", "SurrealDB"]},
    {"name": "Bob", "role": "designer", "skills": ["UI/UX", "Figma"]},
    {"name": "Charlie", "role": "manager", "skills": ["Leadership", "Strategy"]}
])
def sample_user_data(request):
    """Provide sample user data for tests."""
    return request.param

@pytest.fixture(params=[
    {"name": "ACME Corp", "industry": "technology", "size": "large"},
    {"name": "StartupXYZ", "industry": "fintech", "size": "small"},
    {"name": "GlobalTech", "industry": "consulting", "size": "medium"}
])
def sample_company_data(request):
    """Provide sample company data for tests."""
    return request.param

@pytest.fixture(params=[
    {"type": "works_at", "properties": {"position": "senior", "department": "engineering"}},
    {"type": "manages", "properties": {"team_size": 5, "since": "2023-01-01"}},
    {"type": "collaborates_with", "properties": {"project": "alpha", "frequency": "daily"}}
])
def sample_relation_data(request):
    """Provide sample relation data for tests."""
    return request.param

# =============================================================================
# UTILITY FIXTURES
# =============================================================================

@pytest.fixture
def retry_helper():
    """Provide retry functionality for flaky operations."""
    async def retry_async(func, max_retries=3, delay=1.0, *args, **kwargs):
        """Retry an async function with exponential backoff."""
        for attempt in range(max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                logger.warning(f"Attempt {attempt + 1} failed: {e}, retrying...")
                await asyncio.sleep(delay * (2 ** attempt))

        raise Exception("Max retries exceeded")

    return retry_async

@pytest.fixture
def timeout_helper():
    """Provide timeout functionality for tests."""
    def timeout_async(timeout_seconds=30):
        """Decorator to add timeout to async functions."""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                try:
                    return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout_seconds)
                except asyncio.TimeoutError:
                    pytest.fail(f"Test timed out after {timeout_seconds} seconds")
            return wrapper
        return decorator

    return timeout_async

# =============================================================================
# PYTEST HOOKS
# =============================================================================

def pytest_configure(config):
    """Configure pytest with custom settings."""
    # Add custom markers
    config.addinivalue_line("markers", "core_functionality: Core MCP functionality tests")
    config.addinivalue_line("markers", "integration: Integration tests with real SurrealDB")
    config.addinivalue_line("markers", "performance: Performance and benchmarking tests")
    config.addinivalue_line("markers", "error_handling: Error handling and recovery tests")
    config.addinivalue_line("markers", "compliance: MCP protocol compliance tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "real_service: Tests requiring real SurrealDB")

def pytest_runtest_setup(item):
    """Set up individual test runs."""
    # Skip tests if environment not properly configured
    if "real_service" in item.keywords:
        if not SurrealDBTestManager.check_surrealdb_availability():
            pytest.skip("Real SurrealDB service not available")

def pytest_runtest_teardown(item, nextitem):
    """Clean up after individual test runs."""
    # Additional cleanup if needed
    pass

def pytest_collection_modifyitems(config, items):
    """Modify collected test items."""
    # Add markers based on test names
    for item in items:
        # Add performance marker to performance tests
        if "performance" in item.nodeid.lower():
            item.add_marker(pytest.mark.performance)

        # Add slow marker to potentially slow tests
        if any(keyword in item.nodeid.lower() for keyword in
               ["benchmark", "concurrent", "end_to_end", "comprehensive"]):
            item.add_marker(pytest.mark.slow)

        # Add real_service marker to integration tests
        if "integration" in item.nodeid.lower() or "real_" in item.nodeid.lower():
            item.add_marker(pytest.mark.real_service)

def pytest_sessionstart(session):
    """Called after the Session object has been created."""
    logger.info("Starting SurrealDB MCP test session")

    # Validate environment
    required_vars = ["SURREALDB_URL", "SURREALDB_USERNAME", "SURREALDB_PASSWORD"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        logger.warning(f"Missing environment variables: {missing_vars}")

def pytest_sessionfinish(session, exitstatus):
    """Called after whole test run finished."""
    logger.info(f"SurrealDB MCP test session finished with exit status: {exitstatus}")

    # Generate final summary
    if hasattr(session, 'testsfailed') and session.testsfailed > 0:
        logger.error(f"Test session completed with {session.testsfailed} failures")
    else:
        logger.info("Test session completed successfully")

# =============================================================================
# CLEANUP HANDLERS
# =============================================================================

def cleanup_on_interrupt(signum, frame):
    """Handle cleanup on interrupt."""
    logger.info("Test interrupted, cleaning up...")
    global _surrealdb_process
    if _surrealdb_process:
        SurrealDBTestManager.stop_surrealdb(_surrealdb_process)
    sys.exit(1)

# Register signal handlers
signal.signal(signal.SIGINT, cleanup_on_interrupt)
signal.signal(signal.SIGTERM, cleanup_on_interrupt)
