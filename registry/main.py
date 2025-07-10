#!/usr/bin/env python3
"""
Machina Registry Main Application
Production-ready MCP server registry using FastMCP framework.
"""

import asyncio
import sys
from pathlib import Path

# Add the parent directory to the path so we can import fastmcp
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastmcp import MCPRegistry
import logfire


async def main():
    """Main entry point for the MCP registry server"""

    # Configure Logfire
    logfire.configure()
    logger = logfire

    try:
        # Initialize the registry
        registry = MCPRegistry(
            registry_name="machina-mcp-registry",
            storage_path="mcp_status.json"
        )

        logger.info("Starting Machina MCP Registry server")

        # Add default health checks
        registry.health_monitor.add_default_health_checks()

        # Register some example servers for testing
        await register_example_servers(registry)

        # Start the registry server
        await registry.run()

    except KeyboardInterrupt:
        logger.info("Registry server stopped by user")
    except Exception as e:
        logger.error(f"Registry server failed: {str(e)}")
        raise


async def register_example_servers(registry: MCPRegistry):
    """Register example servers for demonstration"""

    # Register existing MCP servers from the primer directory
    example_servers = [
        {
            "name": "bayes-mcp",
            "endpoint": "stdio://primer/mcp_implementations/bayes_mcp.py",
            "tools": ["bayes_theorem", "update_belief", "credible_interval", "beta_distribution", "normal_distribution", "hypothesis_test", "ab_test_analysis"],
            "description": "Bayesian inference and statistical analysis"
        },
        {
            "name": "darwin-mcp",
            "endpoint": "stdio://primer/mcp_implementations/darwin_mcp.py",
            "tools": ["create_population", "run_evolution", "get_fitness", "genetic_crossover", "genetic_mutation", "selection_tournament", "get_best_individual", "get_population_stats", "visualize_evolution"],
            "description": "Genetic algorithm platform"
        },
        {
            "name": "docker-mcp",
            "endpoint": "stdio://primer/mcp_implementations/docker_mcp.py",
            "tools": ["list_containers", "create_container", "start_container", "stop_container", "remove_container", "get_container_logs", "get_container_stats", "pull_image", "list_images", "remove_image", "build_image", "create_network", "list_networks", "remove_network"],
            "description": "Docker container management"
        },
        {
            "name": "fastmcp-mcp",
            "endpoint": "stdio://primer/mcp_implementations/fastmcp_mcp.py",
            "tools": ["generate_fastapi_app", "create_mcp_endpoint", "add_middleware", "create_database_model", "generate_crud_operations", "add_authentication", "create_test_suite", "deploy_to_cloud"],
            "description": "FastAPI application framework generator"
        }
    ]

    for server_config in example_servers:
        # Use the registry's register_server tool
        await registry.fastmcp._call_tool_safe(
            "register_server",
            {
                "name": server_config["name"],
                "endpoint": server_config["endpoint"],
                "tools": server_config["tools"],
                "description": server_config["description"]
            }
        )

        logfire.info(f"Registered example server: {server_config['name']}")


if __name__ == "__main__":
    asyncio.run(main())
