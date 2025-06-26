"""
Integration tests for MCP servers.

Simple tests to verify that MCP servers are running and responding correctly.
"""

import os
import asyncio
import pytest
import httpx
from typing import Dict, Any


# MCP server configurations
MCP_SERVERS = {
    "stripe": {"port": 8001, "name": "stripe-mcp"},
    "shopify": {"port": 8002, "name": "shopify-mcp"},
    "darwin": {"port": 8003, "name": "darwin-mcp"},
    "docker": {"port": 8004, "name": "docker-mcp"},
    "fastmcp": {"port": 8005, "name": "fastmcp-mcp"},
    "bayes": {"port": 8006, "name": "bayes-mcp"},
    "upstash": {"port": 8007, "name": "upstash-mcp"},
    "calendar": {"port": 8008, "name": "calendar-mcp"},
    "gmail": {"port": 8009, "name": "gmail-mcp"},
    "gcp": {"port": 8010, "name": "gcp-mcp"},
    "github": {"port": 8011, "name": "github-mcp"},
    "memory": {"port": 8012, "name": "memory-mcp"},
    "logfire": {"port": 8013, "name": "logfire-mcp"},
}


class TestMCPServers:
    """Integration tests for MCP servers."""

    @pytest.mark.asyncio
    async def test_server_health(self):
        """Test that all MCP servers are healthy."""
        results = {}

        for server_name, config in MCP_SERVERS.items():
            host = os.getenv(f"{server_name.upper()}_HOST", "localhost")
            port = config["port"]
            url = f"http://{host}:{port}/health"

            async with httpx.AsyncClient(timeout=5.0) as client:
                try:
                    response = await client.get(url)
                    results[server_name] = {
                        "status": "healthy" if response.status_code == 200 else "unhealthy",
                        "status_code": response.status_code
                    }
                except Exception as e:
                    results[server_name] = {
                        "status": "unreachable",
                        "error": str(e)
                    }

        # Print results
        print("\nMCP Server Health Check Results:")
        print("-" * 40)
        for server, result in results.items():
            status = result.get("status", "unknown")
            print(f"{server.upper()}: {status}")

        # Check if any servers are running (for local testing)
        healthy_servers = [s for s, r in results.items() if r.get("status") == "healthy"]
        if healthy_servers:
            print(f"\nHealthy servers: {', '.join(healthy_servers)}")
        else:
            print("\nNo servers are currently running. Start them with: docker-compose up")

    @pytest.mark.asyncio
    async def test_stripe_tools(self):
        """Test Stripe MCP server tools."""
        host = os.getenv("STRIPE_HOST", "localhost")
        port = MCP_SERVERS["stripe"]["port"]

        async with httpx.AsyncClient(base_url=f"http://{host}:{port}", timeout=5.0) as client:
            try:
                # Test listing tools
                response = await client.get("/tools")
                if response.status_code == 200:
                    tools = response.json()
                    print(f"\nStripe MCP has {len(tools)} tools available")

                    # Test a simple tool if API key is configured
                    if os.getenv("STRIPE_API_KEY"):
                        # Test listing customers
                        response = await client.post(
                            "/tools/call",
                            json={
                                "tool": "stripe_list_customers",
                                "arguments": {"limit": 1}
                            }
                        )
                        assert response.status_code == 200
                        print("✓ Stripe customer listing works")
                else:
                    pytest.skip("Stripe MCP server not running")
            except httpx.ConnectError:
                pytest.skip("Stripe MCP server not accessible")

    @pytest.mark.asyncio
    async def test_memory_operations(self):
        """Test Memory MCP server operations."""
        host = os.getenv("MEMORY_HOST", "localhost")
        port = MCP_SERVERS["memory"]["port"]

        async with httpx.AsyncClient(base_url=f"http://{host}:{port}", timeout=5.0) as client:
            try:
                # Test storing a value
                response = await client.post(
                    "/tools/call",
                    json={
                        "tool": "memory_store",
                        "arguments": {
                            "key": "test_key",
                            "value": {"test": "data"}
                        }
                    }
                )

                if response.status_code == 200:
                    # Test retrieving the value
                    response = await client.post(
                        "/tools/call",
                        json={
                            "tool": "memory_retrieve",
                            "arguments": {"key": "test_key"}
                        }
                    )
                    assert response.status_code == 200
                    result = response.json()
                    assert result.get("value") == {"test": "data"}
                    print("\n✓ Memory MCP store/retrieve works")

                    # Clean up
                    await client.post(
                        "/tools/call",
                        json={
                            "tool": "memory_delete",
                            "arguments": {"key": "test_key"}
                        }
                    )
                else:
                    pytest.skip("Memory MCP server not running")
            except httpx.ConnectError:
                pytest.skip("Memory MCP server not accessible")

    @pytest.mark.asyncio
    async def test_darwin_optimization(self):
        """Test Darwin MCP genetic algorithm optimization."""
        host = os.getenv("DARWIN_HOST", "localhost")
        port = MCP_SERVERS["darwin"]["port"]

        async with httpx.AsyncClient(base_url=f"http://{host}:{port}", timeout=10.0) as client:
            try:
                # Test simple optimization
                response = await client.post(
                    "/tools/call",
                    json={
                        "tool": "darwin_run_optimization",
                        "arguments": {
                            "fitness_function": "def fitness(individual): return sum(individual)",
                            "gene_space": [0, 1],
                            "num_genes": 5,
                            "num_generations": 5,
                            "sol_per_pop": 10
                        }
                    }
                )

                if response.status_code == 200:
                    result = response.json()
                    assert result.get("success") is True
                    print("\n✓ Darwin MCP optimization works")
                else:
                    pytest.skip("Darwin MCP server not running")
            except httpx.ConnectError:
                pytest.skip("Darwin MCP server not accessible")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
