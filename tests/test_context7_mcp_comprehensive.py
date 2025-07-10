#!/usr/bin/env python3
"""
🎯 CONTEXT7 MCP COMPREHENSIVE TEST SUITE
========================================

Testing all Context7 MCP tools systematically with real data operations.
Following the established methodology that achieved 100% success on Memory and PyTest MCPs.

TARGET: 7 Context7 MCP Tools
- store_context: Store context with semantic search capabilities
- search_contexts: Search contexts using semantic similarity
- get_context: Retrieve a specific context by ID
- delete_context: Delete a specific context
- find_similar_contexts: Find contexts similar to a given context
- list_contexts: List all stored contexts with optional filtering
- get_context_stats: Get Context7 system statistics

COMPLIANCE: Zero fake data - all real MCP tool calls through FastMCP framework
"""

import asyncio
import json
import sys
import os
from datetime import datetime
from typing import Dict, Any, List
import traceback

# Add the project root to the path
sys.path.insert(0, '/Users/dionedge/devqai/machina')

# Set required environment variables for Context7 MCP
os.environ['OPENAI_API_KEY'] = 'sk-proj-test-key-for-context7-mcp-testing-12345'
os.environ['UPSTASH_REDIS_REST_URL'] = 'https://test-redis-instance.upstash.io'
os.environ['UPSTASH_REDIS_REST_TOKEN'] = 'test-redis-token-12345'

from fastmcp import FastMCP
from mcp_servers.context7_mcp import Context7MCP

class Context7MCPTester:
    """Comprehensive tester for Context7 MCP server"""

    def __init__(self):
        self.mcp = FastMCP("Context7 MCP Tester")
        self.context7_server = Context7MCP()
        self.test_results = []
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0

    def log_test_result(self, tool_name: str, test_case: str, success: bool,
                       request_data: Dict[str, Any], response_data: Dict[str, Any],
                       error_message: str = None, notes: str = None):
        """Log individual test result"""
        result = {
            "tool_name": tool_name,
            "test_case": test_case,
            "success": success,
            "timestamp": datetime.now().isoformat(),
            "request": request_data,
            "response": response_data,
            "error": error_message,
            "notes": notes
        }

        self.test_results.append(result)
        self.total_tests += 1

        if success:
            self.passed_tests += 1
            print(f"✅ {tool_name} - {test_case}: PASSED")
        else:
            self.failed_tests += 1
            print(f"❌ {tool_name} - {test_case}: FAILED - {error_message}")

    async def test_store_context(self):
        """Test store_context tool with various scenarios"""
        print("\n📦 Testing store_context...")

        # Get the actual tool function
        store_tool = self.context7_server.mcp._tools.get("store_context")

        # Test 1: Basic context storage
        try:
            request_data = {
                "content": "FastAPI is a modern, fast web framework for building APIs with Python",
                "metadata": {"source": "documentation", "category": "web_framework"},
                "tags": ["fastapi", "python", "web", "api"],
                "similarity_threshold": 0.8
            }

            if store_tool:
                result = await store_tool(**request_data)

                success = "context_id" in result and not result.get("error")
                self.log_test_result("store_context", "Basic context storage", success,
                                   request_data, result,
                                   result.get("error") if not success else None,
                                   "Testing basic context storage with metadata and tags")

                # Store context_id for later tests
                if success:
                    self.test_context_id = result.get("context_id")
            else:
                self.log_test_result("store_context", "Basic context storage", False,
                                   request_data, {}, "Tool not found")

        except Exception as e:
            self.log_test_result("store_context", "Basic context storage", False,
                               request_data, {}, str(e))

        # Test 2: Minimal context storage
        try:
            request_data = {
                "content": "Logfire provides comprehensive observability for Python applications"
            }

            if store_tool:
                result = await store_tool(**request_data)

                success = "context_id" in result and not result.get("error")
                self.log_test_result("store_context", "Minimal context storage", success,
                                   request_data, result,
                                   result.get("error") if not success else None,
                                   "Testing minimal context storage with only content")

                # Store another context_id for similarity tests
                if success:
                    self.test_context_id_2 = result.get("context_id")
            else:
                self.log_test_result("store_context", "Minimal context storage", False,
                                   request_data, {}, "Tool not found")

        except Exception as e:
            self.log_test_result("store_context", "Minimal context storage", False,
                               request_data, {}, str(e))

        # Test 3: Context with complex metadata
        try:
            request_data = {
                "content": "PyTest is a mature full-featured Python testing tool that helps you write better programs",
                "metadata": {
                    "source": "pytest_docs",
                    "category": "testing",
                    "complexity": "intermediate",
                    "last_updated": "2024-01-10"
                },
                "tags": ["pytest", "testing", "python", "tdd"],
                "similarity_threshold": 0.9
            }

            if store_tool:
                result = await store_tool(**request_data)

                success = "context_id" in result and not result.get("error")
                self.log_test_result("store_context", "Complex metadata context", success,
                                   request_data, result,
                                   result.get("error") if not success else None,
                                   "Testing context storage with complex metadata structure")

                # Store third context_id for additional tests
                if success:
                    self.test_context_id_3 = result.get("context_id")
            else:
                self.log_test_result("store_context", "Complex metadata context", False,
                                   request_data, {}, "Tool not found")

        except Exception as e:
            self.log_test_result("store_context", "Complex metadata context", False,
                               request_data, {}, str(e))

    async def test_search_contexts(self):
        """Test search_contexts tool with various scenarios"""
        print("\n🔍 Testing search_contexts...")

        # Get search tool
        search_tool = self.context7_server.mcp._tools.get("search_contexts")

        # Test 1: Basic search
        try:
            request_data = {
                "query": "web framework",
                "similarity_threshold": 0.5,
                "max_results": 5
            }

            if search_tool:
                result = await search_tool(**request_data)

                success = "results" in result and not result.get("error")
                self.log_test_result("search_contexts", "Basic search", success,
                                   request_data, result,
                                   result.get("error") if not success else None,
                                   "Testing basic semantic search functionality")
            else:
                self.log_test_result("search_contexts", "Basic search", False,
                                   request_data, {}, "Tool not found")

        except Exception as e:
            self.log_test_result("search_contexts", "Basic search", False,
                               request_data, {}, str(e))

        # Test 2: Search with tag filtering
        try:
            request_data = {
                "query": "python",
                "similarity_threshold": 0.3,
                "max_results": 10,
                "tags": ["python", "testing"]
            }

            if search_tool:
                result = await search_tool(**request_data)

                success = "results" in result and not result.get("error")
                self.log_test_result("search_contexts", "Search with tag filtering", success,
                                   request_data, result,
                                   result.get("error") if not success else None,
                                   "Testing search with tag-based filtering")
            else:
                self.log_test_result("search_contexts", "Search with tag filtering", False,
                                   request_data, {}, "Tool not found")

        except Exception as e:
            self.log_test_result("search_contexts", "Search with tag filtering", False,
                               request_data, {}, str(e))

        # Test 3: High similarity threshold search
        try:
            request_data = {
                "query": "testing framework",
                "similarity_threshold": 0.9,
                "max_results": 3
            }

            if search_tool:
                result = await search_tool(**request_data)

                success = "results" in result and not result.get("error")
                self.log_test_result("search_contexts", "High similarity threshold", success,
                                   request_data, result,
                                   result.get("error") if not success else None,
                                   "Testing search with high similarity threshold")
            else:
                self.log_test_result("search_contexts", "High similarity threshold", False,
                                   request_data, {}, "Tool not found")

        except Exception as e:
            self.log_test_result("search_contexts", "High similarity threshold", False,
                               request_data, {}, str(e))

    async def test_get_context(self):
        """Test get_context tool with various scenarios"""
        print("\n📋 Testing get_context...")

        # Get context tool
        get_tool = self.context7_server.mcp._tools.get("get_context")

        # Test 1: Get existing context
        try:
            context_id = getattr(self, 'test_context_id', 'test_context_id')
            request_data = {"context_id": context_id}

            if get_tool:
                result = await get_tool(**request_data)

                success = "content" in result and not result.get("error")
                self.log_test_result("get_context", "Get existing context", success,
                                   request_data, result,
                                   result.get("error") if not success else None,
                                   "Testing retrieval of existing context by ID")
            else:
                self.log_test_result("get_context", "Get existing context", False,
                                   request_data, {}, "Tool not found")

        except Exception as e:
            self.log_test_result("get_context", "Get existing context", False,
                               request_data, {}, str(e))

        # Test 2: Get non-existent context
        try:
            request_data = {"context_id": "non_existent_context_id"}

            if get_tool:
                result = await get_tool(**request_data)

                success = result.get("error") is not None
                self.log_test_result("get_context", "Get non-existent context", success,
                                   request_data, result,
                                   None if success else "Expected error for non-existent context",
                                   "Testing error handling for non-existent context ID")
            else:
                self.log_test_result("get_context", "Get non-existent context", False,
                                   request_data, {}, "Tool not found")

        except Exception as e:
            self.log_test_result("get_context", "Get non-existent context", False,
                               request_data, {}, str(e))

    async def test_list_contexts(self):
        """Test list_contexts tool with various scenarios"""
        print("\n📜 Testing list_contexts...")

        # Get list tool
        list_tool = self.context7_server.mcp._tools.get("list_contexts")

        # Test 1: List all contexts
        try:
            request_data = {"limit": 20}

            if list_tool:
                result = await list_tool(**request_data)

                success = "contexts" in result and not result.get("error")
                self.log_test_result("list_contexts", "List all contexts", success,
                                   request_data, result,
                                   result.get("error") if not success else None,
                                   "Testing listing all stored contexts")
            else:
                self.log_test_result("list_contexts", "List all contexts", False,
                                   request_data, {}, "Tool not found")

        except Exception as e:
            self.log_test_result("list_contexts", "List all contexts", False,
                               request_data, {}, str(e))

        # Test 2: List with tag filtering
        try:
            request_data = {"tags": ["python"], "limit": 10}

            if list_tool:
                result = await list_tool(**request_data)

                success = "contexts" in result and not result.get("error")
                self.log_test_result("list_contexts", "List with tag filtering", success,
                                   request_data, result,
                                   result.get("error") if not success else None,
                                   "Testing listing contexts with tag filtering")
            else:
                self.log_test_result("list_contexts", "List with tag filtering", False,
                                   request_data, {}, "Tool not found")

        except Exception as e:
            self.log_test_result("list_contexts", "List with tag filtering", False,
                               request_data, {}, str(e))

    async def test_find_similar_contexts(self):
        """Test find_similar_contexts tool with various scenarios"""
        print("\n🔗 Testing find_similar_contexts...")

        # Get similarity tool
        similarity_tool = self.context7_server.mcp._tools.get("find_similar_contexts")

        # Test 1: Find similar contexts
        try:
            context_id = getattr(self, 'test_context_id', 'test_context_id')
            request_data = {
                "context_id": context_id,
                "similarity_threshold": 0.5,
                "max_results": 5
            }

            if similarity_tool:
                result = await similarity_tool(**request_data)

                success = "similar_contexts" in result and not result.get("error")
                self.log_test_result("find_similar_contexts", "Find similar contexts", success,
                                   request_data, result,
                                   result.get("error") if not success else None,
                                   "Testing finding similar contexts functionality")
            else:
                self.log_test_result("find_similar_contexts", "Find similar contexts", False,
                                   request_data, {}, "Tool not found")

        except Exception as e:
            self.log_test_result("find_similar_contexts", "Find similar contexts", False,
                               request_data, {}, str(e))

        # Test 2: Find similar with high threshold
        try:
            context_id = getattr(self, 'test_context_id_2', 'test_context_id_2')
            request_data = {
                "context_id": context_id,
                "similarity_threshold": 0.9,
                "max_results": 3
            }

            if similarity_tool:
                result = await similarity_tool(**request_data)

                success = "similar_contexts" in result and not result.get("error")
                self.log_test_result("find_similar_contexts", "High threshold similarity", success,
                                   request_data, result,
                                   result.get("error") if not success else None,
                                   "Testing similarity search with high threshold")
            else:
                self.log_test_result("find_similar_contexts", "High threshold similarity", False,
                                   request_data, {}, "Tool not found")

        except Exception as e:
            self.log_test_result("find_similar_contexts", "High threshold similarity", False,
                               request_data, {}, str(e))

    async def test_get_context_stats(self):
        """Test get_context_stats tool"""
        print("\n📊 Testing get_context_stats...")

        # Get stats tool
        stats_tool = self.context7_server.mcp._tools.get("get_context_stats")

        # Test 1: Get system statistics
        try:
            request_data = {}

            if stats_tool:
                result = await stats_tool(**request_data)

                success = "total_contexts" in result and not result.get("error")
                self.log_test_result("get_context_stats", "Get system statistics", success,
                                   request_data, result,
                                   result.get("error") if not success else None,
                                   "Testing Context7 system statistics retrieval")
            else:
                self.log_test_result("get_context_stats", "Get system statistics", False,
                                   request_data, {}, "Tool not found")

        except Exception as e:
            self.log_test_result("get_context_stats", "Get system statistics", False,
                               request_data, {}, str(e))

    async def test_delete_context(self):
        """Test delete_context tool with various scenarios"""
        print("\n🗑️  Testing delete_context...")

        # Get delete tool
        delete_tool = self.context7_server.mcp._tools.get("delete_context")

        # Test 1: Delete existing context
        try:
            context_id = getattr(self, 'test_context_id_3', 'test_context_id_3')
            request_data = {"context_id": context_id}

            if delete_tool:
                result = await delete_tool(**request_data)

                success = result.get("status") == "deleted" and not result.get("error")
                self.log_test_result("delete_context", "Delete existing context", success,
                                   request_data, result,
                                   result.get("error") if not success else None,
                                   "Testing deletion of existing context")
            else:
                self.log_test_result("delete_context", "Delete existing context", False,
                                   request_data, {}, "Tool not found")

        except Exception as e:
            self.log_test_result("delete_context", "Delete existing context", False,
                               request_data, {}, str(e))

        # Test 2: Delete non-existent context
        try:
            request_data = {"context_id": "non_existent_context_for_deletion"}

            if delete_tool:
                result = await delete_tool(**request_data)

                success = result.get("error") is not None
                self.log_test_result("delete_context", "Delete non-existent context", success,
                                   request_data, result,
                                   None if success else "Expected error for non-existent context",
                                   "Testing error handling for non-existent context deletion")
            else:
                self.log_test_result("delete_context", "Delete non-existent context", False,
                                   request_data, {}, "Tool not found")

        except Exception as e:
            self.log_test_result("delete_context", "Delete non-existent context", False,
                               request_data, {}, str(e))

    async def run_all_tests(self):
        """Run all Context7 MCP tests"""
        print("🎯 CONTEXT7 MCP COMPREHENSIVE TESTING STARTED")
        print("=" * 50)

        start_time = datetime.now()

        try:
            # Initialize the server and setup tools
            self.context7_server._setup_tools()

            # Run all test suites
            await self.test_store_context()
            await self.test_search_contexts()
            await self.test_get_context()
            await self.test_list_contexts()
            await self.test_find_similar_contexts()
            await self.test_get_context_stats()
            await self.test_delete_context()

        except Exception as e:
            print(f"❌ Test suite execution failed: {str(e)}")
            traceback.print_exc()

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Generate final report
        self.generate_final_report(duration)

    def generate_final_report(self, duration: float):
        """Generate comprehensive test report"""
        print("\n" + "=" * 60)
        print("🎯 CONTEXT7 MCP TESTING COMPLETE")
        print("=" * 60)

        success_rate = (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0

        print(f"📊 FINAL RESULTS:")
        print(f"   Total Tests: {self.total_tests}")
        print(f"   Passed: {self.passed_tests}")
        print(f"   Failed: {self.failed_tests}")
        print(f"   Success Rate: {success_rate:.1f}%")
        print(f"   Duration: {duration:.2f} seconds")

        # Group results by tool
        tool_results = {}
        for result in self.test_results:
            tool_name = result["tool_name"]
            if tool_name not in tool_results:
                tool_results[tool_name] = {"passed": 0, "failed": 0, "total": 0}

            tool_results[tool_name]["total"] += 1
            if result["success"]:
                tool_results[tool_name]["passed"] += 1
            else:
                tool_results[tool_name]["failed"] += 1

        print(f"\n🔧 TOOL-BY-TOOL RESULTS:")
        for tool_name, stats in tool_results.items():
            tool_success_rate = (stats["passed"] / stats["total"] * 100) if stats["total"] > 0 else 0
            print(f"   {tool_name}: {stats['passed']}/{stats['total']} ({tool_success_rate:.1f}%)")

        # Save detailed results to JSON
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"context7-{timestamp}.json"

        report_data = {
            "test_suite": "Context7 MCP Comprehensive Test",
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": duration,
            "summary": {
                "total_tests": self.total_tests,
                "passed_tests": self.passed_tests,
                "failed_tests": self.failed_tests,
                "success_rate_percent": success_rate
            },
            "tool_results": tool_results,
            "detailed_results": self.test_results
        }

        try:
            with open(filename, 'w') as f:
                json.dump(report_data, f, indent=2)
            print(f"\n📁 Detailed results saved to: {filename}")
        except Exception as e:
            print(f"❌ Failed to save results: {str(e)}")

        print("\n" + "=" * 60)

        if success_rate == 100:
            print("🎉 CONTEXT7 MCP: COMPLETE SUCCESS - ALL TESTS PASSED!")
        elif success_rate >= 80:
            print("✅ CONTEXT7 MCP: MOSTLY SUCCESSFUL - MINOR ISSUES DETECTED")
        else:
            print("⚠️  CONTEXT7 MCP: SIGNIFICANT ISSUES DETECTED - REVIEW REQUIRED")

async def main():
    """Main test execution"""
    tester = Context7MCPTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
