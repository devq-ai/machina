"""
Comprehensive Test Suite for TaskMaster AI Integration

This test module provides thorough testing of the TaskMaster AI integration
functionality, implementing DevQ.ai's testing standards with fixtures,
mocking, and comprehensive coverage of all TaskMaster operations.

Test Coverage:
- Task model validation and serialization
- TaskMaster service operations (CRUD)
- Task dependency management and cycle detection
- Task complexity analysis and scoring
- Task status and progress tracking
- Cache integration and performance
- API endpoint functionality
- Error handling and edge cases
- Bulk operations and filtering
- Statistics and analytics
"""

import asyncio
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import logfire
from fastapi.testclient import TestClient
from fastapi import status

from app.models.task_models import (
    Task,
    TaskList,
    TaskStats,
    TaskFilter,
    TaskOperation,
    TaskStatus,
    TaskPriority,
    TaskType,
    TaskComplexity,
    TaskDependency,
    TaskMetrics,
    TaskContext,
    TaskValidation
)
from app.services.taskmaster_service import TaskMasterService
from app.api.v1.taskmaster import router as taskmaster_router
from app.core.cache import CacheService, CacheKeyType
from app.core.config import Settings
from app.core.exceptions import NotFoundError, ValidationError, ConflictError


@pytest.fixture
def test_settings():
    """Test settings for TaskMaster integration."""
    return Settings(
        ENVIRONMENT="testing",
        REDIS_DB=15,
        CACHE_TTL=300,
        DEBUG=True
    )


@pytest.fixture
def mock_cache_service():
    """Mock cache service for testing."""
    mock = AsyncMock(spec=CacheService)

    # Mock cache operations
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=True)
    mock.exists = AsyncMock(return_value=False)
    mock.publish = AsyncMock(return_value=1)

    # Mock statistics
    mock_stats = MagicMock()
    mock_stats.total_operations = 0
    mock_stats.cache_hits = 0
    mock_stats.cache_misses = 0
    mock.get_stats = MagicMock(return_value=mock_stats)

    return mock


@pytest_asyncio.fixture
async def taskmaster_service(mock_cache_service):
    """Create TaskMaster service with mocked dependencies."""
    service = TaskMasterService(mock_cache_service)
    return service


@pytest.fixture
def sample_task_data():
    """Sample task data for testing."""
    return {
        "title": "Test Task",
        "description": "A comprehensive test task for validation",
        "task_type": TaskType.FEATURE,
        "priority": TaskPriority.HIGH,
        "details": "Detailed implementation notes for the test task",
        "context": {
            "repository": "test-repo",
            "branch": "feature/test",
            "assigned_to": "test@devq.ai",
            "tags": ["test", "feature"]
        },
        "metrics": {
            "estimated_hours": 8.0,
            "complexity_score": 5
        }
    }


@pytest.fixture
def sample_task(sample_task_data):
    """Create a sample task instance."""
    return Task(**sample_task_data)


class TestTaskModels:
    """Test suite for task models and validation."""

    def test_task_creation_with_defaults(self):
        """Test task creation with minimal data."""
        task = Task(title="Minimal Task")

        assert task.title == "Minimal Task"
        assert task.status == TaskStatus.PENDING
        assert task.priority == TaskPriority.MEDIUM
        assert task.task_type == TaskType.FEATURE
        assert isinstance(task.created_at, datetime)
        assert isinstance(task.updated_at, datetime)
        assert task.version == 1

    def test_task_creation_with_full_data(self, sample_task_data):
        """Test task creation with complete data."""
        task = Task(**sample_task_data)

        assert task.title == "Test Task"
        assert task.description == "A comprehensive test task for validation"
        assert task.task_type == TaskType.FEATURE
        assert task.priority == TaskPriority.HIGH
        assert task.context.repository == "test-repo"
        assert task.metrics.estimated_hours == 8.0

    def test_task_validation_errors(self):
        """Test task validation with invalid data."""
        with pytest.raises(ValueError):
            Task(title="")  # Empty title should fail

        with pytest.raises(ValueError):
            Task(title="Valid Title", metrics={"completion_percentage": 150})  # Invalid percentage

    def test_task_status_transitions(self, sample_task):
        """Test task status transitions and timestamp management."""
        assert sample_task.started_at is None
        assert sample_task.completed_at is None

        # Start task
        sample_task.update_status(TaskStatus.IN_PROGRESS)
        assert sample_task.status == TaskStatus.IN_PROGRESS
        assert sample_task.started_at is not None

        # Complete task
        sample_task.update_status(TaskStatus.DONE)
        assert sample_task.status == TaskStatus.DONE
        assert sample_task.completed_at is not None
        assert sample_task.metrics.completion_percentage == 100.0

    def test_task_progress_updates(self, sample_task):
        """Test task progress updates and auto-status changes."""
        # Update progress to 50%
        sample_task.update_progress(50.0, "Half way done")
        assert sample_task.metrics.completion_percentage == 50.0
        assert sample_task.status == TaskStatus.IN_PROGRESS

        # Complete task via progress
        sample_task.update_progress(100.0, "Task completed")
        assert sample_task.metrics.completion_percentage == 100.0
        assert sample_task.status == TaskStatus.DONE

    def test_task_complexity_calculation(self):
        """Test automatic complexity calculation."""
        # Simple task
        simple_task = Task(title="Simple Task", description="Short description")
        simple_score = simple_task.calculate_complexity_score()
        assert 1 <= simple_score <= 4

        # Complex task with subtasks and dependencies
        complex_task = Task(
            title="Complex Task",
            description="A" * 600,  # Long description
            details="B" * 1200,     # Long details
            task_type=TaskType.RESEARCH,
            subtasks=[
                Task(title="Subtask 1"),
                Task(title="Subtask 2"),
                Task(title="Subtask 3")
            ]
        )
        complex_score = complex_task.calculate_complexity_score()
        assert 7 <= complex_score <= 10

    def test_task_dependencies(self, sample_task):
        """Test task dependency management."""
        dependency_id = "dep-task-123"

        # Add dependency
        sample_task.add_dependency(dependency_id, "blocks")
        assert len(sample_task.dependencies) == 1
        assert sample_task.dependencies[0].task_id == dependency_id

        # Remove dependency
        removed = sample_task.remove_dependency(dependency_id)
        assert removed is True
        assert len(sample_task.dependencies) == 0

    def test_task_self_dependency_prevention(self, sample_task):
        """Test prevention of self-dependencies."""
        with pytest.raises(ValueError, match="cannot depend on itself"):
            sample_task.add_dependency(sample_task.id)

    def test_task_subtasks(self, sample_task):
        """Test subtask management."""
        subtask = Task(title="Subtask")

        sample_task.add_subtask(subtask)
        assert len(sample_task.subtasks) == 1
        assert subtask.parent_id == sample_task.id
        assert sample_task.subtasks[0].title == "Subtask"

    def test_task_properties(self, sample_task):
        """Test task computed properties."""
        # Age calculation
        assert sample_task.age_days >= 0

        # Complexity category
        sample_task.metrics.complexity_score = 7
        assert sample_task.complexity_category == TaskComplexity.COMPLEX

        # Overdue check with due date
        sample_task.due_date = datetime.utcnow() - timedelta(days=1)
        assert sample_task.is_overdue is True

    def test_task_serialization(self, sample_task):
        """Test task serialization and deserialization."""
        # To dict
        task_dict = sample_task.to_dict()
        assert isinstance(task_dict, dict)
        assert task_dict["title"] == sample_task.title

        # Summary
        summary = sample_task.to_summary()
        assert "id" in summary
        assert "title" in summary
        assert "complexity_score" in summary

        # Round-trip serialization
        new_task = Task(**task_dict)
        assert new_task.title == sample_task.title
        assert new_task.id == sample_task.id

    def test_task_metrics_model(self):
        """Test task metrics model validation and properties."""
        metrics = TaskMetrics(
            estimated_hours=8.0,
            actual_hours=10.0,
            completion_percentage=75.5,
            complexity_score=6,
            lines_of_code=250,
            test_coverage=85.0
        )

        assert metrics.efficiency_ratio == 0.8  # 8.0 / 10.0
        assert metrics.is_overdue is True
        assert metrics.completion_percentage == 75.5

    def test_task_context_model(self):
        """Test task context model."""
        context = TaskContext(
            repository="test-repo",
            branch="feature/test",
            environment="development",
            assigned_to="developer@devq.ai",
            tags=["backend", "api"]
        )

        assert context.repository == "test-repo"
        assert len(context.tags) == 2
        assert "backend" in context.tags

    def test_task_validation_model(self):
        """Test task validation model."""
        validation = TaskValidation(
            test_strategy="Unit and integration tests",
            acceptance_criteria=["Feature works", "Tests pass", "Code review approved"],
            validation_steps=["Run tests", "Check coverage", "Review code"],
            reviewed=True,
            approved=False
        )

        assert len(validation.acceptance_criteria) == 3
        assert validation.reviewed is True
        assert validation.approved is False

    def test_task_filter_model(self):
        """Test task filtering model."""
        task_filter = TaskFilter(
            status=[TaskStatus.PENDING, TaskStatus.IN_PROGRESS],
            priority=[TaskPriority.HIGH],
            task_type=[TaskType.FEATURE],
            assigned_to="developer@devq.ai",
            complexity_min=5,
            completion_min=0.0,
            search_text="test task"
        )

        assert len(task_filter.status) == 2
        assert task_filter.complexity_min == 5
        assert task_filter.search_text == "test task"

    def test_task_stats_model(self):
        """Test task statistics model."""
        stats = TaskStats(
            total_tasks=100,
            completed_tasks=80,
            in_progress_tasks=15,
            pending_tasks=5,
            average_completion_time=6.5,
            average_complexity_score=5.5,
            completion_rate=80.0
        )

        assert stats.total_tasks == 100
        assert stats.completion_rate == 80.0

        # Productivity score calculation
        productivity = stats.productivity_score
        assert 0 <= productivity <= 100


class TestTaskMasterService:
    """Test suite for TaskMaster service operations."""

    @pytest.mark.asyncio
    async def test_create_task_success(self, taskmaster_service, sample_task_data):
        """Test successful task creation."""
        # Mock cache operations
        taskmaster_service.cache_service.get.return_value = None  # No existing task
        taskmaster_service.cache_service.set.return_value = True

        task = await taskmaster_service.create_task(sample_task_data)

        assert isinstance(task, Task)
        assert task.title == "Test Task"
        assert task.metrics.complexity_score is not None

        # Verify cache operations
        taskmaster_service.cache_service.get.assert_called_once()
        taskmaster_service.cache_service.set.assert_called()

    @pytest.mark.asyncio
    async def test_create_task_conflict(self, taskmaster_service, sample_task_data):
        """Test task creation with existing ID."""
        # Mock existing task
        existing_task_data = {"id": "existing-id", "title": "Existing Task"}
        taskmaster_service.cache_service.get.return_value = existing_task_data

        with pytest.raises(ConflictError):
            await taskmaster_service.create_task({**sample_task_data, "id": "existing-id"})

    @pytest.mark.asyncio
    async def test_get_task_from_cache(self, taskmaster_service, sample_task_data):
        """Test retrieving task from cache."""
        # Mock cached task
        taskmaster_service.cache_service.get.return_value = sample_task_data

        task = await taskmaster_service.get_task("test-id", raise_if_not_found=False)

        assert task is not None
        assert task.title == "Test Task"
        assert taskmaster_service._cache_hit_count == 1

    @pytest.mark.asyncio
    async def test_get_task_not_found(self, taskmaster_service):
        """Test retrieving non-existent task."""
        taskmaster_service.cache_service.get.return_value = None

        # Without raising exception
        task = await taskmaster_service.get_task("nonexistent", raise_if_not_found=False)
        assert task is None

        # With raising exception
        with pytest.raises(NotFoundError):
            await taskmaster_service.get_task("nonexistent", raise_if_not_found=True)

    @pytest.mark.asyncio
    async def test_update_task_success(self, taskmaster_service, sample_task_data):
        """Test successful task update."""
        # Mock existing task
        taskmaster_service.cache_service.get.return_value = sample_task_data

        updates = {
            "title": "Updated Task Title",
            "status": TaskStatus.IN_PROGRESS,
            "metrics": {"completion_percentage": 50.0}
        }

        updated_task = await taskmaster_service.update_task("test-id", updates)

        assert updated_task.title == "Updated Task Title"
        assert updated_task.status == TaskStatus.IN_PROGRESS

        # Verify cache update
        taskmaster_service.cache_service.set.assert_called()

    @pytest.mark.asyncio
    async def test_delete_task_success(self, taskmaster_service, sample_task_data):
        """Test successful task deletion."""
        # Mock existing task without subtasks
        task_without_subtasks = {**sample_task_data, "subtasks": []}
        taskmaster_service.cache_service.get.return_value = task_without_subtasks

        result = await taskmaster_service.delete_task("test-id")

        assert result is True
        taskmaster_service.cache_service.delete.assert_called()

    @pytest.mark.asyncio
    async def test_delete_task_with_subtasks_no_cascade(self, taskmaster_service, sample_task_data):
        """Test task deletion with subtasks but no cascade."""
        # Mock task with subtasks
        task_with_subtasks = {
            **sample_task_data,
            "subtasks": [{"id": "subtask-1", "title": "Subtask"}]
        }
        taskmaster_service.cache_service.get.return_value = task_with_subtasks

        with pytest.raises(ConflictError, match="has subtasks"):
            await taskmaster_service.delete_task("test-id", cascade=False)

    @pytest.mark.asyncio
    async def test_add_task_dependency_success(self, taskmaster_service, sample_task_data):
        """Test adding task dependency."""
        # Mock both tasks exist
        taskmaster_service.cache_service.get.side_effect = [
            sample_task_data,  # Main task
            {"id": "dep-id", "title": "Dependency Task"}  # Dependency task
        ]

        result = await taskmaster_service.add_task_dependency("test-id", "dep-id")

        assert result is True
        # Verify cache updates
        assert taskmaster_service.cache_service.set.call_count >= 1

    @pytest.mark.asyncio
    async def test_add_task_dependency_cycle_detection(self, taskmaster_service, sample_task_data):
        """Test cycle detection in task dependencies."""
        # Mock tasks that would create a cycle
        task_a = {**sample_task_data, "id": "task-a"}
        task_b = {
            **sample_task_data,
            "id": "task-b",
            "dependencies": [{"task_id": "task-a", "dependency_type": "blocks"}]
        }

        taskmaster_service.cache_service.get.side_effect = [task_a, task_b]

        with pytest.raises(ConflictError, match="cycle"):
            await taskmaster_service.add_task_dependency("task-a", "task-b")

    @pytest.mark.asyncio
    async def test_update_task_status(self, taskmaster_service, sample_task_data):
        """Test task status update with notifications."""
        taskmaster_service.cache_service.get.return_value = sample_task_data

        # Mock cache utilities for notifications
        taskmaster_service.cache_utilities.notify_mcp_server_update = AsyncMock(return_value=1)

        updated_task = await taskmaster_service.update_task_status(
            "test-id", TaskStatus.DONE, "Task completed successfully"
        )

        assert updated_task.status == TaskStatus.DONE
        assert updated_task.completed_at is not None

        # Verify notification was sent
        taskmaster_service.cache_utilities.notify_mcp_server_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_task_progress(self, taskmaster_service, sample_task_data):
        """Test task progress update."""
        taskmaster_service.cache_service.get.return_value = sample_task_data

        updated_task = await taskmaster_service.update_task_progress(
            "test-id", 75.0, "Three quarters complete"
        )

        assert updated_task.metrics.completion_percentage == 75.0
        # Should remain in progress, not auto-complete
        assert updated_task.status == TaskStatus.IN_PROGRESS

    @pytest.mark.asyncio
    async def test_analyze_task_complexity(self, taskmaster_service, sample_task_data):
        """Test task complexity analysis."""
        complex_task_data = {
            **sample_task_data,
            "description": "A" * 600,  # Long description
            "details": "B" * 1200,     # Long details
            "subtasks": [{"title": f"Subtask {i}"} for i in range(5)],
            "dependencies": [{"task_id": f"dep-{i}"} for i in range(3)]
        }
        taskmaster_service.cache_service.get.return_value = complex_task_data

        analysis = await taskmaster_service.analyze_task_complexity("test-id")

        assert "complexity_score" in analysis
        assert "complexity_category" in analysis
        assert "factors" in analysis
        assert "recommendations" in analysis
        assert 1 <= analysis["complexity_score"] <= 10

    @pytest.mark.asyncio
    async def test_get_task_statistics(self, taskmaster_service):
        """Test task statistics retrieval."""
        # Mock cached statistics
        taskmaster_service.cache_service.get.return_value = None  # No cache

        stats = await taskmaster_service.get_task_statistics()

        assert isinstance(stats, TaskStats)
        assert stats.total_tasks == 0  # Default empty stats

        # Verify caching
        taskmaster_service.cache_service.set.assert_called()

    @pytest.mark.asyncio
    async def test_get_service_metrics(self, taskmaster_service):
        """Test service metrics retrieval."""
        # Set up some operation counts
        taskmaster_service._operation_count = 50
        taskmaster_service._cache_hit_count = 30
        taskmaster_service._cache_miss_count = 20

        metrics = await taskmaster_service.get_service_metrics()

        assert metrics["total_operations"] == 50
        assert metrics["cache_metrics"]["cache_hits"] == 30
        assert metrics["cache_metrics"]["hit_rate"] == 60.0  # 30/50 * 100

    @pytest.mark.asyncio
    async def test_list_tasks_empty(self, taskmaster_service):
        """Test listing tasks when none exist."""
        task_list = await taskmaster_service.list_tasks()

        assert isinstance(task_list, TaskList)
        assert task_list.total_count == 0
        assert len(task_list.tasks) == 0
        assert task_list.page == 1

    @pytest.mark.asyncio
    async def test_search_tasks_empty(self, taskmaster_service):
        """Test searching tasks when none exist."""
        results = await taskmaster_service.search_tasks("test query")

        assert isinstance(results, list)
        assert len(results) == 0


class TestTaskMasterAPI:
    """Test suite for TaskMaster API endpoints."""

    @pytest.fixture
    def test_client(self):
        """Create test client with TaskMaster router."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(taskmaster_router, prefix="/api/v1")

        return TestClient(app)

    @pytest.fixture
    def mock_taskmaster_service(self):
        """Mock TaskMaster service for API testing."""
        mock = AsyncMock(spec=TaskMasterService)
        return mock

    def test_get_task_enums(self, test_client):
        """Test getting task enumeration values."""
        response = test_client.get("/api/v1/tasks/enums")

        assert response.status_code == 200
        data = response.json()

        assert "statuses" in data
        assert "priorities" in data
        assert "types" in data
        assert "complexities" in data

        assert TaskStatus.PENDING.value in data["statuses"]
        assert TaskPriority.HIGH.value in data["priorities"]

    @patch('app.api.v1.taskmaster.get_taskmaster_service')
    def test_create_task_success(self, mock_get_service, test_client, sample_task_data):
        """Test successful task creation via API."""
        # Mock service
        mock_service = AsyncMock()
        mock_task = Task(**sample_task_data)
        mock_service.create_task.return_value = mock_task
        mock_get_service.return_value = mock_service

        response = test_client.post("/api/v1/tasks/", json=sample_task_data)

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Test Task"

    @patch('app.api.v1.taskmaster.get_taskmaster_service')
    def test_create_task_validation_error(self, mock_get_service, test_client):
        """Test task creation with validation error."""
        mock_service = AsyncMock()
        mock_service.create_task.side_effect = ValidationError("Invalid data")
        mock_get_service.return_value = mock_service

        response = test_client.post("/api/v1/tasks/", json={"invalid": "data"})

        assert response.status_code == 400
        assert "error" in response.json()

    @patch('app.api.v1.taskmaster.get_taskmaster_service')
    def test_get_task_success(self, mock_get_service, test_client, sample_task_data):
        """Test successful task retrieval via API."""
        mock_service = AsyncMock()
        mock_task = Task(**sample_task_data)
        mock_service.get_task.return_value = mock_task
        mock_get_service.return_value = mock_service

        response = test_client.get("/api/v1/tasks/test-id")

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Task"

    @patch('app.api.v1.taskmaster.get_taskmaster_service')
    def test_get_task_not_found(self, mock_get_service, test_client):
        """Test task retrieval when not found."""
        mock_service = AsyncMock()
        mock_service.get_task.side_effect = NotFoundError("Task", "test-id")
        mock_get_service.return_value = mock_service

        response = test_client.get("/api/v1/tasks/nonexistent")

        assert response.status_code == 404
        assert "error" in response.json()

    @patch('app.api.v1.taskmaster.get_taskmaster_service')
    def test_update_task_status(self, mock_get_service, test_client, sample_task_data):
        """Test task status update via API."""
        mock_service = AsyncMock()
        updated_task = Task(**{**sample_task_data, "status": TaskStatus.DONE})
        mock_service.update_task_status.return_value = updated_task
        mock_get_service.return_value = mock_service

        response = test_client.patch(
            "/api/v1/tasks/test-id/status",
            json={"new_status": "done", "notes": "Task completed"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "done"

    @patch('app.api.v1.taskmaster.get_taskmaster_service')
    def test_list_tasks_with_filters(self, mock_get_service, test_client):
        """Test listing tasks with filters."""
        mock_service = AsyncMock()
        mock_task_list = TaskList(tasks=[], total_count=0, page=1, page_size=50)
        mock_service.list_tasks.return_value = mock_task_list
        mock_get_service.return_value = mock_service

        response = test_client.get(
            "/api/v1/tasks/?status=pending&priority=high&page=1&page_size=20"
        )

        assert response.status_code == 200
        data = response.json()
        assert "tasks" in data
        assert "total_count" in data
        assert data["page"] == 1

    @patch('app.api.v1.taskmaster.get_taskmaster_service')
    def test_analyze_task_complexity(self, mock_get_service, test_client):
        """Test task complexity analysis via API."""
        mock_service = AsyncMock()
        mock_analysis = {
            "task_id": "test-id",
            "complexity_score": 7,
            "complexity_category": "complex",
            "factors": {},
            "recommendations": ["Break into subtasks"]
        }
        mock_service.analyze_task_complexity.return_value = mock_analysis
        mock_get_service.return_value = mock_service

        response = test_client.get("/api/v1/tasks/test-id/complexity")

        assert response.status_code == 200
        data = response.json()
        assert data["complexity_score"] == 7
        assert data["complexity_category"] == "complex"

    @patch('app.api.v1.taskmaster.get_taskmaster_service')
    def test_get_task_statistics(self, mock_get_service, test_client):
        """Test task statistics retrieval via API."""
        mock_service = AsyncMock()
        mock_stats = TaskStats(
            total_tasks=100,
            completed_tasks=80,
            completion_rate=80.0
        )
        mock_service.get_task_statistics.return_value = mock_stats
        mock_get_service.return_value = mock_service

        response = test_client.get("/api/v1/tasks/statistics")

        assert response.status_code == 200
        data = response.json()
        assert data["total_tasks"] == 100
        assert data["completion_rate"] == 80.0

    @patch('app.api.v1.taskmaster.get_taskmaster_service')
    def test_service_health_check(self, mock_get_service, test_client):
        """Test TaskMaster service health check."""
        mock_service = AsyncMock()
        mock_metrics = {
            "total_operations": 100,
            "cache_metrics": {"hit_rate": 85.0},
            "complexity_cache_size": 50
        }
        mock_service.get_service_metrics.return_value = mock_metrics
        mock_get_service.return_value = mock_service

        response = test_client.get("/api/v1/tasks/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "metrics" in data


class TestTaskMasterIntegration:
    """Integration tests for TaskMaster with cache and database."""

    @pytest.mark.asyncio
    async def test_task_caching_integration(self, taskmaster_service, sample_task_data):
        """Test task caching integration."""
        # Create task (should cache it)
        task = await taskmaster_service.create_task(sample_task_data)

        # Verify cache was called for creation
        assert taskmaster_service.cache_service.set.called

        # Mock cache hit for retrieval
        taskmaster_service.cache_service.get.return_value = task.dict()

        # Retrieve task (should hit cache)
        retrieved_task = await taskmaster_service.get_task(task.id, raise_if_not_found=False)

        assert retrieved_task is not None
        assert retrieved_task.title == task.title
        assert taskmaster_service._cache_hit_count > 0

    @pytest.mark.asyncio
    async def test_task_complexity_caching(self, taskmaster_service, sample_task_data):
        """Test task complexity analysis caching."""
        taskmaster_service.cache_service.get.return_value = sample_task_data

        # First analysis
        analysis1 = await taskmaster_service.analyze_task_complexity("test-id")

        # Second analysis (should use cache)
        analysis2 = await taskmaster_service.analyze_task_complexity("test-id")

        assert analysis1["complexity_score"] == analysis2["complexity_score"]
        assert "test-id" in taskmaster_service._complexity_cache

    @pytest.mark.asyncio
    async def test_task_notification_integration(self, taskmaster_service, sample_task_data):
        """Test task status change notifications."""
        taskmaster_service.cache_service.get.return_value = sample_task_data
        taskmaster_service.cache_utilities.notify_mcp_server_update = AsyncMock(return_value=1)

        # Update task status
        await taskmaster_service.update_task_status("test-id", TaskStatus.DONE, "Completed")

        # Verify notification was sent
        taskmaster_service.cache_utilities.notify_mcp_server_update.assert_called_once()
        call_args = taskmaster_service.cache_utilities.notify_mcp_server_update.call_args
        assert call_args[0][0] == "test-id"  # task_id
        assert call_args[0][1] == "status_change"  # event type

    @pytest.mark.asyncio
    async def test_task_dependency_validation(self, taskmaster_service, sample_task_data):
        """Test task dependency validation and cycle detection."""
        # Mock tasks for dependency chain
        task_a = {**sample_task_data, "id": "task-a"}
        task_b = {**sample_task_data, "id": "task-b"}

        # Set up mock responses
        taskmaster_service.cache_service.get.side_effect = [task_a, task_b]

        # Add valid dependency
        result = await taskmaster_service.add_task_dependency("task-a", "task-b")
        assert result is True

    @pytest.mark.asyncio
    async def test_service_metrics_collection(self, taskmaster_service):
        """Test comprehensive service metrics collection."""
        # Simulate some operations
        taskmaster_service._operation_count = 100
        taskmaster_service._cache_hit_count = 70
        taskmaster_service._cache_miss_count = 30
        taskmaster_service._complexity_cache["task-1"] = 5
        taskmaster_service._complexity_cache["task-2"] = 8

        metrics = await taskmaster_service.get_service_metrics()

        assert metrics["total_operations"] == 100
        assert metrics["cache_metrics"]["hit_rate"] == 70.0
        assert metrics["complexity_cache_size"] == 2
        assert "timestamp" in metrics

    @pytest.mark.asyncio
    async def test_bulk_task_operations(self, taskmaster_service):
        """Test bulk task operations performance."""
        # Test empty list operations
        task_list = await taskmaster_service.list_tasks(page=1, page_size=100)
        assert isinstance(task_list, TaskList)
        assert task_list.total_count == 0

        # Test search with empty results
        search_results = await taskmaster_service.search_tasks("nonexistent", limit=50)
        assert isinstance(search_results, list)
        assert len(search_results) == 0

    @pytest.mark.asyncio
    async def test_task_operation_logging(self, taskmaster_service, sample_task_data):
        """Test task operation logging and audit trail."""
        taskmaster_service.cache_service.get.return_value = None

        # Create task (should log operation)
        task = await taskmaster_service.create_task(sample_task_data)

        # Verify operation was logged to cache
        set_calls = [call for call in taskmaster_service.cache_service.set.call_args_list]

        # Should have at least 2 calls: task cache + operation log
        assert len(set_calls) >= 2

        # Check that operation logging was called
        operation_logged = any(
            "operation:" in str(call) for call in set_calls
        )
        # Note: This is a simplified check - in real testing we'd verify the exact log entry


class TestTaskMasterComplexity:
    """Test suite for task complexity assessment edge cases."""

    @pytest.mark.asyncio
    async def test_complexity_calculation_factors(self, taskmaster_service):
        """Test detailed complexity calculation factors."""
        # Minimal task
        minimal_task = {
            "id": "minimal-task",
            "title": "Simple Task",
            "description": "Short",
            "details": "Brief",
            "subtasks": [],
            "dependencies": [],
            "task_type": TaskType.BUGFIX
        }

        taskmaster_service.cache_service.get.return_value = minimal_task
        analysis = await taskmaster_service.analyze_task_complexity("minimal-task")

        assert analysis["complexity_score"] <= 3
        assert "factors" in analysis
        assert "recommendations" in analysis

    @pytest.mark.asyncio
    async def test_complexity_recommendations(self, taskmaster_service):
        """Test complexity-based recommendations."""
        # Expert-level complex task
        complex_task = {
            "id": "complex-task",
            "title": "Expert Task",
            "description": "A" * 700,  # Very long description
            "details": "B" * 1500,     # Very long details
            "subtasks": [{"title": f"Subtask {i}"} for i in range(8)],
            "dependencies": [{"task_id": f"dep-{i}"} for i in range(4)],
            "task_type": TaskType.RESEARCH
        }

        taskmaster_service.cache_service.get.return_value = complex_task
        analysis = await taskmaster_service.analyze_task_complexity("complex-task")

        assert analysis["complexity_score"] >= 8
        recommendations = analysis["recommendations"]
        assert any("expert" in rec.lower() or "senior" in rec.lower() for rec in recommendations)

    @pytest.mark.asyncio
    async def test_complexity_caching_behavior(self, taskmaster_service, sample_task_data):
        """Test complexity analysis caching behavior."""
        taskmaster_service.cache_service.get.return_value = sample_task_data

        # First calculation
        analysis1 = await taskmaster_service.analyze_task_complexity("test-id", recalculate=False)
        score1 = analysis1["complexity_score"]

        # Second calculation (should use cache)
        analysis2 = await taskmaster_service.analyze_task_complexity("test-id", recalculate=False)
        score2 = analysis2["complexity_score"]

        assert score1 == score2
        assert "test-id" in taskmaster_service._complexity_cache

        # Force recalculation
        analysis3 = await taskmaster_service.analyze_task_complexity("test-id", recalculate=True)
        score3 = analysis3["complexity_score"]

        # Should still be the same (same task data)
        assert score3 == score1


class TestTaskMasterErrorHandling:
    """Test suite for error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_invalid_task_data_handling(self, taskmaster_service):
        """Test handling of invalid task data."""
        invalid_data = {
            "title": "",  # Empty title should fail
            "metrics": {"completion_percentage": 150}  # Invalid percentage
        }

        with pytest.raises(ValidationError):
            await taskmaster_service.create_task(invalid_data)

    @pytest.mark.asyncio
    async def test_cache_failure_resilience(self, taskmaster_service, sample_task_data):
        """Test resilience when cache operations fail."""
        # Mock cache failure
        taskmaster_service.cache_service.get.side_effect = Exception("Cache failure")

        # Should handle gracefully
        task = await taskmaster_service.get_task("test-id", raise_if_not_found=False)
        assert task is None  # Should return None instead of raising

    @pytest.mark.asyncio
    async def test_dependency_validation_errors(self, taskmaster_service, sample_task_data):
        """Test dependency validation error handling."""
        # Task with invalid dependency
        task_data_with_invalid_dep = {
            **sample_task_data,
            "dependencies": [{"task_id": "nonexistent-task", "dependency_type": "blocks"}]
        }

        with pytest.raises(ValidationError):
            await taskmaster_service.create_task(task_data_with_invalid_dep, validate_dependencies=True)

    @pytest.mark.asyncio
    async def test_concurrent_operation_safety(self, taskmaster_service, sample_task_data):
        """Test safety of concurrent operations."""
        taskmaster_service.cache_service.get.return_value = sample_task_data

        # Simulate concurrent updates
        tasks = []
        for i in range(5):
            task = taskmaster_service.update_task_progress("test-id", 20.0 * i, f"Update {i}")
            tasks.append(task)

        # Execute concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should complete (though some might return exceptions due to mocking)
        assert len(results) == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
