#!/usr/bin/env python3
"""
Task Master MCP Server

A comprehensive task management and orchestration server implementing the MCP protocol.
Provides intelligent task lifecycle management, dependency resolution, complexity analysis,
and real-time collaboration features for AI-enhanced development workflows.

This implementation follows DevQ.ai standards with standard MCP library integration,
comprehensive error handling, performance optimization, and full observability.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
import sys

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

try:
    from mcp import types
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from pydantic import BaseModel, Field, field_validator
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Please ensure mcp and pydantic are installed")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TaskStatus:
    """Task status constants"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"
    DEFERRED = "deferred"
    CANCELLED = "cancelled"


class TaskPriority:
    """Task priority constants"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TaskModel(BaseModel):
    """Pydantic model for task validation"""
    id: str
    title: str
    description: str
    status: str = TaskStatus.PENDING
    priority: str = TaskPriority.MEDIUM
    dependencies: List[str] = Field(default_factory=list)
    subtasks: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    assigned_to: Optional[str] = None
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    complexity_score: Optional[int] = None
    progress_percentage: int = 0
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        valid_statuses = [TaskStatus.PENDING, TaskStatus.IN_PROGRESS, TaskStatus.DONE,
                         TaskStatus.BLOCKED, TaskStatus.DEFERRED, TaskStatus.CANCELLED]
        if v not in valid_statuses:
            raise ValueError(f"Status must be one of: {valid_statuses}")
        return v

    @field_validator('priority')
    @classmethod
    def validate_priority(cls, v):
        valid_priorities = [TaskPriority.LOW, TaskPriority.MEDIUM, TaskPriority.HIGH, TaskPriority.CRITICAL]
        if v not in valid_priorities:
            raise ValueError(f"Priority must be one of: {valid_priorities}")
        return v

    @field_validator('progress_percentage')
    @classmethod
    def validate_progress(cls, v):
        if not 0 <= v <= 100:
            raise ValueError("Progress percentage must be between 0 and 100")
        return v


class TaskStorage:
    """In-memory task storage with persistence to JSON file"""

    def __init__(self, storage_file: str = "tasks.json"):
        self.storage_file = Path(storage_file)
        self.tasks: Dict[str, TaskModel] = {}
        self.load_tasks()

    def load_tasks(self):
        """Load tasks from storage file"""
        if self.storage_file.exists():
            try:
                with open(self.storage_file, 'r') as f:
                    data = json.load(f)
                    for task_id, task_data in data.items():
                        # Convert datetime strings back to datetime objects
                        for date_field in ['created_at', 'updated_at', 'due_date', 'completed_at']:
                            if task_data.get(date_field):
                                task_data[date_field] = datetime.fromisoformat(task_data[date_field])
                        self.tasks[task_id] = TaskModel(**task_data)
                logger.info(f"Loaded {len(self.tasks)} tasks from {self.storage_file}")
            except Exception as e:
                logger.error(f"Error loading tasks from {self.storage_file}: {e}")

    def save_tasks(self):
        """Save tasks to storage file"""
        try:
            data = {}
            for task_id, task in self.tasks.items():
                task_dict = task.model_dump()
                # Convert datetime objects to ISO strings for JSON serialization
                for date_field in ['created_at', 'updated_at', 'due_date', 'completed_at']:
                    if task_dict.get(date_field):
                        task_dict[date_field] = task_dict[date_field].isoformat()
                data[task_id] = task_dict

            with open(self.storage_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            logger.debug(f"Saved {len(self.tasks)} tasks to {self.storage_file}")
        except Exception as e:
            logger.error(f"Error saving tasks to {self.storage_file}: {e}")

    async def create_task(self, task_data: Dict[str, Any]) -> str:
        """Create a new task"""
        task_id = str(uuid.uuid4())
        task_data['id'] = task_id
        task = TaskModel(**task_data)
        self.tasks[task_id] = task
        self.save_tasks()
        return task_id

    async def get_task(self, task_id: str) -> Optional[TaskModel]:
        """Get a task by ID"""
        return self.tasks.get(task_id)

    async def update_task(self, task_id: str, updates: Dict[str, Any]) -> bool:
        """Update a task"""
        if task_id not in self.tasks:
            return False

        task = self.tasks[task_id]
        update_data = task.model_dump()
        update_data.update(updates)
        update_data['updated_at'] = datetime.now()

        # Set completed_at when status changes to done
        if updates.get('status') == TaskStatus.DONE and task.status != TaskStatus.DONE:
            update_data['completed_at'] = datetime.now()
            update_data['progress_percentage'] = 100

        self.tasks[task_id] = TaskModel(**update_data)
        self.save_tasks()
        return True

    async def delete_task(self, task_id: str) -> bool:
        """Delete a task"""
        if task_id in self.tasks:
            del self.tasks[task_id]
            self.save_tasks()
            return True
        return False

    async def list_tasks(self,
                        status: Optional[str] = None,
                        priority: Optional[str] = None,
                        assigned_to: Optional[str] = None,
                        tags: Optional[List[str]] = None,
                        limit: Optional[int] = None) -> List[TaskModel]:
        """List tasks with optional filtering"""
        filtered_tasks = list(self.tasks.values())

        if status:
            filtered_tasks = [t for t in filtered_tasks if t.status == status]
        if priority:
            filtered_tasks = [t for t in filtered_tasks if t.priority == priority]
        if assigned_to:
            filtered_tasks = [t for t in filtered_tasks if t.assigned_to == assigned_to]
        if tags:
            filtered_tasks = [t for t in filtered_tasks if any(tag in t.tags for tag in tags)]

        # Sort by priority and creation date
        priority_order = {TaskPriority.CRITICAL: 4, TaskPriority.HIGH: 3,
                         TaskPriority.MEDIUM: 2, TaskPriority.LOW: 1}
        filtered_tasks.sort(key=lambda t: (priority_order.get(t.priority, 0), t.created_at), reverse=True)

        if limit:
            filtered_tasks = filtered_tasks[:limit]

        return filtered_tasks


class TaskAnalyzer:
    """Task complexity analysis and recommendations"""

    @staticmethod
    def analyze_complexity(task: TaskModel, dependencies: List[TaskModel] = None) -> int:
        """Analyze task complexity on a scale of 1-10"""
        complexity = 1

        # Base complexity from description length and keywords
        description_words = len(task.description.split())
        if description_words > 50:
            complexity += 2
        elif description_words > 20:
            complexity += 1

        # Complexity keywords
        high_complexity_keywords = [
            'integrate', 'implement', 'design', 'architecture', 'algorithm',
            'optimization', 'security', 'authentication', 'database', 'api',
            'testing', 'performance', 'scalability', 'deployment'
        ]

        description_lower = task.description.lower()
        keyword_matches = sum(1 for keyword in high_complexity_keywords if keyword in description_lower)
        complexity += min(keyword_matches, 3)

        # Dependencies add complexity
        if dependencies:
            complexity += min(len(dependencies), 2)

        # Subtasks add complexity
        if task.subtasks:
            complexity += min(len(task.subtasks) // 2, 2)

        # Estimated hours factor
        if task.estimated_hours:
            if task.estimated_hours > 20:
                complexity += 2
            elif task.estimated_hours > 8:
                complexity += 1

        return min(complexity, 10)

    @staticmethod
    def get_recommendations(task: TaskModel) -> List[str]:
        """Get recommendations for task completion"""
        recommendations = []

        if task.complexity_score and task.complexity_score >= 8:
            recommendations.append("Consider breaking this high-complexity task into smaller subtasks")

        if not task.estimated_hours:
            recommendations.append("Add time estimation to improve project planning")

        if task.dependencies:
            recommendations.append("Verify all dependencies are completed before starting")

        if task.priority == TaskPriority.HIGH and not task.assigned_to:
            recommendations.append("Assign this high-priority task to ensure timely completion")

        if task.due_date and task.due_date < datetime.now():
            recommendations.append("This task is overdue - consider rescheduling or prioritizing")

        return recommendations


class TaskMasterMCP:
    """Main MCP server class for task management"""

    def __init__(self):
        self.storage = TaskStorage()
        self.analyzer = TaskAnalyzer()
        self.server = Server("task-master")
        self._setup_handlers()
        logger.info("TaskMaster MCP Server initialized")

    def _setup_handlers(self):
        """Set up MCP tool handlers"""

        @self.server.list_tools()
        async def list_tools() -> List[types.Tool]:
            """List all available tools"""
            return [
                types.Tool(
                    name="create_task",
                    description="Create a new task with comprehensive details",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Task title"},
                            "description": {"type": "string", "description": "Detailed task description"},
                            "priority": {"type": "string", "enum": ["low", "medium", "high", "critical"], "default": "medium"},
                            "assigned_to": {"type": "string", "description": "Person assigned to the task"},
                            "estimated_hours": {"type": "number", "description": "Estimated completion time in hours"},
                            "due_date": {"type": "string", "description": "Due date in ISO format"},
                            "tags": {"type": "array", "items": {"type": "string"}, "description": "List of tags"},
                            "dependencies": {"type": "array", "items": {"type": "string"}, "description": "List of dependency task IDs"}
                        },
                        "required": ["title", "description"]
                    }
                ),
                types.Tool(
                    name="get_task",
                    description="Get detailed information about a specific task",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "task_id": {"type": "string", "description": "Unique identifier of the task"},
                            "include_dependencies": {"type": "boolean", "default": False, "description": "Include dependency details"}
                        },
                        "required": ["task_id"]
                    }
                ),
                types.Tool(
                    name="update_task",
                    description="Update an existing task's properties",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "task_id": {"type": "string", "description": "Unique identifier of the task"},
                            "title": {"type": "string", "description": "New task title"},
                            "description": {"type": "string", "description": "New task description"},
                            "status": {"type": "string", "enum": ["pending", "in_progress", "done", "blocked", "deferred", "cancelled"]},
                            "priority": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                            "assigned_to": {"type": "string", "description": "Person assigned to the task"},
                            "estimated_hours": {"type": "number", "description": "Estimated completion time"},
                            "actual_hours": {"type": "number", "description": "Actual time spent"},
                            "progress_percentage": {"type": "integer", "minimum": 0, "maximum": 100},
                            "due_date": {"type": "string", "description": "Due date in ISO format"},
                            "tags": {"type": "array", "items": {"type": "string"}}
                        },
                        "required": ["task_id"]
                    }
                ),
                types.Tool(
                    name="delete_task",
                    description="Delete a task permanently",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "task_id": {"type": "string", "description": "Unique identifier of the task to delete"}
                        },
                        "required": ["task_id"]
                    }
                ),
                types.Tool(
                    name="list_tasks",
                    description="List tasks with optional filtering and pagination",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "status": {"type": "string", "enum": ["pending", "in_progress", "done", "blocked", "deferred", "cancelled"]},
                            "priority": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                            "assigned_to": {"type": "string", "description": "Filter by assigned person"},
                            "tags": {"type": "array", "items": {"type": "string"}, "description": "Filter by tags"},
                            "limit": {"type": "integer", "default": 50, "description": "Maximum number of tasks"},
                            "include_completed": {"type": "boolean", "default": True}
                        }
                    }
                ),
                types.Tool(
                    name="add_dependency",
                    description="Add a dependency relationship between tasks",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "task_id": {"type": "string", "description": "Task that depends on another"},
                            "dependency_id": {"type": "string", "description": "Task that must be completed first"}
                        },
                        "required": ["task_id", "dependency_id"]
                    }
                ),
                types.Tool(
                    name="remove_dependency",
                    description="Remove a dependency relationship between tasks",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "task_id": {"type": "string", "description": "Task to remove dependency from"},
                            "dependency_id": {"type": "string", "description": "Dependency task to remove"}
                        },
                        "required": ["task_id", "dependency_id"]
                    }
                ),
                types.Tool(
                    name="analyze_task_complexity",
                    description="Analyze and return task complexity with recommendations",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "task_id": {"type": "string", "description": "Unique identifier of the task"},
                            "recalculate": {"type": "boolean", "default": False, "description": "Recalculate complexity score"}
                        },
                        "required": ["task_id"]
                    }
                ),
                types.Tool(
                    name="get_task_statistics",
                    description="Get comprehensive task statistics and analytics",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "date_range": {"type": "string", "enum": ["last_7_days", "last_30_days", "last_90_days"]},
                            "group_by": {"type": "string", "enum": ["status", "priority", "assigned_to"], "default": "status"}
                        }
                    }
                ),
                types.Tool(
                    name="search_tasks",
                    description="Search tasks by text query in specified fields",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query string"},
                            "search_fields": {"type": "array", "items": {"type": "string", "enum": ["title", "description", "tags"]}, "default": ["title", "description", "tags"]},
                            "limit": {"type": "integer", "default": 20, "description": "Maximum results"}
                        },
                        "required": ["query"]
                    }
                ),
                types.Tool(
                    name="update_progress",
                    description="Update task progress percentage with optional notes",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "task_id": {"type": "string", "description": "Unique identifier of the task"},
                            "progress_percentage": {"type": "integer", "minimum": 0, "maximum": 100},
                            "notes": {"type": "string", "description": "Optional progress notes"}
                        },
                        "required": ["task_id", "progress_percentage"]
                    }
                ),
                types.Tool(
                    name="get_recommendations",
                    description="Get AI-powered recommendations for task completion",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "task_id": {"type": "string", "description": "Unique identifier of the task"}
                        },
                        "required": ["task_id"]
                    }
                )
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
            """Handle tool calls"""
            try:
                if name == "create_task":
                    result = await self.create_task(**arguments)
                elif name == "get_task":
                    result = await self.get_task(**arguments)
                elif name == "update_task":
                    result = await self.update_task(**arguments)
                elif name == "delete_task":
                    result = await self.delete_task(**arguments)
                elif name == "list_tasks":
                    result = await self.list_tasks(**arguments)
                elif name == "add_dependency":
                    result = await self.add_dependency(**arguments)
                elif name == "remove_dependency":
                    result = await self.remove_dependency(**arguments)
                elif name == "analyze_task_complexity":
                    result = await self.analyze_task_complexity(**arguments)
                elif name == "get_task_statistics":
                    result = await self.get_task_statistics(**arguments)
                elif name == "search_tasks":
                    result = await self.search_tasks(**arguments)
                elif name == "update_progress":
                    result = await self.update_progress(**arguments)
                elif name == "get_recommendations":
                    result = await self.get_recommendations(**arguments)
                else:
                    result = {"success": False, "error": f"Unknown tool: {name}"}

                return [types.TextContent(type="text", text=json.dumps(result, indent=2, default=str))]

            except Exception as e:
                logger.error(f"Error executing tool {name}: {e}")
                error_result = {"success": False, "error": str(e)}
                return [types.TextContent(type="text", text=json.dumps(error_result, indent=2))]

    # Tool implementation methods
    async def create_task(self, title: str, description: str, **kwargs) -> Dict[str, Any]:
        """Create a new task with comprehensive details"""
        try:
            task_data = {
                'title': title,
                'description': description,
                'priority': kwargs.get('priority', TaskPriority.MEDIUM),
                'tags': kwargs.get('tags', []),
                'dependencies': kwargs.get('dependencies', [])
            }

            # Add optional fields if provided
            for field in ['assigned_to', 'estimated_hours']:
                if kwargs.get(field):
                    task_data[field] = kwargs[field]

            if kwargs.get('due_date'):
                task_data['due_date'] = datetime.fromisoformat(kwargs['due_date'])

            task_id = await self.storage.create_task(task_data)
            task = await self.storage.get_task(task_id)

            # Analyze complexity
            task.complexity_score = self.analyzer.analyze_complexity(task)
            await self.storage.update_task(task_id, {'complexity_score': task.complexity_score})

            logger.info(f"Created task {task_id}: {title}")
            return {
                'success': True,
                'task_id': task_id,
                'complexity_score': task.complexity_score,
                'message': f'Task "{title}" created successfully'
            }

        except Exception as e:
            logger.error(f"Error creating task: {e}")
            return {'success': False, 'error': str(e)}

    async def get_task(self, task_id: str, include_dependencies: bool = False) -> Dict[str, Any]:
        """Get detailed information about a specific task"""
        try:
            task = await self.storage.get_task(task_id)
            if not task:
                return {'success': False, 'error': f'Task {task_id} not found'}

            result = task.model_dump()
            result['success'] = True

            # Convert datetime objects to ISO strings
            for field in ['created_at', 'updated_at', 'due_date', 'completed_at']:
                if result.get(field):
                    result[field] = result[field].isoformat()

            if include_dependencies:
                dependency_details = []
                if task.dependencies:
                    for dep_id in task.dependencies:
                        dep_task = await self.storage.get_task(dep_id)
                        if dep_task:
                            dependency_details.append({
                                'id': dep_id,
                                'title': dep_task.title,
                                'status': dep_task.status
                            })
                result['dependency_details'] = dependency_details

            return result

        except Exception as e:
            logger.error(f"Error getting task {task_id}: {e}")
            return {'success': False, 'error': str(e)}

    async def update_task(self, task_id: str, **kwargs) -> Dict[str, Any]:
        """Update an existing task's properties"""
        try:
            task = await self.storage.get_task(task_id)
            if not task:
                return {'success': False, 'error': f'Task {task_id} not found'}

            updates = {}
            for field in ['title', 'description', 'status', 'priority', 'assigned_to',
                         'estimated_hours', 'actual_hours', 'progress_percentage', 'tags']:
                if kwargs.get(field) is not None:
                    updates[field] = kwargs[field]

            if kwargs.get('due_date'):
                updates['due_date'] = datetime.fromisoformat(kwargs['due_date'])

            success = await self.storage.update_task(task_id, updates)
            if success:
                logger.info(f"Updated task {task_id}")
                return {'success': True, 'message': f'Task {task_id} updated successfully'}
            else:
                return {'success': False, 'error': 'Failed to update task'}

        except Exception as e:
            logger.error(f"Error updating task {task_id}: {e}")
            return {'success': False, 'error': str(e)}

    async def delete_task(self, task_id: str) -> Dict[str, Any]:
        """Delete a task permanently"""
        try:
            task = await self.storage.get_task(task_id)
            if not task:
                return {'success': False, 'error': f'Task {task_id} not found'}

            # Check if other tasks depend on this task
            all_tasks = await self.storage.list_tasks()
            dependent_tasks = [t for t in all_tasks if task_id in t.dependencies]

            if dependent_tasks:
                dependent_ids = [t.id for t in dependent_tasks]
                return {
                    'success': False,
                    'error': f'Cannot delete task {task_id}. It has dependencies: {dependent_ids}'
                }

            success = await self.storage.delete_task(task_id)
            if success:
                logger.info(f"Deleted task {task_id}")
                return {'success': True, 'message': f'Task {task_id} deleted successfully'}
            else:
                return {'success': False, 'error': 'Failed to delete task'}

        except Exception as e:
            logger.error(f"Error deleting task {task_id}: {e}")
            return {'success': False, 'error': str(e)}

    async def list_tasks(self, **kwargs) -> Dict[str, Any]:
        """List tasks with optional filtering and pagination"""
        try:
            tasks = await self.storage.list_tasks(
                status=kwargs.get('status'),
                priority=kwargs.get('priority'),
                assigned_to=kwargs.get('assigned_to'),
                tags=kwargs.get('tags'),
                limit=kwargs.get('limit', 50)
            )

            if not kwargs.get('include_completed', True):
                tasks = [t for t in tasks if t.status != TaskStatus.DONE]

            result = {
                'success': True,
                'count': len(tasks),
                'tasks': []
            }

            for task in tasks:
                task_dict = task.model_dump()
                # Convert datetime objects to ISO strings
                for field in ['created_at', 'updated_at', 'due_date', 'completed_at']:
                    if task_dict.get(field):
                        task_dict[field] = task_dict[field].isoformat()
                result['tasks'].append(task_dict)

            return result

        except Exception as e:
            logger.error(f"Error listing tasks: {e}")
            return {'success': False, 'error': str(e)}

    async def add_dependency(self, task_id: str, dependency_id: str) -> Dict[str, Any]:
        """Add a dependency relationship between tasks"""
        try:
            task = await self.storage.get_task(task_id)
            dependency = await self.storage.get_task(dependency_id)

            if not task:
                return {'success': False, 'error': f'Task {task_id} not found'}
            if not dependency:
                return {'success': False, 'error': f'Dependency task {dependency_id} not found'}

            # Check for circular dependencies
            if await self._would_create_cycle(task_id, dependency_id):
                return {'success': False, 'error': 'Adding this dependency would create a circular dependency'}

            if dependency_id not in task.dependencies:
                new_dependencies = task.dependencies + [dependency_id]
                await self.storage.update_task(task_id, {'dependencies': new_dependencies})
                logger.info(f"Added dependency {dependency_id} to task {task_id}")
                return {'success': True, 'message': 'Dependency added successfully'}
            else:
                return {'success': False, 'error': 'Dependency already exists'}

        except Exception as e:
            logger.error(f"Error adding dependency: {e}")
            return {'success': False, 'error': str(e)}

    async def remove_dependency(self, task_id: str, dependency_id: str) -> Dict[str, Any]:
        """Remove a dependency relationship between tasks"""
        try:
            task = await self.storage.get_task(task_id)
            if not task:
                return {'success': False, 'error': f'Task {task_id} not found'}

            if dependency_id in task.dependencies:
                new_dependencies = [d for d in task.dependencies if d != dependency_id]
                await self.storage.update_task(task_id, {'dependencies': new_dependencies})
                logger.info(f"Removed dependency {dependency_id} from task {task_id}")
                return {'success': True, 'message': 'Dependency removed successfully'}
            else:
                return {'success': False, 'error': 'Dependency not found'}

        except Exception as e:
            logger.error(f"Error removing dependency: {e}")
            return {'success': False, 'error': str(e)}

    async def analyze_task_complexity(self, task_id: str, recalculate: bool = False) -> Dict[str, Any]:
        """Analyze and return task complexity with recommendations"""
        try:
            task = await self.storage.get_task(task_id)
            if not task:
                return {'success': False, 'error': f'Task {task_id} not found'}

            # Get dependency tasks for complexity calculation
            dependency_tasks = []
            for dep_id in task.dependencies:
                dep_task = await self.storage.get_task(dep_id)
                if dep_task:
                    dependency_tasks.append(dep_task)

            if recalculate or task.complexity_score is None:
                complexity = self.analyzer.analyze_complexity(task, dependency_tasks)
                await self.storage.update_task(task_id, {'complexity_score': complexity})
                task.complexity_score = complexity

            recommendations = self.analyzer.get_recommendations(task)

            return {
                'success': True,
                'task_id': task_id,
                'complexity_score': task.complexity_score,
                'complexity_level': self._get_complexity_level(task.complexity_score),
                'recommendations': recommendations,
                'analysis': {
                    'dependency_count': len(task.dependencies),
                    'subtask_count': len(task.subtasks),
                    'estimated_hours': task.estimated_hours,
                    'has_due_date': task.due_date is not None,
                    'is_assigned': task.assigned_to is not None
                }
            }

        except Exception as e:
            logger.error(f"Error analyzing task complexity: {e}")
            return {'success': False, 'error': str(e)}

    async def get_task_statistics(self, **kwargs) -> Dict[str, Any]:
        """Get comprehensive task statistics and analytics"""
        try:
            all_tasks = await self.storage.list_tasks()
            date_range = kwargs.get('date_range')
            group_by = kwargs.get('group_by', 'status')

            # Apply date filtering
            if date_range:
                cutoff_date = self._get_cutoff_date(date_range)
                if cutoff_date:
                    all_tasks = [t for t in all_tasks if t.created_at >= cutoff_date]

            # Calculate basic statistics
            total_tasks = len(all_tasks)
            completed_tasks = len([t for t in all_tasks if t.status == TaskStatus.DONE])
            in_progress_tasks = len([t for t in all_tasks if t.status == TaskStatus.IN_PROGRESS])
            overdue_tasks = len([t for t in all_tasks if t.due_date and t.due_date < datetime.now() and t.status != TaskStatus.DONE])

            # Group by specified field
            grouped_stats = {}
            for task in all_tasks:
                if group_by == "status":
                    key = task.status
                elif group_by == "priority":
                    key = task.priority
                elif group_by == "assigned_to":
                    key = task.assigned_to or "unassigned"
                else:
                    key = "all"

                if key not in grouped_stats:
                    grouped_stats[key] = {
                        'count': 0,
                        'completed': 0,
                        'total_hours': 0,
                        'avg_complexity': 0
                    }

                grouped_stats[key]['count'] += 1
                if task.status == TaskStatus.DONE:
                    grouped_stats[key]['completed'] += 1
                if task.estimated_hours:
                    grouped_stats[key]['total_hours'] += task.estimated_hours
                if task.complexity_score:
                    grouped_stats[key]['avg_complexity'] += task.complexity_score

            # Calculate averages
            for stats in grouped_stats.values():
                if stats['count'] > 0:
                    stats['completion_rate'] = stats['completed'] / stats['count'] * 100
                    stats['avg_complexity'] = stats['avg_complexity'] / stats['count']
                else:
                    stats['completion_rate'] = 0

            return {
                'success': True,
                'date_range': date_range,
                'grouped_by': group_by,
                'summary': {
                    'total_tasks': total_tasks,
                    'completed_tasks': completed_tasks,
                    'in_progress_tasks': in_progress_tasks,
                    'overdue_tasks': overdue_tasks,
                    'completion_rate': (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
                },
                'grouped_statistics': grouped_stats
            }

        except Exception as e:
            logger.error(f"Error getting task statistics: {e}")
            return {'success': False, 'error': str(e)}

    async def search_tasks(self, query: str, **kwargs) -> Dict[str, Any]:
        """Search tasks by text query in specified fields"""
        try:
            search_fields = kwargs.get('search_fields', ['title', 'description', 'tags'])
            limit = kwargs.get('limit', 20)

            all_tasks = await self.storage.list_tasks()
            matching_tasks = []
            query_lower = query.lower()

            for task in all_tasks:
                match_score = 0

                if 'title' in search_fields and query_lower in task.title.lower():
                    match_score += 3
                if 'description' in search_fields and query_lower in task.description.lower():
                    match_score += 2
                if 'tags' in search_fields and any(query_lower in tag.lower() for tag in task.tags):
                    match_score += 1

                if match_score > 0:
                    task_dict = task.model_dump()
                    task_dict['match_score'] = match_score
                    # Convert datetime objects to ISO strings
                    for field in ['created_at', 'updated_at', 'due_date', 'completed_at']:
                        if task_dict.get(field):
                            task_dict[field] = task_dict[field].isoformat()
                    matching_tasks.append(task_dict)

            # Sort by match score (descending)
            matching_tasks.sort(key=lambda x: x['match_score'], reverse=True)

            if limit:
                matching_tasks = matching_tasks[:limit]

            return {
                'success': True,
                'query': query,
                'count': len(matching_tasks),
                'tasks': matching_tasks
            }

        except Exception as e:
            logger.error(f"Error searching tasks: {e}")
            return {'success': False, 'error': str(e)}

    async def update_progress(self, task_id: str, progress_percentage: int, notes: str = None, **kwargs) -> Dict[str, Any]:
        """Update task progress percentage with optional notes"""
        try:
            task = await self.storage.get_task(task_id)
            if not task:
                return {'success': False, 'error': f'Task {task_id} not found'}

            updates = {'progress_percentage': progress_percentage}
            notes = notes or kwargs.get('notes')

            # Auto-update status based on progress
            if progress_percentage == 100 and task.status != TaskStatus.DONE:
                updates['status'] = TaskStatus.DONE
            elif progress_percentage > 0 and task.status == TaskStatus.PENDING:
                updates['status'] = TaskStatus.IN_PROGRESS

            # Add notes to metadata
            if notes:
                metadata = task.metadata.copy()
                if 'progress_notes' not in metadata:
                    metadata['progress_notes'] = []
                metadata['progress_notes'].append({
                    'timestamp': datetime.now().isoformat(),
                    'progress': progress_percentage,
                    'notes': notes
                })
                updates['metadata'] = metadata

            success = await self.storage.update_task(task_id, updates)
            if success:
                logger.info(f"Updated progress for task {task_id} to {progress_percentage}%")
                return {
                    'success': True,
                    'progress_percentage': progress_percentage,
                    'status': updates.get('status', task.status),
                    'message': f'Progress updated to {progress_percentage}%'
                }
            else:
                return {'success': False, 'error': 'Failed to update progress'}

        except Exception as e:
            logger.error(f"Error updating progress for task {task_id}: {e}")
            return {'success': False, 'error': str(e)}

    async def get_recommendations(self, task_id: str) -> Dict[str, Any]:
        """Get AI-powered recommendations for task completion"""
        try:
            task = await self.storage.get_task(task_id)
            if not task:
                return {'success': False, 'error': f'Task {task_id} not found'}

            recommendations = self.analyzer.get_recommendations(task)

            return {
                'success': True,
                'task_id': task_id,
                'recommendations': recommendations,
                'task_info': {
                    'title': task.title,
                    'status': task.status,
                    'priority': task.priority,
                    'complexity_score': task.complexity_score,
                    'progress_percentage': task.progress_percentage
                }
            }

        except Exception as e:
            logger.error(f"Error getting recommendations for task {task_id}: {e}")
            return {'success': False, 'error': str(e)}

    # Helper methods
    async def _would_create_cycle(self, task_id: str, dependency_id: str) -> bool:
        """Check if adding a dependency would create a circular dependency"""
        visited = set()

        async def has_path_to_task(current_id: str, target_id: str) -> bool:
            if current_id == target_id:
                return True
            if current_id in visited:
                return False

            visited.add(current_id)
            current_task = await self.storage.get_task(current_id)
            if not current_task:
                return False

            for dep_id in current_task.dependencies:
                if await has_path_to_task(dep_id, target_id):
                    return True

            return False

        return await has_path_to_task(dependency_id, task_id)

    def _get_complexity_level(self, score: Optional[int]) -> str:
        """Convert complexity score to human-readable level"""
        if not score:
            return "unknown"
        elif score <= 3:
            return "low"
        elif score <= 6:
            return "medium"
        elif score <= 8:
            return "high"
        else:
            return "very_high"

    def _get_cutoff_date(self, date_range: str) -> Optional[datetime]:
        """Get cutoff date for filtering"""
        now = datetime.now()
        if date_range == "last_7_days":
            return now - timedelta(days=7)
        elif date_range == "last_30_days":
            return now - timedelta(days=30)
        elif date_range == "last_90_days":
            return now - timedelta(days=90)
        return None


def main():
    """Main entry point for the MCP server"""
    try:
        task_master = TaskMasterMCP()
        logger.info("Starting TaskMaster MCP Server...")

        # Run the server with stdio transport
        async def run_server():
            async with stdio_server() as (read_stream, write_stream):
                await task_master.server.run(
                    read_stream,
                    write_stream,
                    task_master.server.create_initialization_options()
                )

        asyncio.run(run_server())

    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise


if __name__ == "__main__":
    main()
