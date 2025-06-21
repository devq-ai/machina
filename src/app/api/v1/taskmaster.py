"""
TaskMaster API Endpoints for Machina Registry Service

This module provides REST API endpoints for TaskMaster AI integration in the Machina
Registry Service, implementing DevQ.ai's standard API patterns with comprehensive
task management, validation, caching, and observability.

Features:
- Complete task CRUD operations with validation
- Task status and progress management
- Task dependency management
- Task complexity analysis
- Task search and filtering
- Bulk operations and batch processing
- Statistics and analytics endpoints
- Integration with Redis cache for performance
"""

from typing import Any, Dict, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Body, status
from fastapi.responses import JSONResponse
import logfire

from ...models.task_models import (
    Task,
    TaskList,
    TaskStats,
    TaskFilter,
    TaskStatus,
    TaskPriority,
    TaskType,
    TaskComplexity
)
from ...services.taskmaster_service import TaskMasterService
from ...core.cache import get_cache_service
from ...core.exceptions import (
    NotFoundError,
    ValidationError,
    ConflictError
)

# Create router
router = APIRouter(prefix="/tasks", tags=["TaskMaster AI"])


async def get_taskmaster_service() -> TaskMasterService:
    """Dependency to get TaskMaster service instance."""
    cache_service = await get_cache_service()
    return TaskMasterService(cache_service)


@router.post("/", response_model=Task, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: Dict[str, Any] = Body(..., description="Task data"),
    validate_dependencies: bool = Query(True, description="Validate task dependencies"),
    taskmaster: TaskMasterService = Depends(get_taskmaster_service)
) -> Task:
    """
    Create a new task.

    Args:
        task_data: Task data including title, description, type, etc.
        validate_dependencies: Whether to validate task dependencies
        taskmaster: TaskMaster service instance

    Returns:
        Created task with generated ID and metadata

    Raises:
        400: Validation error
        409: Task with same ID already exists
    """
    with logfire.span("API create_task", task_title=task_data.get("title")):
        try:
            task = await taskmaster.create_task(task_data, validate_dependencies)

            logfire.info(
                "Task created via API",
                task_id=task.id,
                title=task.title,
                task_type=task.task_type
            )

            return task

        except ValidationError as e:
            logfire.warning("Task creation validation failed", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Validation failed",
                    "message": str(e),
                    "field": getattr(e, 'field', None)
                }
            )
        except ConflictError as e:
            logfire.warning("Task creation conflict", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "Conflict",
                    "message": str(e)
                }
            )


@router.get("/{task_id}", response_model=Task)
async def get_task(
    task_id: str,
    include_subtasks: bool = Query(True, description="Include subtasks in response"),
    taskmaster: TaskMasterService = Depends(get_taskmaster_service)
) -> Task:
    """
    Get a task by ID.

    Args:
        task_id: Task identifier
        include_subtasks: Whether to include subtasks
        taskmaster: TaskMaster service instance

    Returns:
        Task details with optional subtasks

    Raises:
        404: Task not found
    """
    with logfire.span("API get_task", task_id=task_id):
        try:
            task = await taskmaster.get_task(task_id, include_subtasks)

            logfire.debug("Task retrieved via API", task_id=task_id)
            return task

        except NotFoundError as e:
            logfire.warning("Task not found", task_id=task_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "Not found",
                    "message": str(e),
                    "task_id": task_id
                }
            )


@router.put("/{task_id}", response_model=Task)
async def update_task(
    task_id: str,
    updates: Dict[str, Any] = Body(..., description="Task updates"),
    validate_dependencies: bool = Query(True, description="Validate dependencies"),
    taskmaster: TaskMasterService = Depends(get_taskmaster_service)
) -> Task:
    """
    Update an existing task.

    Args:
        task_id: Task identifier
        updates: Dictionary of fields to update
        validate_dependencies: Whether to validate dependencies
        taskmaster: TaskMaster service instance

    Returns:
        Updated task

    Raises:
        400: Validation error
        404: Task not found
    """
    with logfire.span("API update_task", task_id=task_id):
        try:
            task = await taskmaster.update_task(task_id, updates, validate_dependencies)

            logfire.info(
                "Task updated via API",
                task_id=task_id,
                updated_fields=list(updates.keys())
            )

            return task

        except NotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "Not found",
                    "message": str(e),
                    "task_id": task_id
                }
            )
        except ValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Validation failed",
                    "message": str(e),
                    "updates": updates
                }
            )


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: str,
    cascade: bool = Query(False, description="Delete subtasks as well"),
    taskmaster: TaskMasterService = Depends(get_taskmaster_service)
):
    """
    Delete a task.

    Args:
        task_id: Task identifier
        cascade: Whether to delete subtasks as well
        taskmaster: TaskMaster service instance

    Raises:
        404: Task not found
        409: Task has subtasks and cascade is False
    """
    with logfire.span("API delete_task", task_id=task_id):
        try:
            await taskmaster.delete_task(task_id, cascade)

            logfire.info("Task deleted via API", task_id=task_id, cascade=cascade)

        except NotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "Not found",
                    "message": str(e),
                    "task_id": task_id
                }
            )
        except ConflictError as e:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "Conflict",
                    "message": str(e),
                    "task_id": task_id
                }
            )


@router.get("/", response_model=TaskList)
async def list_tasks(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Tasks per page"),
    status: Optional[List[TaskStatus]] = Query(None, description="Filter by status"),
    priority: Optional[List[TaskPriority]] = Query(None, description="Filter by priority"),
    task_type: Optional[List[TaskType]] = Query(None, description="Filter by type"),
    assigned_to: Optional[str] = Query(None, description="Filter by assignee"),
    search: Optional[str] = Query(None, description="Search in title/description"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    taskmaster: TaskMasterService = Depends(get_taskmaster_service)
) -> TaskList:
    """
    List tasks with filtering, pagination, and sorting.

    Args:
        page: Page number (1-based)
        page_size: Number of tasks per page
        status: Filter by task status
        priority: Filter by priority level
        task_type: Filter by task type
        assigned_to: Filter by assignee
        search: Search text in title and description
        sort_by: Field to sort by
        sort_order: Sort order (asc/desc)
        taskmaster: TaskMaster service instance

    Returns:
        Paginated list of tasks with metadata
    """
    with logfire.span("API list_tasks", page=page, page_size=page_size):
        # Build filters
        filters = TaskFilter(
            status=status,
            priority=priority,
            task_type=task_type,
            assigned_to=assigned_to,
            search_text=search
        )

        task_list = await taskmaster.list_tasks(
            filters=filters,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order
        )

        logfire.info(
            "Tasks listed via API",
            page=page,
            page_size=page_size,
            total_count=task_list.total_count
        )

        return task_list


@router.get("/search", response_model=List[Task])
async def search_tasks(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    task_type: Optional[List[TaskType]] = Query(None, description="Filter by type"),
    status: Optional[List[TaskStatus]] = Query(None, description="Filter by status"),
    taskmaster: TaskMasterService = Depends(get_taskmaster_service)
) -> List[Task]:
    """
    Search tasks by text query.

    Args:
        q: Search query string
        limit: Maximum number of results
        task_type: Filter by task type
        status: Filter by status
        taskmaster: TaskMaster service instance

    Returns:
        List of matching tasks
    """
    with logfire.span("API search_tasks", query=q, limit=limit):
        filters = TaskFilter(
            task_type=task_type,
            status=status,
            search_text=q
        )

        results = await taskmaster.search_tasks(q, filters, limit)

        logfire.info(
            "Task search completed via API",
            query=q,
            results_count=len(results)
        )

        return results


@router.patch("/{task_id}/status", response_model=Task)
async def update_task_status(
    task_id: str,
    new_status: TaskStatus = Body(..., description="New task status"),
    notes: Optional[str] = Body(None, description="Status change notes"),
    taskmaster: TaskMasterService = Depends(get_taskmaster_service)
) -> Task:
    """
    Update task status.

    Args:
        task_id: Task identifier
        new_status: New task status
        notes: Optional status change notes
        taskmaster: TaskMaster service instance

    Returns:
        Updated task

    Raises:
        404: Task not found
    """
    with logfire.span("API update_task_status", task_id=task_id, new_status=new_status):
        try:
            task = await taskmaster.update_task_status(task_id, new_status, notes)

            logfire.info(
                "Task status updated via API",
                task_id=task_id,
                new_status=new_status
            )

            return task

        except NotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "Not found",
                    "message": str(e),
                    "task_id": task_id
                }
            )


@router.patch("/{task_id}/progress", response_model=Task)
async def update_task_progress(
    task_id: str,
    completion_percentage: float = Body(..., ge=0, le=100, description="Completion percentage"),
    notes: Optional[str] = Body(None, description="Progress notes"),
    taskmaster: TaskMasterService = Depends(get_taskmaster_service)
) -> Task:
    """
    Update task completion progress.

    Args:
        task_id: Task identifier
        completion_percentage: New completion percentage (0-100)
        notes: Optional progress notes
        taskmaster: TaskMaster service instance

    Returns:
        Updated task

    Raises:
        404: Task not found
    """
    with logfire.span("API update_task_progress",
                     task_id=task_id, completion=completion_percentage):
        try:
            task = await taskmaster.update_task_progress(
                task_id, completion_percentage, notes
            )

            logfire.info(
                "Task progress updated via API",
                task_id=task_id,
                completion_percentage=completion_percentage
            )

            return task

        except NotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "Not found",
                    "message": str(e),
                    "task_id": task_id
                }
            )


@router.post("/{task_id}/dependencies", status_code=status.HTTP_201_CREATED)
async def add_task_dependency(
    task_id: str,
    depends_on_id: str = Body(..., description="Task ID this task depends on"),
    dependency_type: str = Body("blocks", description="Type of dependency"),
    taskmaster: TaskMasterService = Depends(get_taskmaster_service)
) -> Dict[str, Any]:
    """
    Add a dependency between tasks.

    Args:
        task_id: Task that depends on another
        depends_on_id: Task that is depended upon
        dependency_type: Type of dependency relationship
        taskmaster: TaskMaster service instance

    Returns:
        Success confirmation

    Raises:
        404: Task not found
        409: Dependency would create a cycle
    """
    with logfire.span("API add_task_dependency",
                     task_id=task_id, depends_on_id=depends_on_id):
        try:
            success = await taskmaster.add_task_dependency(
                task_id, depends_on_id, dependency_type
            )

            logfire.info(
                "Task dependency added via API",
                task_id=task_id,
                depends_on_id=depends_on_id
            )

            return {
                "message": "Dependency added successfully",
                "task_id": task_id,
                "depends_on_id": depends_on_id,
                "dependency_type": dependency_type
            }

        except NotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "Not found",
                    "message": str(e)
                }
            )
        except ConflictError as e:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "Conflict",
                    "message": str(e)
                }
            )


@router.delete("/{task_id}/dependencies/{depends_on_id}")
async def remove_task_dependency(
    task_id: str,
    depends_on_id: str,
    taskmaster: TaskMasterService = Depends(get_taskmaster_service)
) -> Dict[str, Any]:
    """
    Remove a dependency between tasks.

    Args:
        task_id: Task to remove dependency from
        depends_on_id: Dependency to remove
        taskmaster: TaskMaster service instance

    Returns:
        Success confirmation

    Raises:
        404: Task not found
    """
    with logfire.span("API remove_task_dependency",
                     task_id=task_id, depends_on_id=depends_on_id):
        try:
            removed = await taskmaster.remove_task_dependency(task_id, depends_on_id)

            if removed:
                logfire.info(
                    "Task dependency removed via API",
                    task_id=task_id,
                    depends_on_id=depends_on_id
                )
                return {
                    "message": "Dependency removed successfully",
                    "task_id": task_id,
                    "depends_on_id": depends_on_id
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "error": "Dependency not found",
                        "message": f"No dependency found between {task_id} and {depends_on_id}"
                    }
                )

        except NotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "Not found",
                    "message": str(e)
                }
            )


@router.get("/{task_id}/complexity", response_model=Dict[str, Any])
async def analyze_task_complexity(
    task_id: str,
    recalculate: bool = Query(False, description="Force recalculation"),
    taskmaster: TaskMasterService = Depends(get_taskmaster_service)
) -> Dict[str, Any]:
    """
    Analyze task complexity with detailed breakdown.

    Args:
        task_id: Task identifier
        recalculate: Whether to force recalculation
        taskmaster: TaskMaster service instance

    Returns:
        Complexity analysis with score, category, and recommendations

    Raises:
        404: Task not found
    """
    with logfire.span("API analyze_task_complexity", task_id=task_id):
        try:
            analysis = await taskmaster.analyze_task_complexity(task_id, recalculate)

            logfire.info(
                "Task complexity analyzed via API",
                task_id=task_id,
                complexity_score=analysis["complexity_score"]
            )

            return analysis

        except NotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "Not found",
                    "message": str(e),
                    "task_id": task_id
                }
            )


@router.get("/statistics", response_model=TaskStats)
async def get_task_statistics(
    status: Optional[List[TaskStatus]] = Query(None, description="Filter by status"),
    priority: Optional[List[TaskPriority]] = Query(None, description="Filter by priority"),
    task_type: Optional[List[TaskType]] = Query(None, description="Filter by type"),
    assigned_to: Optional[str] = Query(None, description="Filter by assignee"),
    taskmaster: TaskMasterService = Depends(get_taskmaster_service)
) -> TaskStats:
    """
    Get task statistics and analytics.

    Args:
        status: Filter by task status
        priority: Filter by priority level
        task_type: Filter by task type
        assigned_to: Filter by assignee
        taskmaster: TaskMaster service instance

    Returns:
        Comprehensive task statistics and analytics
    """
    with logfire.span("API get_task_statistics"):
        filters = TaskFilter(
            status=status,
            priority=priority,
            task_type=task_type,
            assigned_to=assigned_to
        )

        stats = await taskmaster.get_task_statistics(filters)

        logfire.info(
            "Task statistics retrieved via API",
            total_tasks=stats.total_tasks,
            completion_rate=stats.completion_rate
        )

        return stats


@router.get("/service/metrics", response_model=Dict[str, Any])
async def get_service_metrics(
    taskmaster: TaskMasterService = Depends(get_taskmaster_service)
) -> Dict[str, Any]:
    """
    Get TaskMaster service performance metrics.

    Args:
        taskmaster: TaskMaster service instance

    Returns:
        Service performance metrics and statistics
    """
    with logfire.span("API get_service_metrics"):
        metrics = await taskmaster.get_service_metrics()

        logfire.info(
            "Service metrics retrieved via API",
            total_operations=metrics["total_operations"]
        )

        return metrics


@router.get("/enums", response_model=Dict[str, List[str]])
async def get_task_enums() -> Dict[str, List[str]]:
    """
    Get available task enumeration values.

    Returns:
        Dictionary of available enum values for task fields
    """
    return {
        "statuses": [status.value for status in TaskStatus],
        "priorities": [priority.value for priority in TaskPriority],
        "types": [task_type.value for task_type in TaskType],
        "complexities": [complexity.value for complexity in TaskComplexity]
    }


# Health check endpoint for TaskMaster service
@router.get("/health", response_model=Dict[str, Any])
async def taskmaster_health_check(
    taskmaster: TaskMasterService = Depends(get_taskmaster_service)
) -> Dict[str, Any]:
    """
    Health check for TaskMaster service.

    Args:
        taskmaster: TaskMaster service instance

    Returns:
        Service health status and metrics
    """
    with logfire.span("API taskmaster_health_check"):
        try:
            metrics = await taskmaster.get_service_metrics()

            health_status = {
                "status": "healthy",
                "service": "TaskMaster AI",
                "timestamp": datetime.utcnow().isoformat(),
                "metrics": {
                    "total_operations": metrics["total_operations"],
                    "cache_hit_rate": metrics["cache_metrics"]["hit_rate"],
                    "complexity_cache_size": metrics["complexity_cache_size"]
                }
            }

            return health_status

        except Exception as e:
            logfire.error("TaskMaster health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "service": "TaskMaster AI",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
