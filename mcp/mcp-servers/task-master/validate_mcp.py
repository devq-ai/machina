#!/usr/bin/env python3
"""
MCP Server Validation Script for Task Master

This script validates that the Task Master MCP server is working correctly
by testing MCP protocol compliance, tool functionality, and integration.
"""

import asyncio
import json
import sys
import subprocess
import tempfile
import os
from pathlib import Path

async def test_mcp_protocol():
    """Test basic MCP protocol compliance"""
    print("🔍 Testing MCP Protocol Compliance...")

    # Test server startup
    try:
        process = subprocess.Popen(
            [sys.executable, "server.py"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Send initialize request
        initialize_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        }

        request_json = json.dumps(initialize_request) + "\n"
        process.stdin.write(request_json)
        process.stdin.flush()

        # Read response with timeout
        try:
            response_line = await asyncio.wait_for(
                asyncio.create_task(asyncio.to_thread(process.stdout.readline)),
                timeout=5.0
            )

            if response_line:
                response = json.loads(response_line.strip())
                if response.get("result"):
                    print("✅ MCP Protocol: Server responds to initialize")
                    return True
                else:
                    print("❌ MCP Protocol: Invalid initialize response")
                    return False
            else:
                print("❌ MCP Protocol: No response from server")
                return False

        except asyncio.TimeoutError:
            print("❌ MCP Protocol: Server response timeout")
            return False

    except Exception as e:
        print(f"❌ MCP Protocol: Error testing server - {e}")
        return False
    finally:
        if 'process' in locals():
            process.terminate()
            process.wait()

async def test_tools_listing():
    """Test that all expected tools are available"""
    print("\n🔧 Testing MCP Tools Listing...")

    expected_tools = [
        "create_task",
        "get_task",
        "update_task",
        "delete_task",
        "list_tasks",
        "add_dependency",
        "remove_dependency",
        "analyze_task_complexity",
        "get_task_statistics",
        "search_tasks",
        "update_progress",
        "get_recommendations"
    ]

    try:
        process = subprocess.Popen(
            [sys.executable, "server.py"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Initialize first
        initialize_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "test-client", "version": "1.0.0"}
            }
        }

        process.stdin.write(json.dumps(initialize_request) + "\n")
        process.stdin.flush()

        # Read initialize response
        init_response = process.stdout.readline()

        # Send initialized notification
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        process.stdin.write(json.dumps(initialized_notification) + "\n")
        process.stdin.flush()

        # Request tools list
        tools_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list"
        }

        process.stdin.write(json.dumps(tools_request) + "\n")
        process.stdin.flush()

        # Read tools response
        tools_response_line = await asyncio.wait_for(
            asyncio.create_task(asyncio.to_thread(process.stdout.readline)),
            timeout=5.0
        )

        if tools_response_line:
            tools_response = json.loads(tools_response_line.strip())
            if "result" in tools_response and "tools" in tools_response["result"]:
                available_tools = [tool["name"] for tool in tools_response["result"]["tools"]]

                print(f"📋 Available tools: {len(available_tools)}")
                for tool in available_tools:
                    print(f"   • {tool}")

                missing_tools = set(expected_tools) - set(available_tools)
                if missing_tools:
                    print(f"❌ Missing tools: {missing_tools}")
                    return False
                else:
                    print("✅ All expected tools are available")
                    return True
            else:
                print("❌ Invalid tools response format")
                return False
        else:
            print("❌ No tools response received")
            return False

    except Exception as e:
        print(f"❌ Error testing tools: {e}")
        return False
    finally:
        if 'process' in locals():
            process.terminate()
            process.wait()

def test_imports():
    """Test that all required imports work"""
    print("\n📦 Testing Import Dependencies...")

    try:
        # Test MCP imports
        from mcp import types
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
        print("✅ MCP imports: OK")

        # Test Pydantic imports
        from pydantic import BaseModel, Field, field_validator
        print("✅ Pydantic imports: OK")

        # Test asyncio
        import asyncio
        print("✅ Asyncio: OK")

        # Test other dependencies
        import json
        import uuid
        import datetime
        print("✅ Standard library imports: OK")

        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_server_file():
    """Test server file structure and syntax"""
    print("\n📝 Testing Server File Structure...")

    server_file = Path("server.py")
    if not server_file.exists():
        print("❌ server.py file not found")
        return False

    try:
        # Test syntax by compiling
        with open(server_file) as f:
            code = f.read()

        compile(code, str(server_file), 'exec')
        print("✅ Python syntax: Valid")

        # Check for key classes and functions
        required_components = [
            "class TaskStatus",
            "class TaskPriority",
            "class TaskModel",
            "class TaskStorage",
            "class TaskAnalyzer",
            "class TaskMasterMCP",
            "def main"
        ]

        missing_components = []
        for component in required_components:
            if component not in code:
                missing_components.append(component)

        if missing_components:
            print(f"❌ Missing components: {missing_components}")
            return False
        else:
            print("✅ All required components present")
            return True

    except SyntaxError as e:
        print(f"❌ Syntax error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error reading server file: {e}")
        return False

async def run_validation():
    """Run all validation tests"""
    print("🚀 Task Master MCP Server Validation")
    print("=" * 50)

    # Track test results
    results = []

    # Test 1: Imports and dependencies
    results.append(("Import Dependencies", test_imports()))

    # Test 2: Server file structure
    results.append(("Server File Structure", test_server_file()))

    # Test 3: MCP protocol compliance
    results.append(("MCP Protocol", await test_mcp_protocol()))

    # Test 4: Tools listing
    results.append(("MCP Tools", await test_tools_listing()))

    # Summary
    print("\n" + "=" * 50)
    print("📊 VALIDATION SUMMARY")
    print("=" * 50)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:.<30} {status}")
        if result:
            passed += 1

    print(f"\nResults: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Task Master MCP Server is ready!")
        print("💡 Server can be integrated with main Machina service")
        return True
    else:
        print(f"\n⚠️  {total - passed} tests failed. Please review and fix issues.")
        return False

if __name__ == "__main__":
    try:
        result = asyncio.run(run_validation())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n🛑 Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error during validation: {e}")
        sys.exit(1)
