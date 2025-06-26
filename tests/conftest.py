"""
Test Configuration and Fixtures for Machina Registry Service

This module provides pytest fixtures and configuration for testing the Machina Registry
Service API endpoints. It implements DevQ.ai's standard testing patterns with database
setup, client configuration, and test data management.

Features:
- Async database session management for tests
- FastAPI test client setup with dependency overrides
- Service registry test fixtures
- Mock service discovery components
- Test data factories and cleanup utilities
"""

import asyncio
import os
import sys
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Generator
from uuid import uuid4

from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import event
from sqlalchemy.engine import Engine

# Add src to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from app.core.database import Base, get_db
from app.core.config import settings
from app.models.domain.registry_item import (
    RegistryItem,
    ServiceBuildType,
    ServiceProtocol,
    ServiceStatus,
    ServicePriority
)
from main import app


# Test Database Configuration
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

# Create test engine with different settings
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,  # Set to True for SQL debugging
    pool_pre_ping=True,
    poolclass=StaticPool,
    connect_args={
        "check_same_thread": False,
    },
)

# Create async session factory for tests
TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Create a test database session for async operations.

    This fixture creates and tears down the database for each test function,
    ensuring clean test isolation.
    """
    # Create all tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async with TestSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

    # Drop all tables after test
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def db_session(event_loop) -> Generator[AsyncSession, None, None]:
    """
    Synchronous wrapper for database session.

    This fixture provides a database session that can be used in synchronous tests.
    """
    async def _get_session():
        # Create all tables
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Create session
        async with TestSessionLocal() as session:
            try:
                yield session
            finally:
                await session.close()

        # Drop all tables after test
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    session_gen = _get_session()
    session = event_loop.run_until_complete(session_gen.__anext__())

    try:
        yield session
    finally:
        try:
            event_loop.run_until_complete(session_gen.__anext__())
        except StopAsyncIteration:
            pass


@pytest.fixture
def client() -> TestClient:
    """
    Create a FastAPI test client with database override.

    This fixture overrides the database dependency to use the test database
    and provides a synchronous client for testing API endpoints.
    """
    def override_get_db():
        """Override database dependency for testing."""
        async def _get_test_db():
            async with TestSessionLocal() as session:
                try:
                    yield session
                except Exception:
                    await session.rollback()
                    raise
                finally:
                    await session.close()

        return _get_test_db()

    # Override the dependency
    app.dependency_overrides[get_db] = override_get_db

    # Create test tables
    async def create_test_tables():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_test_tables():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    # Set up tables
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(create_test_tables())

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        # Clean up
        loop.run_until_complete(drop_test_tables())
        loop.close()
        # Clear dependency overrides
        app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """
    Create an async HTTP client for testing API endpoints.

    This fixture provides an async client that can be used for testing
    async API endpoints with proper database session management.
    """
    async def override_get_db():
        """Override database dependency for async testing."""
        async with TestSessionLocal() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    # Override the dependency
    app.dependency_overrides[get_db] = override_get_db

    # Create test tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    try:
        async with AsyncClient(app=app, base_url="http://test") as async_client:
            yield async_client
    finally:
        # Clean up
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        # Clear dependency overrides
        app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_db_service(async_db: AsyncSession) -> RegistryItem:
    """
    Create a test service in the database for use in tests.

    This fixture creates a standard test service that can be used across
    multiple test functions for consistent testing scenarios.
    """
    service = RegistryItem(
        name="test-service",
        display_name="Test Service",
        description="A test service for API testing",
        build_type=ServiceBuildType.FASTMCP,
        protocol=ServiceProtocol.STDIO,
        priority=ServicePriority.MEDIUM,
        location="/test/services/test-service",
        endpoint="http://localhost:8080",
        port=8080,
        version="1.0.0",
        tags=["test", "api"],
        status=ServiceStatus.HEALTHY,
        is_required=False,
        is_enabled=True,
        auto_start=False,
        dependencies=[],
        dependents=[],
        service_metadata={"framework": "fastapi", "language": "python"},
        config={"timeout": 30, "retries": 3},
        health_check_url="http://localhost:8080/health",
        source="test",
        created_by="test_user",
        updated_by="test_user",
        success_count=10,
        failure_count=1
    )

    async_db.add(service)
    await async_db.commit()
    await async_db.refresh(service)

    return service


@pytest.fixture
def sample_service_data() -> dict:
    """
    Provide sample service data for testing.

    This fixture returns a dictionary with valid service data that can be
    used for creating test services via the API.
    """
    return {
        "name": "sample-test-service",
        "display_name": "Sample Test Service",
        "description": "A sample service for testing purposes",
        "build_type": "fastmcp",
        "protocol": "stdio",
        "priority": "medium",
        "location": "/test/services/sample",
        "endpoint": "http://localhost:9000",
        "port": 9000,
        "version": "1.0.0",
        "tags": ["sample", "test"],
        "is_required": False,
        "is_enabled": True,
        "auto_start": False,
        "dependencies": [],
        "service_metadata": {
            "framework": "fastapi",
            "language": "python",
            "environment": "test"
        },
        "config": {
            "timeout": 30,
            "retries": 3,
            "debug": True
        },
        "health_check_url": "http://localhost:9000/health"
    }


@pytest.fixture
def multiple_service_data() -> list:
    """
    Provide multiple service data entries for bulk testing.

    This fixture returns a list of service data dictionaries for testing
    scenarios that require multiple services.
    """
    services = []
    for i in range(5):
        services.append({
            "name": f"bulk-test-service-{i}",
            "display_name": f"Bulk Test Service {i}",
            "description": f"Bulk test service number {i}",
            "build_type": "fastmcp",
            "protocol": "stdio",
            "priority": ["low", "medium", "high"][i % 3],
            "location": f"/test/services/bulk-{i}",
            "port": 8000 + i,
            "version": "1.0.0",
            "tags": ["bulk", "test", f"service-{i}"],
            "is_required": i % 2 == 0,
            "is_enabled": True,
            "auto_start": False,
            "dependencies": [],
            "service_metadata": {"index": i, "batch": "bulk-test"},
            "config": {"timeout": 30 + (i * 5)},
            "health_check_url": f"http://localhost:{8000 + i}/health"
        })
    return services


@pytest_asyncio.fixture
async def populated_db(async_db: AsyncSession, multiple_service_data: list) -> list:
    """
    Create a database populated with multiple test services.

    This fixture creates several test services in the database for testing
    scenarios that require existing data.
    """
    services = []
    for service_data in multiple_service_data:
        service = RegistryItem(
            name=service_data["name"],
            display_name=service_data["display_name"],
            description=service_data["description"],
            build_type=ServiceBuildType(service_data["build_type"]),
            protocol=ServiceProtocol(service_data["protocol"]),
            priority=ServicePriority(service_data["priority"]),
            location=service_data["location"],
            port=service_data["port"],
            version=service_data["version"],
            tags=service_data["tags"],
            is_required=service_data["is_required"],
            is_enabled=service_data["is_enabled"],
            auto_start=service_data["auto_start"],
            dependencies=service_data["dependencies"],
            service_metadata=service_data["service_metadata"],
            config=service_data["config"],
            health_check_url=service_data["health_check_url"],
            status=ServiceStatus.HEALTHY,
            source="test",
            created_by="test_user",
            updated_by="test_user"
        )
        async_db.add(service)
        services.append(service)

    await async_db.commit()

    # Refresh all services to get their IDs
    for service in services:
        await async_db.refresh(service)

    return services


@pytest.fixture
def mock_discovery_orchestrator():
    """
    Provide a mock discovery orchestrator for testing.

    This fixture returns a mock discovery orchestrator that can be used
    to test discovery-related functionality without actual service discovery.
    """
    from unittest.mock import AsyncMock, Mock

    mock_orchestrator = AsyncMock()

    # Mock discovered service info
    mock_service_info = Mock()
    mock_service_info.name = "discovered-service"
    mock_service_info.type = "mcp"
    mock_service_info.location = "/discovered/service"
    mock_service_info.source = "local"
    mock_service_info.metadata = {"discovered": True}

    mock_orchestrator.discover_all_services.return_value = [mock_service_info]
    mock_orchestrator.get_discovery_stats.return_value = {
        "total_discovered": 1,
        "successful": 1,
        "failed": 0
    }

    return mock_orchestrator


@pytest.fixture
def mock_health_probe():
    """
    Provide a mock health probe for testing health check functionality.

    This fixture returns a mock health probe that can be configured to
    return different health check results for testing purposes.
    """
    from unittest.mock import AsyncMock

    mock_probe = AsyncMock()
    mock_probe.check_health.return_value = {
        "status": "healthy",
        "response_time_ms": 150,
        "metadata": {
            "http_status": 200,
            "timestamp": "2023-12-01T10:00:00Z"
        }
    }

    return mock_probe


@pytest.fixture(autouse=True)
def clean_test_environment():
    """
    Automatically clean the test environment before and after each test.

    This fixture ensures that each test starts with a clean environment
    and cleans up after itself to prevent test interference.
    """
    # Pre-test cleanup
    if os.path.exists("./test.db"):
        os.remove("./test.db")

    yield

    # Post-test cleanup
    if os.path.exists("./test.db"):
        os.remove("./test.db")


# Configure pytest settings
pytest_plugins = [
    "pytest_asyncio",
]

# Mark all async functions as async tests
pytestmark = pytest.mark.asyncio


def pytest_configure(config):
    """Configure pytest with custom settings."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically."""
    for item in items:
        # Mark tests in test_api directories as integration tests
        if "test_api" in str(item.fspath):
            item.add_marker(pytest.mark.integration)

        # Mark async tests
        if asyncio.iscoroutinefunction(item.function):
            item.add_marker(pytest.mark.asyncio)


# Helper utilities for tests

def create_test_service_data(**overrides) -> dict:
    """
    Create test service data with optional overrides.

    Args:
        **overrides: Fields to override in the default service data

    Returns:
        Dictionary with service data suitable for API requests
    """
    base_data = {
        "name": f"test-service-{uuid4().hex[:8]}",
        "display_name": "Test Service",
        "description": "A test service",
        "build_type": "fastmcp",
        "protocol": "stdio",
        "priority": "medium",
        "location": "/test/service",
        "port": 8080,
        "version": "1.0.0",
        "tags": ["test"],
        "is_required": False,
        "is_enabled": True,
        "auto_start": False,
        "dependencies": [],
        "service_metadata": {},
        "config": {},
        "health_check_url": "http://localhost:8080/health"
    }

    base_data.update(overrides)
    return base_data


async def create_test_service_in_db(db: AsyncSession, **overrides) -> RegistryItem:
    """
    Create a test service directly in the database.

    Args:
        db: Database session
        **overrides: Fields to override in the default service

    Returns:
        Created RegistryItem instance
    """
    service_data = create_test_service_data(**overrides)

    service = RegistryItem(
        name=service_data["name"],
        display_name=service_data["display_name"],
        description=service_data["description"],
        build_type=ServiceBuildType(service_data["build_type"]),
        protocol=ServiceProtocol(service_data["protocol"]),
        priority=ServicePriority(service_data["priority"]),
        location=service_data["location"],
        port=service_data["port"],
        version=service_data["version"],
        tags=service_data["tags"],
        is_required=service_data["is_required"],
        is_enabled=service_data["is_enabled"],
        auto_start=service_data["auto_start"],
        dependencies=service_data["dependencies"],
        service_metadata=service_data["service_metadata"],
        config=service_data["config"],
        health_check_url=service_data["health_check_url"],
        status=ServiceStatus.HEALTHY,
        source="test",
        created_by="test_user",
        updated_by="test_user"
    )

    db.add(service)
    await db.commit()
    await db.refresh(service)

    return service
