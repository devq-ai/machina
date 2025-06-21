"""
Task Models for TaskMaster AI Integration

This module defines the data models for TaskMaster AI integration in the Machina
Registry Service, implementing DevQ.ai's standard task management patterns with
comprehensive validation, status tracking, and complexity assessment.

Features:
- Task and subtask models with full lifecycle support
- Task status tracking with timestamps and progress metrics
- Task complexity assessment and scoring
- Task dependency management and validation
- Integration with Pydantic for type safety and validation
- Support for task serialization and caching
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union, ForwardRef
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator
import logfire


class TaskStatus(str, Enum):
    """Task status enumeration for lifecycle management."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    DONE = "done"
    DEFERRED = "deferred"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    """Task priority levels for scheduling and execution."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TaskComplexity(str, Enum):
    """Task complexity categories for planning and estimation."""
    TRIVIAL = "trivial"      # 1-2 complexity score
    SIMPLE = "simple"        # 3-4 complexity score
    MODERATE = "moderate"    # 5-6 complexity score
    COMPLEX = "complex"      # 7-8 complexity score
    EXPERT = "expert"        # 9-10 complexity score


class TaskType(str, Enum):
    """Task type categories for organization and filtering."""
    FEATURE = "feature"
    BUGFIX = "bugfix"
    REFACTOR = "refactor"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    INFRASTRUCTURE = "infrastructure"
    RESEARCH = "research"
    MAINTENANCE = "maintenance"


# Forward reference for recursive subtask relationships
SubTask = ForwardRef('Task')


class TaskDependency(BaseModel):
    """Task dependency model for managing task relationships."""

    task_id: str = Field(..., description="ID of the dependent task")
    dependency_type: str = Field(default="blocks", description="Type of dependency relationship")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="When dependency was created")

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TaskMetrics(BaseModel):
    """Task performance and progress metrics."""

    estimated_hours: Optional[float] = Field(None, ge=0, description="Estimated time to complete in hours")
    actual_hours: Optional[float] = Field(None, ge=0, description="Actual time spent in hours")
    completion_percentage: float = Field(default=0.0, ge=0, le=100, description="Completion percentage")
    complexity_score: Optional[int] = Field(None, ge=1, le=10, description="Complexity score (1-10)")
    lines_of_code: Optional[int] = Field(None, ge=0, description="Lines of code added/modified")
    test_coverage: Optional[float] = Field(None, ge=0, le=100, description="Test coverage percentage")

    @field_validator('completion_percentage')
    @classmethod
    def validate_completion_percentage(cls, v):
        """Ensure completion percentage is within valid range."""
        return round(v, 2)

    @property
    def efficiency_ratio(self) -> Optional[float]:
        """Calculate efficiency ratio (estimated vs actual hours)."""
        if self.estimated_hours and self.actual_hours and self.actual_hours > 0:
            return round(self.estimated_hours / self.actual_hours, 2)
        return None

    @property
    def is_overdue(self) -> bool:
        """Check if task is taking longer than estimated."""
        if self.estimated_hours and self.actual_hours:
            return self.actual_hours > self.estimated_hours
        return False


class TaskContext(BaseModel):
    """Task context information for development environment."""

    repository: Optional[str] = Field(None, description="Git repository URL or name")
    branch: Optional[str] = Field(None, description="Git branch name")
    commit_hash: Optional[str] = Field(None, description="Associated commit hash")
    pull_request: Optional[str] = Field(None, description="Pull request number or URL")
    environment: Optional[str] = Field(None, description="Development environment")
    assigned_to: Optional[str] = Field(None, description="Developer assigned to task")
    reviewer: Optional[str] = Field(None, description="Code reviewer")
    tags: List[str] = Field(default_factory=list, description="Task tags for organization")

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "repository": "machina-registry",
                "branch": "feature/task-integration",
                "environment": "development",
                "assigned_to": "developer@devq.ai",
                "tags": ["backend", "api", "cache"]
            }
        }


class TaskValidation(BaseModel):
    """Task validation and quality assurance information."""

    test_strategy: Optional[str] = Field(None, description="Testing strategy and approach")
    acceptance_criteria: List[str] = Field(default_factory=list, description="Acceptance criteria for completion")
    validation_steps: List[str] = Field(default_factory=list, description="Steps to validate task completion")
    quality_gates: List[str] = Field(default_factory=list, description="Quality gates that must be passed")
    reviewed: bool = Field(default=False, description="Whether task has been reviewed")
    approved: bool = Field(default=False, description="Whether task has been approved")

    @field_validator('acceptance_criteria', 'validation_steps', 'quality_gates')
    @classmethod
    def validate_lists_not_empty_strings(cls, v):
        """Remove empty strings from lists."""
        return [item.strip() for item in v if item.strip()]


class Task(BaseModel):
    """
    Main task model for TaskMaster AI integration.

    Represents a complete task with all metadata, dependencies, and subtasks.
    Supports hierarchical task structures and comprehensive tracking.
    """

    # Core task identification
    id: str = Field(default_factory=lambda: str(uuid4()), description="Unique task identifier")
    title: str = Field(..., min_length=1, max_length=200, description="Task title")
    description: str = Field(default="", description="Detailed task description")

    # Task classification
    task_type: TaskType = Field(default=TaskType.FEATURE, description="Task type category")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM, description="Task priority level")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Current task status")

    # Task organization
    parent_id: Optional[str] = Field(None, description="Parent task ID for subtasks")
    dependencies: List[TaskDependency] = Field(default_factory=list, description="Task dependencies")
    subtasks: List['Task'] = Field(default_factory=list, description="Child subtasks")

    # Task content and implementation
    details: str = Field(default="", description="Detailed implementation notes")
    implementation_notes: List[str] = Field(default_factory=list, description="Implementation notes and updates")

    # Task tracking and metrics
    metrics: TaskMetrics = Field(default_factory=TaskMetrics, description="Task performance metrics")
    context: TaskContext = Field(default_factory=TaskContext, description="Task development context")
    validation: TaskValidation = Field(default_factory=TaskValidation, description="Task validation information")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Task creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    started_at: Optional[datetime] = Field(None, description="Task start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Task completion timestamp")
    due_date: Optional[datetime] = Field(None, description="Task due date")

    # Metadata
    version: int = Field(default=1, description="Task version for change tracking")
    checksum: Optional[str] = Field(None, description="Task content checksum for change detection")

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }
        json_schema_extra = {
            "example": {
                "id": "task_123",
                "title": "Implement Redis Cache Integration",
                "description": "Add Redis caching to improve application performance",
                "task_type": "feature",
                "priority": "high",
                "status": "in_progress",
                "details": "Implement async Redis connection with connection pooling...",
                "metrics": {
                    "estimated_hours": 8.0,
                    "completion_percentage": 75.0,
                    "complexity_score": 7
                },
                "context": {
                    "repository": "machina-registry",
                    "branch": "feature/redis-cache",
                    "assigned_to": "developer@devq.ai",
                    "tags": ["backend", "performance", "cache"]
                }
            }
        }

    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        """Validate and clean task title."""
        return v.strip()

    @field_validator('updated_at')
    @classmethod
    def set_updated_at(cls, v):
        """Always update the updated_at timestamp."""
        return datetime.utcnow()

    @model_validator(mode='before')
    @classmethod
    def validate_task_consistency(cls, values):
        """Validate task data consistency."""
        if isinstance(values, dict):
            status = values.get('status')
            started_at = values.get('started_at')
            completed_at = values.get('completed_at')

            # Auto-set timestamps based on status
            if status == TaskStatus.IN_PROGRESS and not started_at:
                values['started_at'] = datetime.utcnow()
            elif status == TaskStatus.DONE and not completed_at:
                values['completed_at'] = datetime.utcnow()
                if 'metrics' not in values:
                    values['metrics'] = {}
                values['metrics']['completion_percentage'] = 100.0
            elif status != TaskStatus.DONE and completed_at:
                # Reset completion if status is not done
                values['completed_at'] = None

        return values

    @field_validator('dependencies')
    @classmethod
    def validate_no_self_dependency(cls, v, info):
        """Ensure task doesn't depend on itself."""
        if hasattr(info, 'data') and info.data:
            task_id = info.data.get('id')
            if task_id and any(dep.task_id == task_id for dep in v):
                raise ValueError("Task cannot depend on itself")
        return v

    def add_subtask(self, subtask: 'Task') -> None:
        """Add a subtask and set parent relationship."""
        subtask.parent_id = self.id
        self.subtasks.append(subtask)
        self.updated_at = datetime.utcnow()

        logfire.info(
            "Subtask added",
            parent_task_id=self.id,
            subtask_id=subtask.id,
            subtask_title=subtask.title
        )

    def add_dependency(self, task_id: str, dependency_type: str = "blocks") -> None:
        """Add a task dependency."""
        if task_id == self.id:
            raise ValueError("Task cannot depend on itself")

        # Check if dependency already exists
        existing = any(dep.task_id == task_id for dep in self.dependencies)
        if not existing:
            dependency = TaskDependency(task_id=task_id, dependency_type=dependency_type)
            self.dependencies.append(dependency)
            self.updated_at = datetime.utcnow()

            logfire.info(
                "Task dependency added",
                task_id=self.id,
                depends_on=task_id,
                dependency_type=dependency_type
            )

    def remove_dependency(self, task_id: str) -> bool:
        """Remove a task dependency."""
        initial_count = len(self.dependencies)
        self.dependencies = [dep for dep in self.dependencies if dep.task_id != task_id]

        if len(self.dependencies) < initial_count:
            self.updated_at = datetime.utcnow()
            logfire.info(
                "Task dependency removed",
                task_id=self.id,
                removed_dependency=task_id
            )
            return True
        return False

    def update_status(self, new_status: TaskStatus, notes: Optional[str] = None) -> None:
        """Update task status with proper timestamp management."""
        old_status = self.status
        self.status = new_status
        self.updated_at = datetime.utcnow()

        # Set timestamps based on status changes
        if new_status == TaskStatus.IN_PROGRESS and not self.started_at:
            self.started_at = datetime.utcnow()
        elif new_status == TaskStatus.DONE:
            self.completed_at = datetime.utcnow()
            self.metrics.completion_percentage = 100.0

        # Add implementation note if provided
        if notes:
            self.implementation_notes.append(f"[{datetime.utcnow().isoformat()}] Status changed from {old_status} to {new_status}: {notes}")

        logfire.info(
            "Task status updated",
            task_id=self.id,
            old_status=old_status,
            new_status=new_status,
            notes=notes
        )

    def update_progress(self, completion_percentage: float, notes: Optional[str] = None) -> None:
        """Update task completion percentage."""
        old_percentage = self.metrics.completion_percentage
        self.metrics.completion_percentage = max(0, min(100, completion_percentage))
        self.updated_at = datetime.utcnow()

        # Auto-update status based on completion
        if self.metrics.completion_percentage >= 100 and self.status != TaskStatus.DONE:
            self.update_status(TaskStatus.DONE, "Auto-completed based on 100% progress")
        elif self.metrics.completion_percentage > 0 and self.status == TaskStatus.PENDING:
            self.update_status(TaskStatus.IN_PROGRESS, "Auto-started based on progress update")

        if notes:
            self.implementation_notes.append(f"[{datetime.utcnow().isoformat()}] Progress updated from {old_percentage}% to {completion_percentage}%: {notes}")

        logfire.info(
            "Task progress updated",
            task_id=self.id,
            old_percentage=old_percentage,
            new_percentage=completion_percentage
        )

    def calculate_complexity_score(self) -> int:
        """Calculate task complexity score based on various factors."""
        score = 1  # Base score

        # Factor in subtasks
        if self.subtasks:
            score += min(len(self.subtasks) // 2, 3)  # +1-3 for subtasks

        # Factor in dependencies
        if self.dependencies:
            score += min(len(self.dependencies), 2)  # +1-2 for dependencies

        # Factor in description length and detail
        if len(self.description) > 500:
            score += 2
        elif len(self.description) > 200:
            score += 1

        # Factor in implementation details
        if len(self.details) > 1000:
            score += 2
        elif len(self.details) > 300:
            score += 1

        # Factor in task type
        complexity_by_type = {
            TaskType.RESEARCH: 3,
            TaskType.INFRASTRUCTURE: 2,
            TaskType.REFACTOR: 2,
            TaskType.FEATURE: 1,
            TaskType.TESTING: 1,
            TaskType.BUGFIX: 0,
            TaskType.DOCUMENTATION: 0,
            TaskType.MAINTENANCE: 0
        }
        score += complexity_by_type.get(self.task_type, 1)

        # Cap at 10
        final_score = min(score, 10)
        self.metrics.complexity_score = final_score

        return final_score

    @property
    def complexity_category(self) -> TaskComplexity:
        """Get task complexity category based on score."""
        score = self.metrics.complexity_score or self.calculate_complexity_score()

        if score <= 2:
            return TaskComplexity.TRIVIAL
        elif score <= 4:
            return TaskComplexity.SIMPLE
        elif score <= 6:
            return TaskComplexity.MODERATE
        elif score <= 8:
            return TaskComplexity.COMPLEX
        else:
            return TaskComplexity.EXPERT

    @property
    def is_blocked(self) -> bool:
        """Check if task is blocked by incomplete dependencies."""
        return self.status == TaskStatus.BLOCKED

    @property
    def is_overdue(self) -> bool:
        """Check if task is overdue based on due date."""
        if self.due_date and self.status not in [TaskStatus.DONE, TaskStatus.CANCELLED]:
            return datetime.utcnow() > self.due_date
        return False

    @property
    def age_days(self) -> int:
        """Get task age in days."""
        return (datetime.utcnow() - self.created_at).days

    @property
    def duration_hours(self) -> Optional[float]:
        """Calculate task duration in hours if completed."""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return round(delta.total_seconds() / 3600, 2)
        elif self.started_at:
            delta = datetime.utcnow() - self.started_at
            return round(delta.total_seconds() / 3600, 2)
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary with proper serialization."""
        return self.dict(by_alias=True)

    def to_summary(self) -> Dict[str, Any]:
        """Get task summary for list views."""
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status,
            "priority": self.priority,
            "task_type": self.task_type,
            "completion_percentage": self.metrics.completion_percentage,
            "complexity_score": self.metrics.complexity_score,
            "complexity_category": self.complexity_category,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "age_days": self.age_days,
            "is_overdue": self.is_overdue,
            "subtasks_count": len(self.subtasks),
            "dependencies_count": len(self.dependencies)
        }


# Update forward reference
Task.update_forward_refs()


class TaskList(BaseModel):
    """Task list model for bulk operations and pagination."""

    tasks: List[Task] = Field(default_factory=list, description="List of tasks")
    total_count: int = Field(default=0, description="Total number of tasks")
    page: int = Field(default=1, ge=1, description="Current page number")
    page_size: int = Field(default=50, ge=1, le=1000, description="Number of tasks per page")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Applied filters")

    @property
    def total_pages(self) -> int:
        """Calculate total number of pages."""
        if self.page_size == 0:
            return 0
        return (self.total_count + self.page_size - 1) // self.page_size

    @property
    def has_next_page(self) -> bool:
        """Check if there are more pages."""
        return self.page < self.total_pages

    @property
    def has_previous_page(self) -> bool:
        """Check if there are previous pages."""
        return self.page > 1


class TaskStats(BaseModel):
    """Task statistics and analytics model."""

    total_tasks: int = Field(default=0, description="Total number of tasks")
    completed_tasks: int = Field(default=0, description="Number of completed tasks")
    in_progress_tasks: int = Field(default=0, description="Number of in-progress tasks")
    pending_tasks: int = Field(default=0, description="Number of pending tasks")
    blocked_tasks: int = Field(default=0, description="Number of blocked tasks")
    overdue_tasks: int = Field(default=0, description="Number of overdue tasks")

    average_completion_time: Optional[float] = Field(None, description="Average completion time in hours")
    average_complexity_score: Optional[float] = Field(None, description="Average complexity score")
    completion_rate: float = Field(default=0.0, description="Task completion rate percentage")

    by_priority: Dict[str, int] = Field(default_factory=dict, description="Tasks by priority")
    by_type: Dict[str, int] = Field(default_factory=dict, description="Tasks by type")
    by_complexity: Dict[str, int] = Field(default_factory=dict, description="Tasks by complexity")

    generated_at: datetime = Field(default_factory=datetime.utcnow, description="Statistics generation timestamp")

    @property
    def productivity_score(self) -> float:
        """Calculate productivity score based on completion rate and efficiency."""
        base_score = self.completion_rate

        # Adjust based on average complexity
        if self.average_complexity_score:
            complexity_bonus = min(self.average_complexity_score / 10, 0.2)
            base_score += complexity_bonus * 10

        # Penalize for overdue tasks
        if self.total_tasks > 0:
            overdue_penalty = (self.overdue_tasks / self.total_tasks) * 10
            base_score -= overdue_penalty

        return max(0, min(100, base_score))


class TaskFilter(BaseModel):
    """Task filtering model for search and list operations."""

    status: Optional[List[TaskStatus]] = Field(None, description="Filter by task status")
    priority: Optional[List[TaskPriority]] = Field(None, description="Filter by priority")
    task_type: Optional[List[TaskType]] = Field(None, description="Filter by task type")
    assigned_to: Optional[str] = Field(None, description="Filter by assignee")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")

    created_after: Optional[datetime] = Field(None, description="Filter tasks created after date")
    created_before: Optional[datetime] = Field(None, description="Filter tasks created before date")
    due_after: Optional[datetime] = Field(None, description="Filter tasks due after date")
    due_before: Optional[datetime] = Field(None, description="Filter tasks due before date")

    complexity_min: Optional[int] = Field(None, ge=1, le=10, description="Minimum complexity score")
    complexity_max: Optional[int] = Field(None, ge=1, le=10, description="Maximum complexity score")
    completion_min: Optional[float] = Field(None, ge=0, le=100, description="Minimum completion percentage")
    completion_max: Optional[float] = Field(None, ge=0, le=100, description="Maximum completion percentage")

    search_text: Optional[str] = Field(None, description="Search in title and description")
    include_subtasks: bool = Field(default=False, description="Include subtasks in results")

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TaskOperation(BaseModel):
    """Task operation model for tracking changes and operations."""

    operation_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique operation identifier")
    task_id: str = Field(..., description="Target task ID")
    operation_type: str = Field(..., description="Type of operation performed")
    operation_data: Dict[str, Any] = Field(default_factory=dict, description="Operation data and parameters")

    performed_by: Optional[str] = Field(None, description="User who performed the operation")
    performed_at: datetime = Field(default_factory=datetime.utcnow, description="When operation was performed")

    success: bool = Field(default=True, description="Whether operation was successful")
    error_message: Optional[str] = Field(None, description="Error message if operation failed")
    result_data: Dict[str, Any] = Field(default_factory=dict, description="Operation result data")

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
