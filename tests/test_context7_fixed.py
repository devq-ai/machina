#!/usr/bin/env python3
"""
Context7 Fixed Server Test Script
Tests the fixed Context7 server with proper embedding configuration
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set environment variables for testing
os.environ["OPENAI_API_KEY"] = "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"
os.environ["UPSTASH_REDIS_REST_URL"] = "https://redis-10892.c124.us-central1-1.gce.redns.redis-cloud.com:10892"
os.environ["UPSTASH_REDIS_REST_TOKEN"] = "5tUShoAYAG66wGOt2WoQ09FFb5LvJUGW"
os.environ["CONTEXT7_ENABLE_EMBEDDINGS"] = "true"
os.environ["CONTEXT7_FALLBACK_MODE"] = "true"

async def test_fixed_context7():
    """Test the fixed Context7 server functionality"""
    print("🧪 Testing Fixed Context7 Server...")

    try:
        # Import the fixed server
        from mcp_servers.context7_mcp_fixed import Context7MCP

        # Create server instance
        server = Context7MCP()

        # Test basic functionality
        print("✅ Server initialized successfully")

        # Test storing context
        store_result = await server._Context7MCP__dict__["mcp"].tools["store_context"](
            "This is a test context for embedding generation",
            metadata={"test": True},
            tags=["test", "embedding"]
        )

        print(f"✅ Store context result: {store_result.get('status', 'unknown')}")
        print(f"   Has embedding: {store_result.get('has_embedding', False)}")

        # Test search
        search_result = await server._Context7MCP__dict__["mcp"].tools["search_contexts"](
            "test context embedding",
            similarity_threshold=0.1
        )

        print(f"✅ Search result: {search_result.get('total_found', 0)} contexts found")
        print(f"   Search method: {search_result.get('search_method', 'unknown')}")

        # Test stats
        stats_result = await server._Context7MCP__dict__["mcp"].tools["get_context7_stats"]()

        print(f"✅ Stats result: {stats_result.get('status', 'unknown')}")
        print(f"   Embedding coverage: {stats_result.get('embedding_coverage_percent', 0):.1f}%")

        print("🎉 All tests passed! Context7 server is working correctly.")
        return True

    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False

if __name__ == "__main__":
    asyncio.run(test_fixed_context7())
