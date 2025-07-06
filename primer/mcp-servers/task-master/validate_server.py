#!/usr/bin/env python3
"""
Basic validation script for TaskMaster MCP Server

This script performs basic validation of the task-master server implementation
to ensure core functionality works correctly without requiring full MCP protocol setup.
"""

import asyncio
import json
import tempfile
import os
import sys
from pathlib import Path

# Add the current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def test_imports():
    """Test that all required modules can be imported"""
    print("🧪 Testing imports...")
    try:
        from server import TaskMasterMCP, TaskStorage, TaskAnalyzer, TaskModel, TaskStatus, TaskPriority
        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error during import: {e}")
        return False

async def test_task_storage():
    """Test basic task storage functionality"""
    print("\n🧪 Testing TaskStorage...")

    # Create temporary file for testing
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
    temp_file.close()

    try:
        from server import TaskStorage, TaskStatus, TaskPriority

        storage = TaskStorage(temp_file.name)

        # Test task creation
        task_data = {
            'title': 'Test Task',
            'description': 'A test task for validation',
            'priority': TaskPriority.HIGH
        }

        task_id = await storage.create_task(task_data)
        print(f"✅ Task created with ID: {task_id}")

        # Test task retrieval
        task = await storage.get_task(task_id)
        if task and task.title == 'Test Task':
            print("✅ Task retrieved successfully")
        else:
            print("❌ Task retrieval failed")
            return False

        # Test task update
        success = await storage.update_task(task_id, {'status': TaskStatus.IN_PROGRESS})
        if success:
            print("✅ Task updated successfully")
        else:
            print("❌ Task update failed")
            return False

        # Test task listing
        tasks = await storage.list_tasks()
        if tasks and len(tasks) >= 1:
            print(f"✅ Task listing works: {len(tasks)} tasks found")
        else:
            print("❌ Task listing failed")
            return False

        return True

    except Exception as e:
        print(f"❌ TaskStorage test error: {e}")
        return False
    finally:
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)

async def test_task_analyzer():
    """Test task complexity analysis"""
    print("\n🧪 Testing TaskAnalyzer...")

    try:
        from server import TaskAnalyzer, TaskModel, TaskPriority
        import uuid

        analyzer = TaskAnalyzer()

        # Test simple task
        simple_task = TaskModel(
            id=str(uuid.uuid4()),
            title='Simple Task',
            description='A simple task',
            priority=TaskPriority.LOW
        )

        complexity = analyzer.analyze_complexity(simple_task)
        if 1 <= complexity <= 10:
            print(f"✅ Simple task complexity analysis: {complexity}/10")
        else:
            print(f"❌ Invalid complexity score: {complexity}")
            return False

        # Test complex task
        complex_task = TaskModel(
            id=str(uuid.uuid4()),
            title='Complex Authentication System',
            description='Implement comprehensive authentication system with OAuth integration, database security, API design, performance optimization, testing frameworks, and deployment automation',
            priority=TaskPriority.HIGH,
            estimated_hours=40.0,
            dependencies=['dep1', 'dep2']
        )

        complex_complexity = analyzer.analyze_complexity(complex_task)
        if complex_complexity > complexity:
            print(f"✅ Complex task has higher complexity: {complex_complexity}/10")
        else:
            print(f"❌ Complex task complexity not higher: {complex_complexity}")
            return False

        # Test recommendations
        recommendations = analyzer.get_recommendations(complex_task)
        if recommendations and len(recommendations) > 0:
            print(f"✅ Recommendations generated: {len(recommendations)} recommendations")
        else:
            print("❌ No recommendations generated")
            return False

        return True

    except Exception as e:
        print(f"❌ TaskAnalyzer test error: {e}")
        return False

async def test_mcp_server():
    """Test MCP server functionality (without protocol setup)"""
    print("\n🧪 Testing TaskMasterMCP server...")

    try:
        from server import TaskMasterMCP, TaskPriority

        # Note: We can't fully test MCP protocol without proper setup,
        # but we can test the tool methods directly
        server = TaskMasterMCP()
        print("✅ TaskMasterMCP server created")

        # Test create_task method
        result = await server.create_task(
            title='MCP Test Task',
            description='A test task for MCP server validation',
            priority=TaskPriority.HIGH
        )

        if result.get('success'):
            task_id = result['task_id']
            print(f"✅ MCP create_task works: {task_id}")
        else:
            print(f"❌ MCP create_task failed: {result}")
            return False

        # Test get_task method
        get_result = await server.get_task(task_id)
        if get_result.get('success') and get_result.get('title') == 'MCP Test Task':
            print("✅ MCP get_task works")
        else:
            print(f"❌ MCP get_task failed: {get_result}")
            return False

        # Test update_task method
        update_result = await server.update_task(
            task_id=task_id,
            status='in_progress',
            progress_percentage=50
        )
        if update_result.get('success'):
            print("✅ MCP update_task works")
        else:
            print(f"❌ MCP update_task failed: {update_result}")
            return False

        # Test list_tasks method
        list_result = await server.list_tasks(limit=10)
        if list_result.get('success') and list_result.get('count', 0) >= 1:
            print(f"✅ MCP list_tasks works: {list_result['count']} tasks")
        else:
            print(f"❌ MCP list_tasks failed: {list_result}")
            return False

        # Test complexity analysis
        complexity_result = await server.analyze_task_complexity(task_id)
        if complexity_result.get('success'):
            print(f"✅ MCP analyze_task_complexity works: {complexity_result.get('complexity_score')}/10")
        else:
            print(f"❌ MCP analyze_task_complexity failed: {complexity_result}")
            return False

        # Test search
        search_result = await server.search_tasks('MCP Test')
        if search_result.get('success') and search_result.get('count', 0) >= 1:
            print(f"✅ MCP search_tasks works: {search_result['count']} matches")
        else:
            print(f"❌ MCP search_tasks failed: {search_result}")
            return False

        return True

    except Exception as e:
        print(f"❌ MCP server test error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_dependency_management():
    """Test dependency management and cycle detection"""
    print("\n🧪 Testing dependency management...")

    try:
        from server import TaskMasterMCP

        server = TaskMasterMCP()

        # Create two tasks
        task1_result = await server.create_task('Task 1', 'First task')
        task2_result = await server.create_task('Task 2', 'Second task')

        if not (task1_result.get('success') and task2_result.get('success')):
            print("❌ Failed to create tasks for dependency test")
            return False

        task1_id = task1_result['task_id']
        task2_id = task2_result['task_id']

        # Add dependency: task2 depends on task1
        dep_result = await server.add_dependency(task2_id, task1_id)
        if dep_result.get('success'):
            print("✅ Dependency added successfully")
        else:
            print(f"❌ Failed to add dependency: {dep_result}")
            return False

        # Try to create circular dependency (should fail)
        circular_result = await server.add_dependency(task1_id, task2_id)
        if not circular_result.get('success') and 'circular' in circular_result.get('error', '').lower():
            print("✅ Circular dependency prevention works")
        else:
            print(f"❌ Circular dependency not prevented: {circular_result}")
            return False

        return True

    except Exception as e:
        print(f"❌ Dependency management test error: {e}")
        return False

async def main():
    """Run all validation tests"""
    print("🚀 Starting TaskMaster MCP Server Validation")
    print("=" * 50)

    tests = [
        ("Imports", test_imports()),
        ("TaskStorage", test_task_storage()),
        ("TaskAnalyzer", test_task_analyzer()),
        ("MCP Server", test_mcp_server()),
        ("Dependency Management", test_dependency_management())
    ]

    results = []

    for test_name, test_coro in tests:
        if asyncio.iscoroutine(test_coro):
            result = await test_coro
        else:
            result = test_coro
        results.append((test_name, result))

    print("\n" + "=" * 50)
    print("📊 VALIDATION RESULTS")
    print("=" * 50)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<25} {status}")
        if result:
            passed += 1

    print(f"\nSummary: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED! TaskMaster MCP Server is working correctly.")
        return True
    else:
        print(f"\n❌ {total - passed} tests failed. Please check the implementation.")
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 Validation failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
