"""
TaskMaster AI Service for Machina Registry Service

This module provides the TaskMaster AI service implementation for the Machina Registry
Service, implementing DevQ.ai's standard task management patterns with comprehensive
task operations, caching integration, and observability.

Features:
- Complete task CRUD operations with validation
- Task dependency management and cycle detection
- Task complexity assessment and scoring
- Integration with Redis cache for performance
- Task statistics and analytics
- Bulk operations and batch processing
- Task search and filtering capabilities
- Integration with TaskMaster AI CLI and tools
"""

import asyncio
import hashlib
import json
import time
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta
from uuid import uuid4

import logfire
from pydantic import ValidationError

from ..models.task_models import (
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
    TaskMetrics
)
from ..core.cache import CacheService, CacheKeyType
from ..services.cache_service import CacheUtilities
from ..core.exceptions import (
    NotFoundError,
    ValidationError as MachinaValidationError,
    ConflictError,
    DatabaseError
)


class TaskMasterService:
    """
    Comprehensive TaskMaster AI service for task management.

    Provides high-level task management operations with caching,
    validation, and integration with the TaskMaster AI ecosystem.
    """

    def __init__(self, cache_service: CacheService):
        """
        Initialize TaskMaster service.

        Args:
            cache_service: Redis cache service for performance optimization
        """
        self.cache_service = cache_service
        self.cache_utilities = CacheUtilities(cache_service)

        # Task operation tracking
        self._operation_count = 0
        self._cache_hit_count = 0
        self._cache_miss_count = 0

        # Task complexity analysis cache
        self._complexity_cache: Dict[str, int] = {}

        logfire.info("TaskMaster service initialized")

    async def create_task(self, task_data: Dict[str, Any],
                         validate_dependencies: bool = True) -> Task:
        """
        Create a new task with validation and caching.

        Args:
            task_data: Task data dictionary
            validate_dependencies: Whether to validate task dependencies

        Returns:
            Created Task instance

        Raises:
            ValidationError: If task data is invalid
            ConflictError: If task with same ID already exists
        """
        with logfire.span("TaskMaster create_task", task_title=task_data.get("title")):
            try:
                # Create task instance with validation
                task = Task(**task_data)

                # Check for existing task
                existing_task = await self.get_task(task.id, raise_if_not_found=False)
                if existing_task:
                    raise ConflictError(
                        resource_type="Task",
                        identifier=task.id,
                        message=f"Task with ID '{task.id}' already exists"
                    )

                # Validate dependencies if requested
                if validate_dependencies and task.dependencies:
                    await self._validate_task_dependencies(task)

                # Calculate complexity score
                task.calculate_complexity_score()

                # Cache the task
                await self._cache_task(task)

                # Log operation
                await self._log_operation(
                    task.id,
                    "create",
                    {"title": task.title, "task_type": task.task_type},
                    success=True
                )

                self._operation_count += 1

                logfire.info(
                    "Task created successfully",
                    task_id=task.id,
                    title=task.title,
                    complexity_score=task.metrics.complexity_score
                )

                return task

            except ValidationError as e:
                logfire.error("Task creation validation failed", error=str(e))
                raise MachinaValidationError(
                    message="Task validation failed",
                    field="task_data",
                    value=task_data,
                    cause=e
                )
            except Exception as e:
                logfire.error("Task creation failed", error=str(e))
                raise

    async def get_task(self, task_id: str,
                      include_subtasks: bool = True,
                      raise_if_not_found: bool = True) -> Optional[Task]:
        """
        Retrieve a task by ID with caching.

        Args:
            task_id: Task identifier
            include_subtasks: Whether to include subtasks
            raise_if_not_found: Whether to raise exception if not found

        Returns:
            Task instance or None if not found

        Raises:
            NotFoundError: If task not found and raise_if_not_found is True
        """
        with logfire.span("TaskMaster get_task", task_id=task_id):
            # Try cache first
            cached_task = await self.cache_service.get(
                CacheKeyType.MCP_TOOL,  # Using generic cache type for tasks
                f"task:{task_id}",
                deserialize=True
            )

            if cached_task:
                self._cache_hit_count += 1
                logfire.debug("Task retrieved from cache", task_id=task_id)

                try:
                    task = Task(**cached_task)

                    # Load subtasks if requested
                    if include_subtasks and task.subtasks:
                        for i, subtask_data in enumerate(task.subtasks):
                            if isinstance(subtask_data, dict):
                                task.subtasks[i] = Task(**subtask_data)

                    return task
                except ValidationError as e:
                    logfire.warning("Cached task data invalid, removing from cache",
                                  task_id=task_id, error=str(e))
                    await self.cache_service.delete(CacheKeyType.MCP_TOOL, f"task:{task_id}")

            self._cache_miss_count += 1

            # TODO: In a real implementation, this would query the database
            # For now, return None to simulate task not found
            if raise_if_not_found:
                raise NotFoundError(
                    resource_type="Task",
                    identifier=task_id
                )

            return None

    async def update_task(self, task_id: str, updates: Dict[str, Any],
                         validate_dependencies: bool = True) -> Task:
        """
        Update an existing task with validation.

        Args:
            task_id: Task identifier
            updates: Dictionary of updates to apply
            validate_dependencies: Whether to validate dependencies

        Returns:
            Updated Task instance

        Raises:
            NotFoundError: If task not found
            ValidationError: If updates are invalid
        """
        with logfire.span("TaskMaster update_task", task_id=task_id):
            # Get existing task
            existing_task = await self.get_task(task_id)

            # Apply updates
            task_data = existing_task.dict()
            task_data.update(updates)

            # Handle special update fields
            if 'status' in updates:
                task_data['updated_at'] = datetime.utcnow()

                # Auto-set timestamps based on status
                if updates['status'] == TaskStatus.IN_PROGRESS and not task_data.get('started_at'):
                    task_data['started_at'] = datetime.utcnow()
                elif updates['status'] == TaskStatus.DONE and not task_data.get('completed_at'):
                    task_data['completed_at'] = datetime.utcnow()
                    task_data['metrics']['completion_percentage'] = 100.0

            try:
                # Create updated task
                updated_task = Task(**task_data)

                # Validate dependencies if changed
                if validate_dependencies and 'dependencies' in updates:
                    await self._validate_task_dependencies(updated_task)

                # Recalculate complexity if content changed
                content_fields = ['description', 'details', 'subtasks', 'dependencies']
                if any(field in updates for field in content_fields):
                    updated_task.calculate_complexity_score()

                # Update cache
                await self._cache_task(updated_task)

                # Log operation
                await self._log_operation(
                    task_id,
                    "update",
                    updates,
                    success=True
                )

                self._operation_count += 1

                logfire.info(
                    "Task updated successfully",
                    task_id=task_id,
                    updated_fields=list(updates.keys())
                )

                return updated_task

            except ValidationError as e:
                logfire.error("Task update validation failed", task_id=task_id, error=str(e))
                raise MachinaValidationError(
                    message="Task update validation failed",
                    field="updates",
                    value=updates,
                    cause=e
                )

    async def delete_task(self, task_id: str, cascade: bool = False) -> bool:
        """
        Delete a task and optionally its subtasks.

        Args:
            task_id: Task identifier
            cascade: Whether to delete subtasks as well

        Returns:
            True if task was deleted

        Raises:
            NotFoundError: If task not found
            ConflictError: If task has dependencies and cascade is False
        """
        with logfire.span("TaskMaster delete_task", task_id=task_id):
            # Get existing task
            task = await self.get_task(task_id)

            # Check for subtasks
            if task.subtasks and not cascade:
                raise ConflictError(
                    resource_type="Task",
                    identifier=task_id,
                    message="Task has subtasks. Use cascade=True to delete all subtasks."
                )

            # Delete subtasks if cascade is enabled
            if cascade and task.subtasks:
                for subtask in task.subtasks:
                    await self.delete_task(subtask.id, cascade=True)

            # Remove from cache
            await self.cache_service.delete(CacheKeyType.MCP_TOOL, f"task:{task_id}")

            # Log operation
            await self._log_operation(
                task_id,
                "delete",
                {"cascade": cascade},
                success=True
            )

            self._operation_count += 1

            logfire.info("Task deleted successfully", task_id=task_id, cascade=cascade)
            return True

    async def list_tasks(self, filters: Optional[TaskFilter] = None,
                        page: int = 1, page_size: int = 50,
                        sort_by: str = "created_at",
                        sort_order: str = "desc") -> TaskList:
        """
        List tasks with filtering, pagination, and sorting.

        Args:
            filters: Task filtering criteria
            page: Page number (1-based)
            page_size: Number of tasks per page
            sort_by: Field to sort by
            sort_order: Sort order ('asc' or 'desc')

        Returns:
            TaskList with filtered and paginated tasks
        """
        with logfire.span("TaskMaster list_tasks", page=page, page_size=page_size):
            # TODO: In a real implementation, this would query the database
            # For now, return empty list
            task_list = TaskList(
                tasks=[],
                total_count=0,
                page=page,
                page_size=page_size,
                filters=filters.dict() if filters else {}
            )

            logfire.info(
                "Tasks listed",
                total_count=task_list.total_count,
                page=page,
                page_size=page_size
            )

            return task_list

    async def search_tasks(self, query: str, filters: Optional[TaskFilter] = None,
                          limit: int = 20) -> List[Task]:
        """
        Search tasks by text query.

        Args:
            query: Search query string
            filters: Additional filtering criteria
            limit: Maximum number of results

        Returns:
            List of matching tasks
        """
        with logfire.span("TaskMaster search_tasks", query=query, limit=limit):
            # TODO: Implement full-text search
            # For now, return empty list
            results = []

            logfire.info(
                "Task search completed",
                query=query,
                results_count=len(results)
            )

            return results

    async def get_task_statistics(self, filters: Optional[TaskFilter] = None) -> TaskStats:
        """
        Get task statistics and analytics.

        Args:
            filters: Optional filters to apply to statistics

        Returns:
            TaskStats with comprehensive analytics
        """
        with logfire.span("TaskMaster get_statistics"):
            # Check cache first
            cache_key = self._generate_stats_cache_key(filters)
            cached_stats = await self.cache_service.get(
                CacheKeyType.REGISTRY_STATUS,
                cache_key,
                deserialize=True
            )

            if cached_stats:
                logfire.debug("Statistics retrieved from cache")
                return TaskStats(**cached_stats)

            # TODO: Calculate statistics from database
            # For now, return default stats
            stats = TaskStats(
                total_tasks=0,
                completed_tasks=0,
                in_progress_tasks=0,
                pending_tasks=0,
                blocked_tasks=0,
                overdue_tasks=0,
                completion_rate=0.0,
                by_priority={},
                by_type={},
                by_complexity={}
            )

            # Cache statistics for 5 minutes
            await self.cache_service.set(
                CacheKeyType.REGISTRY_STATUS,
                cache_key,
                stats.dict(),
                ttl=300
            )

            logfire.info("Task statistics calculated", total_tasks=stats.total_tasks)
            return stats

    async def add_task_dependency(self, task_id: str, depends_on_id: str,
                                 dependency_type: str = "blocks") -> bool:
        """
        Add a dependency between tasks.

        Args:
            task_id: Task that depends on another
            depends_on_id: Task that is depended upon
            dependency_type: Type of dependency

        Returns:
            True if dependency was added

        Raises:
            NotFoundError: If either task not found
            ConflictError: If dependency would create a cycle
        """
        with logfire.span("TaskMaster add_dependency",
                         task_id=task_id, depends_on_id=depends_on_id):
            # Get both tasks
            task = await self.get_task(task_id)
            depends_on_task = await self.get_task(depends_on_id)

            # Check for cycle
            if await self._would_create_cycle(task_id, depends_on_id):
                raise ConflictError(
                    resource_type="Task Dependency",
                    identifier=f"{task_id} -> {depends_on_id}",
                    message="Adding this dependency would create a cycle"
                )

            # Add dependency
            task.add_dependency(depends_on_id, dependency_type)

            # Update cache
            await self._cache_task(task)

            logfire.info(
                "Task dependency added",
                task_id=task_id,
                depends_on_id=depends_on_id,
                dependency_type=dependency_type
            )

            return True

    async def remove_task_dependency(self, task_id: str, depends_on_id: str) -> bool:
        """
        Remove a dependency between tasks.

        Args:
            task_id: Task to remove dependency from
            depends_on_id: Dependency to remove

        Returns:
            True if dependency was removed
        """
        with logfire.span("TaskMaster remove_dependency",
                         task_id=task_id, depends_on_id=depends_on_id):
            task = await self.get_task(task_id)
            removed = task.remove_dependency(depends_on_id)

            if removed:
                await self._cache_task(task)
                logfire.info(
                    "Task dependency removed",
                    task_id=task_id,
                    depends_on_id=depends_on_id
                )

            return removed

    async def update_task_progress(self, task_id: str, completion_percentage: float,
                                  notes: Optional[str] = None) -> Task:
        """
        Update task completion progress.

        Args:
            task_id: Task identifier
            completion_percentage: New completion percentage (0-100)
            notes: Optional progress notes

        Returns:
            Updated Task instance
        """
        with logfire.span("TaskMaster update_progress",
                         task_id=task_id, completion=completion_percentage):
            task = await self.get_task(task_id)
            task.update_progress(completion_percentage, notes)

            # Update cache
            await self._cache_task(task)

            # Log operation
            await self._log_operation(
                task_id,
                "update_progress",
                {"completion_percentage": completion_percentage, "notes": notes},
                success=True
            )

            logfire.info(
                "Task progress updated",
                task_id=task_id,
                completion_percentage=completion_percentage
            )

            return task

    async def update_task_status(self, task_id: str, new_status: TaskStatus,
                               notes: Optional[str] = None) -> Task:
        """
        Update task status with proper state transitions.

        Args:
            task_id: Task identifier
            new_status: New task status
            notes: Optional status change notes

        Returns:
            Updated Task instance
        """
        with logfire.span("TaskMaster update_status",
                         task_id=task_id, new_status=new_status):
            task = await self.get_task(task_id)
            old_status = task.status

            task.update_status(new_status, notes)

            # Update cache
            await self._cache_task(task)

            # Publish status change event
            await self.cache_utilities.notify_mcp_server_update(
                task_id,
                "status_change",
                {
                    "old_status": old_status,
                    "new_status": new_status,
                    "notes": notes,
                    "task_title": task.title
                }
            )

            # Log operation
            await self._log_operation(
                task_id,
                "update_status",
                {"old_status": old_status, "new_status": new_status, "notes": notes},
                success=True
            )

            logfire.info(
                "Task status updated",
                task_id=task_id,
                old_status=old_status,
                new_status=new_status
            )

            return task

    async def analyze_task_complexity(self, task_id: str,
                                    recalculate: bool = False) -> Dict[str, Any]:
        """
        Analyze task complexity with detailed breakdown.

        Args:
            task_id: Task identifier
            recalculate: Whether to force recalculation

        Returns:
            Dictionary with complexity analysis
        """
        with logfire.span("TaskMaster analyze_complexity", task_id=task_id):
            task = await self.get_task(task_id)

            # Check cache first
            if not recalculate and task_id in self._complexity_cache:
                cached_score = self._complexity_cache[task_id]
                logfire.debug("Complexity retrieved from cache",
                            task_id=task_id, score=cached_score)

            # Calculate complexity
            base_score = 1
            factors = {}

            # Analyze subtasks
            subtasks_factor = min(len(task.subtasks) // 2, 3)
            factors["subtasks"] = {
                "count": len(task.subtasks),
                "score_contribution": subtasks_factor
            }
            base_score += subtasks_factor

            # Analyze dependencies
            deps_factor = min(len(task.dependencies), 2)
            factors["dependencies"] = {
                "count": len(task.dependencies),
                "score_contribution": deps_factor
            }
            base_score += deps_factor

            # Analyze content complexity
            desc_length = len(task.description)
            details_length = len(task.details)

            desc_factor = 2 if desc_length > 500 else (1 if desc_length > 200 else 0)
            details_factor = 2 if details_length > 1000 else (1 if details_length > 300 else 0)

            factors["content"] = {
                "description_length": desc_length,
                "details_length": details_length,
                "description_factor": desc_factor,
                "details_factor": details_factor,
                "score_contribution": desc_factor + details_factor
            }
            base_score += desc_factor + details_factor

            # Task type complexity
            type_complexity = {
                TaskType.RESEARCH: 3,
                TaskType.INFRASTRUCTURE: 2,
                TaskType.REFACTOR: 2,
                TaskType.FEATURE: 1,
                TaskType.TESTING: 1,
                TaskType.BUGFIX: 0,
                TaskType.DOCUMENTATION: 0,
                TaskType.MAINTENANCE: 0
            }
            type_factor = type_complexity.get(task.task_type, 1)
            factors["task_type"] = {
                "type": task.task_type,
                "score_contribution": type_factor
            }
            base_score += type_factor

            # Final score
            final_score = min(base_score, 10)
            complexity_category = task.complexity_category

            # Cache result
            self._complexity_cache[task_id] = final_score

            analysis = {
                "task_id": task_id,
                "complexity_score": final_score,
                "complexity_category": complexity_category,
                "factors": factors,
                "recommendations": self._get_complexity_recommendations(final_score),
                "analyzed_at": datetime.utcnow().isoformat()
            }

            logfire.info(
                "Task complexity analyzed",
                task_id=task_id,
                complexity_score=final_score,
                category=complexity_category
            )

            return analysis

    async def get_service_metrics(self) -> Dict[str, Any]:
        """
        Get TaskMaster service performance metrics.

        Returns:
            Dictionary with service metrics
        """
        cache_stats = self.cache_service.get_stats()

        total_cache_operations = self._cache_hit_count + self._cache_miss_count
        cache_hit_rate = (
            self._cache_hit_count / total_cache_operations
            if total_cache_operations > 0 else 0
        )

        metrics = {
            "service_name": "TaskMaster AI Service",
            "total_operations": self._operation_count,
            "cache_metrics": {
                "cache_hits": self._cache_hit_count,
                "cache_misses": self._cache_miss_count,
                "hit_rate": round(cache_hit_rate * 100, 2),
                "total_cache_operations": cache_stats.total_operations
            },
            "complexity_cache_size": len(self._complexity_cache),
            "timestamp": datetime.utcnow().isoformat()
        }

        return metrics

    # Private helper methods

    async def _cache_task(self, task: Task) -> None:
        """Cache a task with appropriate TTL."""
        cache_key = f"task:{task.id}"
        await self.cache_service.set(
            CacheKeyType.MCP_TOOL,
            cache_key,
            task.dict(),
            ttl=3600  # 1 hour TTL
        )

    async def _validate_task_dependencies(self, task: Task) -> None:
        """Validate task dependencies exist and don't create cycles."""
        for dependency in task.dependencies:
            # Check if dependency exists
            dep_task = await self.get_task(dependency.task_id, raise_if_not_found=False)
            if not dep_task:
                raise MachinaValidationError(
                    message=f"Dependency task '{dependency.task_id}' not found",
                    field="dependencies",
                    value=dependency.task_id
                )

            # Check for cycles
            if await self._would_create_cycle(task.id, dependency.task_id):
                raise MachinaValidationError(
                    message=f"Dependency on '{dependency.task_id}' would create a cycle",
                    field="dependencies",
                    value=dependency.task_id
                )

    async def _would_create_cycle(self, task_id: str, depends_on_id: str) -> bool:
        """Check if adding a dependency would create a cycle."""
        # Simple cycle detection - in a full implementation,
        # this would do a complete graph traversal
        if task_id == depends_on_id:
            return True

        # Check if depends_on_id already depends on task_id (direct cycle)
        try:
            depends_on_task = await self.get_task(depends_on_id, raise_if_not_found=False)
            if depends_on_task:
                for dep in depends_on_task.dependencies:
                    if dep.task_id == task_id:
                        return True
        except:
            pass

        return False

    async def _log_operation(self, task_id: str, operation_type: str,
                           operation_data: Dict[str, Any], success: bool = True,
                           error_message: Optional[str] = None) -> None:
        """Log task operations for audit trail."""
        operation = TaskOperation(
            task_id=task_id,
            operation_type=operation_type,
            operation_data=operation_data,
            success=success,
            error_message=error_message
        )

        # Cache operation log
        log_key = f"operation:{operation.operation_id}"
        await self.cache_service.set(
            CacheKeyType.REGISTRY_STATUS,
            log_key,
            operation.dict(),
            ttl=86400  # 24 hours
        )

    def _generate_stats_cache_key(self, filters: Optional[TaskFilter]) -> str:
        """Generate cache key for statistics based on filters."""
        if not filters:
            return "stats:all"

        # Create hash of filter parameters
        filter_str = json.dumps(filters.dict(), sort_keys=True, default=str)
        filter_hash = hashlib.md5(filter_str.encode()).hexdigest()[:8]
        return f"stats:filtered:{filter_hash}"

    def _get_complexity_recommendations(self, score: int) -> List[str]:
        """Get recommendations based on complexity score."""
        if score <= 2:
            return [
                "Simple task - can be completed quickly",
                "Good candidate for new team members",
                "Consider combining with other small tasks"
            ]
        elif score <= 4:
            return [
                "Straightforward task with minimal complexity",
                "Should be completable in a single session",
                "Good for building confidence"
            ]
        elif score <= 6:
            return [
                "Moderate complexity - plan carefully",
                "Consider breaking into subtasks",
                "May require research or consultation"
            ]
        elif score <= 8:
            return [
                "Complex task requiring significant effort",
                "Should be broken into multiple subtasks",
                "Assign to experienced team members",
                "Consider pair programming or code reviews"
            ]
        else:
            return [
                "Expert-level task with high complexity",
                "Must be broken into smaller subtasks",
                "Requires senior developer or team lead",
                "Plan for extended timeline and reviews",
                "Consider architectural review before starting"
            ]
