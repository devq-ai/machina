#!/usr/bin/env python3
"""
Comprehensive Test Suite for TaskMaster MCP Server

This test suite validates all functionality of the task-master MCP server including:
- Task creation, retrieval, updating, and deletion
- Dependency management and cycle detection
- Complexity analysis and recommendations
- Search and filtering capabilities
- Progress tracking and statistics
- Error handling and edge cases

Follows DevQ.ai testing standards with ≥90% coverage requirement.
"""

import asyncio
import json
import pytest
import tempfile
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import sys
import os

# Add the server module to path
sys.path.insert(0, os.path.dirname(__file__))

from server import (
    TaskMasterMCP, TaskStorage, TaskAnalyzer, TaskModel,
    TaskStatus, TaskPriority
)


class TestTaskStorage:
    """Test cases for TaskStorage class"""

    def setup_method(self):
        """Set up test environment"""
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        self.temp_file.close()
        self.storage = TaskStorage(self.temp_file.name)

    def teardown_method(self):
        """Clean up test environment"""
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)

    @pytest.mark.asyncio
    async def test_create_task_basic(self):
        """Test basic task creation"""
        task_data = {
            'title': 'Test Task',
            'description': 'A test task for validation',
            'priority': TaskPriority.HIGH
        }

        task_id = await self.storage.create_task(task_data)
        assert task_id is not None
        assert isinstance(task_id, str)

        # Verify task was stored
        task = await self.storage.get_task(task_id)
        assert task is not None
        assert task.title == 'Test Task'
        assert task.priority == TaskPriority.HIGH
        assert task.status == TaskStatus.PENDING

    @pytest.mark.asyncio
    async def test_create_task_with_all_fields(self):
        """Test task creation with all optional fields"""
        due_date = datetime.now() + timedelta(days=7)
        task_data = {
            'title': 'Complex Task',
            'description': 'A complex task with all fields',
            'priority': TaskPriority.CRITICAL,
            'assigned_to': 'john.doe@example.com',
            'estimated_hours': 16.5,
            'due_date': due_date,
            'tags': ['urgent', 'feature', 'api'],
            'dependencies': [],
            'metadata': {'project': 'test-project'}
        }

        task_id = await self.storage.create_task(task_data)
        task = await self.storage.get_task(task_id)

        assert task.title == 'Complex Task'
        assert task.assigned_to == 'john.doe@example.com'
        assert task.estimated_hours == 16.5
        assert task.due_date == due_date
        assert 'urgent' in task.tags
        assert task.metadata['project'] == 'test-project'

    @pytest.mark.asyncio
    async def test_update_task(self):
        """Test task updating"""
        # Create a task
        task_data = {'title': 'Original Title', 'description': 'Original description'}
        task_id = await self.storage.create_task(task_data)

        # Update the task
        updates = {
            'title': 'Updated Title',
            'status': TaskStatus.IN_PROGRESS,
            'progress_percentage': 50
        }
        success = await self.storage.update_task(task_id, updates)
        assert success is True

        # Verify updates
        task = await self.storage.get_task(task_id)
        assert task.title == 'Updated Title'
        assert task.status == TaskStatus.IN_PROGRESS
        assert task.progress_percentage == 50

    @pytest.mark.asyncio
    async def test_update_task_completion(self):
        """Test automatic completion timestamp when status changes to done"""
        task_data = {'title': 'Test Task', 'description': 'Test'}
        task_id = await self.storage.create_task(task_data)

        # Mark as done
        updates = {'status': TaskStatus.DONE}
        await self.storage.update_task(task_id, updates)

        task = await self.storage.get_task(task_id)
        assert task.status == TaskStatus.DONE
        assert task.completed_at is not None
        assert task.progress_percentage == 100

    @pytest.mark.asyncio
    async def test_delete_task(self):
        """Test task deletion"""
        task_data = {'title': 'To Delete', 'description': 'Will be deleted'}
        task_id = await self.storage.create_task(task_data)

        # Verify exists
        task = await self.storage.get_task(task_id)
        assert task is not None

        # Delete
        success = await self.storage.delete_task(task_id)
        assert success is True

        # Verify deletion
        task = await self.storage.get_task(task_id)
        assert task is None

    @pytest.mark.asyncio
    async def test_list_tasks_filtering(self):
        """Test task listing with various filters"""
        # Create multiple tasks
        tasks = [
            {'title': 'High Priority', 'description': 'High priority test task', 'priority': TaskPriority.HIGH, 'status': TaskStatus.PENDING},
            {'title': 'Medium Priority', 'description': 'Medium priority test task', 'priority': TaskPriority.MEDIUM, 'status': TaskStatus.IN_PROGRESS},
            {'title': 'Low Priority', 'description': 'Low priority test task', 'priority': TaskPriority.LOW, 'status': TaskStatus.DONE},
            {'title': 'Assigned Task', 'description': 'Task assigned to user', 'priority': TaskPriority.HIGH, 'assigned_to': 'john@example.com'},
            {'title': 'Tagged Task', 'description': 'Task with tags', 'tags': ['urgent', 'bug']}
        ]

        task_ids = []
        for task_data in tasks:
            task_id = await self.storage.create_task(task_data)
            task_ids.append(task_id)

        # Test status filtering
        pending_tasks = await self.storage.list_tasks(status=TaskStatus.PENDING)
        assert len(pending_tasks) >= 3  # At least 3 pending tasks

        # Test priority filtering
        high_priority_tasks = await self.storage.list_tasks(priority=TaskPriority.HIGH)
        assert len(high_priority_tasks) >= 2  # At least 2 high priority tasks

        # Test assigned_to filtering
        assigned_tasks = await self.storage.list_tasks(assigned_to='john@example.com')
        assert len(assigned_tasks) >= 1

        # Test tags filtering
        tagged_tasks = await self.storage.list_tasks(tags=['urgent'])
        assert len(tagged_tasks) >= 1

    @pytest.mark.asyncio
    async def test_persistence(self):
        """Test that tasks persist across storage instances"""
        # Create and store a task
        task_data = {'title': 'Persistent Task', 'description': 'Should persist'}
        task_id = await self.storage.create_task(task_data)

        # Create new storage instance with same file
        new_storage = TaskStorage(self.temp_file.name)

        # Verify task exists in new instance
        task = await new_storage.get_task(task_id)
        assert task is not None
        assert task.title == 'Persistent Task'


class TestTaskAnalyzer:
    """Test cases for TaskAnalyzer class"""

    def setup_method(self):
        """Set up test environment"""
        self.analyzer = TaskAnalyzer()

    def test_analyze_complexity_basic(self):
        """Test basic complexity analysis"""
        # Simple task
        simple_task = TaskModel(
            id=str(uuid.uuid4()),
            title='Simple Task',
            description='A simple task'
        )
        complexity = self.analyzer.analyze_complexity(simple_task)
        assert 1 <= complexity <= 10
        assert complexity <= 3  # Should be low complexity

    def test_analyze_complexity_high(self):
        """Test high complexity task analysis"""
        # Complex task with keywords and long description
        complex_description = """
        This task involves implementing a comprehensive authentication system with
        OAuth integration, database security measures, API design, performance
        optimization, testing frameworks, and deployment automation. The system
        must handle scalability requirements and integrate with existing
        microservices architecture.
        """

        complex_task = TaskModel(
            id=str(uuid.uuid4()),
            title='Complex Authentication System',
            description=complex_description,
            estimated_hours=40.0,
            dependencies=['dep1', 'dep2', 'dep3'],
            subtasks=['sub1', 'sub2']
        )

        # Create mock dependency tasks
        dependencies = [
            TaskModel(id='dep1', title='Dep 1', description='Dependency 1'),
            TaskModel(id='dep2', title='Dep 2', description='Dependency 2'),
            TaskModel(id='dep3', title='Dep 3', description='Dependency 3')
        ]

        complexity = self.analyzer.analyze_complexity(complex_task, dependencies)
        assert complexity >= 7  # Should be high complexity

    def test_get_recommendations_comprehensive(self):
        """Test comprehensive recommendations generation"""
        # Task with various conditions
        task = TaskModel(
            id=str(uuid.uuid4()),
            title='Test Task',
            description='A test task',
            complexity_score=9,
            priority=TaskPriority.HIGH,
            due_date=datetime.now() - timedelta(days=1),  # Overdue
            dependencies=['dep1', 'dep2']
        )

        recommendations = self.analyzer.get_recommendations(task)
        assert len(recommendations) > 0

        # Check for specific recommendations
        rec_text = ' '.join(recommendations).lower()
        assert 'complexity' in rec_text or 'subtask' in rec_text
        assert 'overdue' in rec_text
        assert 'assign' in rec_text


class TestTaskMasterMCP:
    """Test cases for TaskMasterMCP server"""

    def setup_method(self):
        """Set up test environment"""
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        self.temp_file.close()

        # Mock the storage to use temp file
        with patch('server.TaskStorage') as mock_storage_class:
            mock_storage_class.return_value = TaskStorage(self.temp_file.name)
            self.server = TaskMasterMCP()

    def teardown_method(self):
        """Clean up test environment"""
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)

    @pytest.mark.asyncio
    async def test_create_task_tool(self):
        """Test create_task MCP tool"""
        result = await self.server.create_task(
            title='Test Task',
            description='A test task for MCP',
            priority=TaskPriority.HIGH,
            estimated_hours=8.0,
            tags=['test', 'mcp']
        )

        assert result['success'] is True
        assert 'task_id' in result
        assert 'complexity_score' in result
        assert result['message'] == 'Task "Test Task" created successfully'

    @pytest.mark.asyncio
    async def test_create_task_with_invalid_priority(self):
        """Test create_task with invalid priority"""
        result = await self.server.create_task(
            title='Invalid Task',
            description='Task with invalid priority',
            priority='invalid_priority'
        )

        assert result['success'] is False
        assert 'error' in result

    @pytest.mark.asyncio
    async def test_get_task_tool(self):
        """Test get_task MCP tool"""
        # First create a task
        create_result = await self.server.create_task(
            title='Get Test Task',
            description='Task for get testing'
        )
        task_id = create_result['task_id']

        # Get the task
        result = await self.server.get_task(task_id, include_dependencies=True)

        assert result['success'] is True
        assert result['title'] == 'Get Test Task'
        assert result['description'] == 'Task for get testing'
        assert 'created_at' in result
        assert 'dependency_details' in result

    @pytest.mark.asyncio
    async def test_get_nonexistent_task(self):
        """Test getting a nonexistent task"""
        result = await self.server.get_task('nonexistent-id')

        assert result['success'] is False
        assert 'not found' in result['error']

    @pytest.mark.asyncio
    async def test_update_task_tool(self):
        """Test update_task MCP tool"""
        # Create a task
        create_result = await self.server.create_task(
            title='Update Test',
            description='Will be updated'
        )
        task_id = create_result['task_id']

        # Update the task
        result = await self.server.update_task(
            task_id=task_id,
            title='Updated Title',
            status=TaskStatus.IN_PROGRESS,
            progress_percentage=50
        )

        assert result['success'] is True
        assert 'updated successfully' in result['message']

    @pytest.mark.asyncio
    async def test_delete_task_tool(self):
        """Test delete_task MCP tool"""
        # Create a task
        create_result = await self.server.create_task(
            title='Delete Test',
            description='Will be deleted'
        )
        task_id = create_result['task_id']

        # Delete the task
        result = await self.server.delete_task(task_id)

        assert result['success'] is True
        assert 'deleted successfully' in result['message']

        # Verify deletion
        get_result = await self.server.get_task(task_id)
        assert get_result['success'] is False

    @pytest.mark.asyncio
    async def test_delete_task_with_dependencies(self):
        """Test deleting a task that has dependents"""
        # Create two tasks with dependency
        task1_result = await self.server.create_task(
            title='Dependency Task',
            description='Task that others depend on'
        )
        task1_id = task1_result['task_id']

        task2_result = await self.server.create_task(
            title='Dependent Task',
            description='Task that depends on another',
            dependencies=[task1_id]
        )

        # Try to delete the dependency task
        result = await self.server.delete_task(task1_id)

        assert result['success'] is False
        assert 'dependencies' in result['error']

    @pytest.mark.asyncio
    async def test_list_tasks_tool(self):
        """Test list_tasks MCP tool"""
        # Create multiple tasks
        await self.server.create_task('Task 1', 'First task', priority=TaskPriority.HIGH)
        await self.server.create_task('Task 2', 'Second task', priority=TaskPriority.MEDIUM)
        await self.server.create_task('Task 3', 'Third task', priority=TaskPriority.LOW)

        # List all tasks
        result = await self.server.list_tasks(limit=10)

        assert result['success'] is True
        assert result['count'] >= 3
        assert 'tasks' in result
        assert len(result['tasks']) >= 3

    @pytest.mark.asyncio
    async def test_list_tasks_with_filters(self):
        """Test list_tasks with filtering"""
        # Create tasks with different priorities
        await self.server.create_task('High Task', 'High priority', priority=TaskPriority.HIGH)
        await self.server.create_task('Medium Task', 'Medium priority', priority=TaskPriority.MEDIUM)

        # Filter by priority
        result = await self.server.list_tasks(priority=TaskPriority.HIGH)

        assert result['success'] is True
        assert result['count'] >= 1
        for task in result['tasks']:
            assert task['priority'] == TaskPriority.HIGH

    @pytest.mark.asyncio
    async def test_add_dependency_tool(self):
        """Test add_dependency MCP tool"""
        # Create two tasks
        task1_result = await self.server.create_task('Task 1', 'First task')
        task2_result = await self.server.create_task('Task 2', 'Second task')

        task1_id = task1_result['task_id']
        task2_id = task2_result['task_id']

        # Add dependency
        result = await self.server.add_dependency(task2_id, task1_id)

        assert result['success'] is True
        assert 'added successfully' in result['message']

        # Verify dependency was added
        task2 = await self.server.get_task(task2_id)
        assert task1_id in task2['dependencies']

    @pytest.mark.asyncio
    async def test_add_circular_dependency(self):
        """Test preventing circular dependencies"""
        # Create three tasks in a potential cycle
        task1_result = await self.server.create_task('Task 1', 'First task')
        task2_result = await self.server.create_task('Task 2', 'Second task')
        task3_result = await self.server.create_task('Task 3', 'Third task')

        task1_id = task1_result['task_id']
        task2_id = task2_result['task_id']
        task3_id = task3_result['task_id']

        # Create chain: task3 -> task2 -> task1
        await self.server.add_dependency(task2_id, task1_id)
        await self.server.add_dependency(task3_id, task2_id)

        # Try to create cycle: task1 -> task3
        result = await self.server.add_dependency(task1_id, task3_id)

        assert result['success'] is False
        assert 'circular dependency' in result['error']

    @pytest.mark.asyncio
    async def test_remove_dependency_tool(self):
        """Test remove_dependency MCP tool"""
        # Create tasks with dependency
        task1_result = await self.server.create_task('Task 1', 'First task')
        task2_result = await self.server.create_task('Task 2', 'Second task', dependencies=[task1_result['task_id']])

        task1_id = task1_result['task_id']
        task2_id = task2_result['task_id']

        # Remove dependency
        result = await self.server.remove_dependency(task2_id, task1_id)

        assert result['success'] is True
        assert 'removed successfully' in result['message']

        # Verify dependency was removed
        task2 = await self.server.get_task(task2_id)
        assert task1_id not in task2['dependencies']

    @pytest.mark.asyncio
    async def test_analyze_task_complexity_tool(self):
        """Test analyze_task_complexity MCP tool"""
        # Create a complex task
        result = await self.server.create_task(
            title='Complex Integration Task',
            description='Implement authentication system with database integration, API design, and security measures',
            estimated_hours=30.0
        )
        task_id = result['task_id']

        # Analyze complexity
        analysis = await self.server.analyze_task_complexity(task_id, recalculate=True)

        assert analysis['success'] is True
        assert 'complexity_score' in analysis
        assert 'complexity_level' in analysis
        assert 'recommendations' in analysis
        assert 'analysis' in analysis
        assert analysis['complexity_score'] >= 1

    @pytest.mark.asyncio
    async def test_get_task_statistics_tool(self):
        """Test get_task_statistics MCP tool"""
        # Create multiple tasks with different statuses
        await self.server.create_task('Task 1', 'First task')

        task2_result = await self.server.create_task('Task 2', 'Second task')
        await self.server.update_task(task2_result['task_id'], status=TaskStatus.DONE)

        await self.server.create_task('Task 3', 'Third task', priority=TaskPriority.HIGH)

        # Get statistics
        stats = await self.server.get_task_statistics(group_by='status')

        assert stats['success'] is True
        assert 'summary' in stats
        assert 'grouped_statistics' in stats
        assert stats['summary']['total_tasks'] >= 3

    @pytest.mark.asyncio
    async def test_search_tasks_tool(self):
        """Test search_tasks MCP tool"""
        # Create tasks with searchable content
        await self.server.create_task(
            'Authentication System',
            'Implement OAuth authentication with database integration'
        )
        await self.server.create_task(
            'User Interface',
            'Create responsive UI for user management'
        )
        await self.server.create_task(
            'Database Migration',
            'Set up database schema and authentication tables'
        )

        # Search for tasks
        result = await self.server.search_tasks('authentication', limit=10)

        assert result['success'] is True
        assert result['count'] >= 2  # Should find at least 2 tasks

        # Verify results are ranked by relevance
        for task in result['tasks']:
            assert 'match_score' in task
            assert task['match_score'] > 0

    @pytest.mark.asyncio
    async def test_update_progress_tool(self):
        """Test update_progress MCP tool"""
        # Create a task
        task_result = await self.server.create_task('Progress Task', 'Task for progress testing')
        task_id = task_result['task_id']

        # Update progress
        result = await self.server.update_progress(
            task_id,
            progress_percentage=75,
            notes='Made significant progress on implementation'
        )

        assert result['success'] is True
        assert result['progress_percentage'] == 75
        assert result['status'] == TaskStatus.IN_PROGRESS

        # Verify progress was saved
        task = await self.server.get_task(task_id)
        assert task['progress_percentage'] == 75
        assert 'progress_notes' in task['metadata']

    @pytest.mark.asyncio
    async def test_update_progress_completion(self):
        """Test automatic completion when progress reaches 100%"""
        # Create a task
        task_result = await self.server.create_task('Completion Task', 'Task for completion testing')
        task_id = task_result['task_id']

        # Update progress to 100%
        result = await self.server.update_progress(task_id, progress_percentage=100)

        assert result['success'] is True
        assert result['status'] == TaskStatus.DONE

        # Verify task is marked as done
        task = await self.server.get_task(task_id)
        assert task['status'] == TaskStatus.DONE
        assert task['completed_at'] is not None

    @pytest.mark.asyncio
    async def test_get_recommendations_tool(self):
        """Test get_recommendations MCP tool"""
        # Create a task with conditions that generate recommendations
        task_result = await self.server.create_task(
            'High Complexity Task',
            'Very complex task with integration, authentication, database, API design, and performance optimization',
            priority=TaskPriority.HIGH,
            estimated_hours=40.0
        )
        task_id = task_result['task_id']

        # Get recommendations
        result = await self.server.get_recommendations(task_id)

        assert result['success'] is True
        assert 'recommendations' in result
        assert 'task_info' in result
        assert len(result['recommendations']) > 0

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling for various edge cases"""
        # Test with invalid task ID
        result = await self.server.get_task('invalid-uuid')
        assert result['success'] is False
        assert 'error' in result

        # Test update with invalid task ID
        result = await self.server.update_task('invalid-uuid', title='New Title')
        assert result['success'] is False
        assert 'error' in result

        # Test delete with invalid task ID
        result = await self.server.delete_task('invalid-uuid')
        assert result['success'] is False
        assert 'error' in result


class TestIntegration:
    """Integration tests for complete workflows"""

    def setup_method(self):
        """Set up test environment"""
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        self.temp_file.close()

        with patch('server.TaskStorage') as mock_storage_class:
            mock_storage_class.return_value = TaskStorage(self.temp_file.name)
            self.server = TaskMasterMCP()

    def teardown_method(self):
        """Clean up test environment"""
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)

    @pytest.mark.asyncio
    async def test_complete_project_workflow(self):
        """Test a complete project workflow from creation to completion"""
        # Create a main task
        main_task = await self.server.create_task(
            'Build Authentication System',
            'Complete authentication system with OAuth integration',
            priority=TaskPriority.HIGH,
            estimated_hours=40.0
        )
        main_id = main_task['task_id']

        # Create subtasks
        db_task = await self.server.create_task(
            'Database Schema',
            'Create user authentication tables',
            priority=TaskPriority.HIGH,
            estimated_hours=8.0
        )

        api_task = await self.server.create_task(
            'API Endpoints',
            'Implement authentication API endpoints',
            priority=TaskPriority.HIGH,
            estimated_hours=16.0,
            dependencies=[db_task['task_id']]
        )

        ui_task = await self.server.create_task(
            'User Interface',
            'Create login and registration forms',
            priority=TaskPriority.MEDIUM,
            estimated_hours=12.0,
            dependencies=[api_task['task_id']]
        )

        # Add dependencies to main task
        await self.server.add_dependency(main_id, db_task['task_id'])
        await self.server.add_dependency(main_id, api_task['task_id'])
        await self.server.add_dependency(main_id, ui_task['task_id'])

        # Start working on database task
        await self.server.update_task(db_task['task_id'], status=TaskStatus.IN_PROGRESS)
        await self.server.update_progress(db_task['task_id'], 50, 'Created initial schema')
        await self.server.update_progress(db_task['task_id'], 100, 'Database schema complete')

        # Verify database task is done
        db_status = await self.server.get_task(db_task['task_id'])
        assert db_status['status'] == TaskStatus.DONE

        # Work on API task
        await self.server.update_task(api_task['task_id'], status=TaskStatus.IN_PROGRESS)
        await self.server.update_progress(api_task['task_id'], 100)

        # Work on UI task
        await self.server.update_task(ui_task['task_id'], status=TaskStatus.IN_PROGRESS)
        await self.server.update_progress(ui_task['task_id'], 100)

        # Complete main task
        await self.server.update_task(main_id, status=TaskStatus.DONE)

        # Get final statistics
        stats = await self.server.get_task_statistics()
        assert stats['success'] is True
        assert stats['summary']['completed_tasks'] >= 4
        assert stats['summary']['completion_rate'] == 100.0

    @pytest.mark.asyncio
    async def test_dependency_chain_management(self):
        """Test complex dependency chain management"""
        # Create a chain of dependent tasks
        tasks = []
        for i in range(5):
            task_result = await self.server.create_task(
                f'Task {i+1}',
                f'Task number {i+1} in the chain'
            )
            tasks.append(task_result['task_id'])

        # Create dependency chain: task5 -> task4 -> task3 -> task2 -> task1
        for i in range(1, 5):
            await self.server.add_dependency(tasks[i], tasks[i-1])

        # Complete tasks in order
        for i in range(5):
            await self.server.update_task(tasks[i], status=TaskStatus.DONE)

            # Verify dependencies are properly tracked
            task = await self.server.get_task(tasks[i], include_dependencies=True)
            if i > 0:
                assert len(task['dependency_details']) == 1
                assert task['dependency_details'][0]['status'] == TaskStatus.DONE

    @pytest.mark.asyncio
    async def test_performance_with_many_tasks(self):
        """Test performance with a large number of tasks"""
        import time

        # Create many tasks
        start_time = time.time()
        task_ids = []

        for i in range(100):
            result = await self.server.create_task(
                f'Performance Task {i}',
                f'Task {i} for performance testing',
                priority=TaskPriority.MEDIUM if i % 2 else TaskPriority.HIGH
            )
            task_ids.append(result['task_id'])

        creation_time = time.time() - start_time

        # List all tasks
        start_time = time.time()
        result = await self.server.list_tasks(limit=100)
        list_time = time.time() - start_time

        # Search tasks
        start_time = time.time()
        search_result = await self.server.search_tasks('Performance', limit=50)
        search_time = time.time() - start_time

        # Verify performance (should be reasonable for 100 tasks)
        assert creation_time < 10.0  # Less than 10 seconds to create 100 tasks
        assert list_time < 1.0       # Less than 1 second to list 100 tasks
        assert search_time < 1.0     # Less than 1 second to search

        # Verify functionality
        assert result['count'] == 100
        assert search_result['count'] == 50  # Limited to 50 results as requested


if __name__ == '__main__':
    """Run tests when executed directly"""
    pytest.main([__file__, '-v', '--tb=short'])
