#!/usr/bin/env python3
"""
Mock test for Ptolemies MCP Server
Simulates MCP server responses without requiring external dependencies
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, Any, List


class MockPtolemiesMCPServer:
    """Mock Ptolemies MCP server for testing"""

    def __init__(self):
        self.name = "ptolemies-mcp"
        self.version = "1.0.0"
        self.tools = [
            {
                "name": "ptolemies_health_check",
                "description": "Check health status of Ptolemies services"
            },
            {
                "name": "ptolemies_system_info",
                "description": "Get system information and capabilities"
            },
            {
                "name": "knowledge_create",
                "description": "Create new knowledge entry in the graph"
            },
            {
                "name": "knowledge_search",
                "description": "Search knowledge graph with semantic queries"
            },
            {
                "name": "knowledge_get",
                "description": "Retrieve specific knowledge entry by ID"
            },
            {
                "name": "vector_search",
                "description": "Perform vector similarity search"
            },
            {
                "name": "graph_query",
                "description": "Execute graph queries on Neo4j"
            },
            {
                "name": "surrealdb_query",
                "description": "Execute queries on SurrealDB"
            }
        ]

    async def initialize(self) -> Dict[str, Any]:
        """Initialize connection"""
        await asyncio.sleep(0.1)  # Simulate network delay
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": True,
                "resources": False,
                "prompts": False
            },
            "serverInfo": {
                "name": self.name,
                "version": self.version
            }
        }

    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools"""
        await asyncio.sleep(0.05)  # Simulate processing
        return self.tools

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool and return results"""
        start_time = time.time()

        # Simulate processing delay
        await asyncio.sleep(0.1)

        # Generate responses based on tool
        if tool_name == "ptolemies_health_check":
            response = {
                "status": "healthy",
                "components": {
                    "surrealdb": "connected",
                    "neo4j": "connected",
                    "vector_store": "ready"
                },
                "uptime": 3600,
                "version": self.version
            }

        elif tool_name == "ptolemies_system_info":
            response = {
                "version": self.version,
                "total_tools": len(self.tools),
                "capabilities": [
                    "knowledge_graph",
                    "vector_search",
                    "semantic_search",
                    "graph_queries"
                ],
                "databases": {
                    "surrealdb": {"status": "connected", "namespace": "ptolemies"},
                    "neo4j": {"status": "connected", "nodes": 1250}
                }
            }

        elif tool_name == "knowledge_search":
            query = arguments.get("query", "")
            response = {
                "results": [
                    {
                        "id": "kb_001",
                        "title": f"Result for: {query}",
                        "content": "Sample knowledge entry",
                        "score": 0.95,
                        "metadata": {"source": "test", "created": str(datetime.now())}
                    }
                ],
                "total": 1,
                "query": query
            }

        else:
            response = {
                "status": "success",
                "tool": tool_name,
                "arguments": arguments,
                "timestamp": str(datetime.now())
            }

        # Calculate response time
        response_time = (time.time() - start_time) * 1000

        return {
            "content": [{"text": json.dumps(response)}],
            "isError": False,
            "metadata": {
                "response_time_ms": response_time
            }
        }


async def test_ptolemies_mock():
    """Test Ptolemies MCP server with mock implementation"""

    print("🧪 Testing Ptolemies MCP Server (Mock)")
    print("=" * 50)

    # Create mock server
    server = MockPtolemiesMCPServer()

    try:
        # Test initialization
        print("🔌 Initializing connection...")
        init_result = await server.initialize()
        print(f"✅ Connected to {init_result['serverInfo']['name']} v{init_result['serverInfo']['version']}")
        print(f"   Protocol: {init_result['protocolVersion']}")

        # Test tool listing
        print("\n📋 Listing available tools...")
        tools = await server.list_tools()
        print(f"✅ Found {len(tools)} tools:")
        for tool in tools[:5]:
            print(f"   - {tool['name']}: {tool['description']}")
        if len(tools) > 5:
            print(f"   ... and {len(tools) - 5} more")

        # Test health check
        print("\n🏥 Testing health check...")
        health_result = await server.call_tool("ptolemies_health_check", {})
        health_data = json.loads(health_result["content"][0]["text"])
        print(f"✅ Health Status: {health_data['status']}")
        print(f"   Components: {', '.join(health_data['components'].keys())}")
        print(f"   Uptime: {health_data['uptime']}s")

        # Test system info
        print("\n📊 Testing system info...")
        info_result = await server.call_tool("ptolemies_system_info", {})
        info_data = json.loads(info_result["content"][0]["text"])
        print(f"✅ System Version: {info_data['version']}")
        print(f"   Total Tools: {info_data['total_tools']}")
        print(f"   Capabilities: {', '.join(info_data['capabilities'])}")

        # Test knowledge search
        print("\n🔍 Testing knowledge search...")
        search_result = await server.call_tool("knowledge_search", {"query": "test query"})
        search_data = json.loads(search_result["content"][0]["text"])
        print(f"✅ Search Results: {search_data['total']} found")
        print(f"   First result: {search_data['results'][0]['title']}")

        # Test response time
        print("\n⚡ Testing response times...")
        response_times = []

        for i in range(5):
            start = time.time()
            await server.call_tool("ptolemies_health_check", {})
            response_time = (time.time() - start) * 1000
            response_times.append(response_time)

        avg_response_time = sum(response_times) / len(response_times)
        print(f"✅ Average response time: {avg_response_time:.2f}ms")
        print(f"   Min: {min(response_times):.2f}ms")
        print(f"   Max: {max(response_times):.2f}ms")

        print("\n" + "="*50)
        print("✅ Ptolemies MCP Server: OPERATIONAL")
        print(f"   Version: {server.version}")
        print(f"   Tools: {len(tools)}")
        print(f"   Avg Response: {avg_response_time:.2f}ms")
        print("="*50)

        return True

    except Exception as e:
        print(f"\n❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import sys
    success = asyncio.run(test_ptolemies_mock())
    sys.exit(0 if success else 1)
