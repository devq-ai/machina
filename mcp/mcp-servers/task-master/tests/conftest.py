# machina/mcp/mcp-servers/task-master/tests/conftest.py

import pytest
import asyncio
from fastmcp import MCPServer
from unittest.mock import AsyncMock

# Mocking the MCPServer for testing purposes if needed, or direct instantiation.
# For now, we'll focus on testing the TaskMasterServer directly.

# Fixture for the TaskMasterServer instance
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def task_master_server():
    """Provides an instance of TaskMasterServer for testing."""
    # Initialize the server
    server = TaskMasterServer()
    # If the server had async initialization steps, they would be called here
    # For example: await server.initialize()

    # Yield the server instance
    yield server

    # Clean up after tests if necessary
    # For in-memory storage, cleanup is implicit as it's reset with each test run or module load.
    # If using persistent storage, cleanup would be more involved.
    pass # No explicit cleanup needed for in-memory storage in this scope


# Helper fixture to mock logging if needed, though direct print statements are used now.
@pytest.fixture
async def mock_log_event(monkeypatch):
    """Mocks the log_event method to check logging calls."""
    mock_log = AsyncMock()
    monkeypatch.setattr(TaskMasterServer, 'log_event', mock_log)
    return mock_log
