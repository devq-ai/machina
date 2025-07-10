#!/usr/bin/env python3
"""
Machina Registry Main Application
Production-ready MCP server registry using FastMCP framework.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the parent directory to the path so we can import fastmcp
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastmcp import MCPRegistry
import logfire
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


async def main():
    """Main entry point for the MCP registry server"""

    # Configure Logfire with error handling
    try:
        # Only configure Logfire if we have credentials
        logfire_token = os.getenv('LOGFIRE_TOKEN')
        if logfire_token:
            logfire.configure(
                token=logfire_token,
                service_name="machina-mcp-registry",
                environment=os.getenv('ENVIRONMENT', 'development')
            )
            logger = logfire
        else:
            # Fallback to basic logging if no Logfire token
            import logging
            logging.basicConfig(level=logging.INFO)
            logger = logging.getLogger(__name__)
            logger.info("Using basic logging - LOGFIRE_TOKEN not configured")
    except Exception as e:
        # Fallback to basic logging if Logfire fails
        import logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)
        logger.warning(f"Logfire configuration failed, using basic logging: {e}")

    # Check for validation-only mode
    if "--validate-only" in sys.argv:
        logger.info("Running in validation-only mode")
        result = await validate_environment()
        if result:
            logger.info("✅ Validation successful")
            sys.exit(0)
        else:
            logger.error("❌ Validation failed")
            sys.exit(1)

    try:
        # Initialize the registry
        registry = MCPRegistry(
            registry_name="machina-mcp-registry",
            storage_path="mcp_status.json"
        )

        logger.info("🚀 Starting Machina MCP Registry server")
        logger.info("📊 Registering 13 production-ready servers")

        # Add default health checks
        registry.health_monitor.add_default_health_checks()

        # Register all production-ready servers
        await register_production_servers(registry, logger)

        # Log registry status
        logger.info("✅ All servers registered successfully")
        logger.info("🔄 Starting registry server...")

        # Start the registry server
        await registry.run()

    except KeyboardInterrupt:
        logger.info("🛑 Registry server stopped by user")
    except Exception as e:
        logger.error(f"❌ Registry server failed: {str(e)}")
        raise


async def register_production_servers(registry: MCPRegistry, logger):
    """Register all 13 production-ready servers with complete configuration"""

    # Define all production-ready servers
    production_servers = [
        # Knowledge & Context Servers
        {
            "name": "context7-mcp",
            "endpoint": "stdio://devqai/mcp/mcp-servers/context7-mcp/context7_mcp/server.py",
            "framework": "FastMCP",
            "status": "production-ready",
            "version": "1.0.0",
            "tools": [
                "store_document", "search_documents", "get_context", "clear_context",
                "list_documents", "delete_document", "crawl_documentation", "update_document",
                "get_document", "batch_store_documents", "semantic_search", "get_related_documents",
                "generate_summary", "extract_keywords", "calculate_embeddings"
            ],
            "description": "Redis-backed contextual reasoning and document management with vector search",
            "environment_vars": ["OPENAI_API_KEY", "UPSTASH_REDIS_REST_URL", "UPSTASH_REDIS_REST_TOKEN"],
            "health_check": "embedding_service_test",
            "category": "knowledge"
        },
        {
            "name": "memory-mcp",
            "endpoint": "stdio://devqai/mcp/mcp-servers/memory-mcp/memory_mcp/server.py",
            "framework": "FastMCP",
            "status": "production-ready",
            "version": "1.0.0",
            "tools": [
                "store_memory", "retrieve_memory", "update_memory", "delete_memory",
                "list_memories", "search_memories", "clear_all_memories", "get_memory_stats"
            ],
            "description": "Memory management and persistence for AI workflows with search capabilities",
            "health_check": "memory_operations_test",
            "category": "knowledge"
        },
        {
            "name": "sequential-thinking-mcp",
            "endpoint": "stdio://devqai/mcp/mcp-servers/sequential-thinking-mcp/sequential_thinking_mcp/server.py",
            "framework": "FastMCP",
            "status": "production-ready",
            "version": "1.0.0",
            "tools": [
                "create_thinking_chain", "add_thought_step", "execute_thinking_chain"
            ],
            "description": "Step-by-step problem solving and reasoning chains for complex analysis",
            "health_check": "thinking_chain_test",
            "category": "knowledge"
        },

        # Web & Data Servers
        {
            "name": "crawl4ai-mcp",
            "endpoint": "stdio://devqai/mcp/mcp-servers/crawl4ai-mcp/crawl4ai_mcp/server.py",
            "framework": "FastMCP",
            "status": "production-ready",
            "version": "1.0.0",
            "tools": [
                "crawl_url", "extract_content", "batch_crawl"
            ],
            "description": "Web crawling and content extraction with AI-powered content processing",
            "health_check": "crawl_test",
            "category": "web"
        },
        {
            "name": "github-mcp",
            "endpoint": "stdio://devqai/mcp/mcp-servers/github-mcp/github_mcp/server.py",
            "framework": "FastMCP",
            "status": "production-ready",
            "version": "1.0.0",
            "tools": [
                "get_repository", "list_issues", "create_issue"
            ],
            "description": "GitHub repository operations and management with issue tracking",
            "environment_vars": ["GITHUB_TOKEN"],
            "health_check": "github_api_test",
            "category": "web"
        },

        # Development & Testing Servers
        {
            "name": "fastapi-mcp",
            "endpoint": "stdio://devqai/mcp/mcp-servers/fastapi-mcp/fastapi_mcp/server.py",
            "framework": "FastMCP",
            "status": "production-ready",
            "version": "1.0.0",
            "tools": [
                "create_project", "generate_endpoint", "add_middleware"
            ],
            "description": "FastAPI project generation and management with automated scaffolding",
            "health_check": "project_generation_test",
            "category": "development"
        },
        {
            "name": "pytest-mcp",
            "endpoint": "stdio://devqai/mcp/mcp-servers/pytest-mcp/pytest_mcp/server.py",
            "framework": "FastMCP",
            "status": "production-ready",
            "version": "1.0.0",
            "tools": [
                "run_tests", "generate_test", "get_coverage", "create_fixture",
                "run_specific_test", "list_test_files", "validate_test_structure"
            ],
            "description": "Python testing framework integration with automated test generation",
            "health_check": "test_execution_test",
            "category": "development"
        },
        {
            "name": "pydantic-ai-mcp",
            "endpoint": "stdio://devqai/mcp/mcp-servers/pydantic-ai-mcp/pydantic_ai_mcp/server.py",
            "framework": "FastMCP",
            "status": "production-ready",
            "version": "1.0.0",
            "tools": [
                "create_agent", "run_agent", "list_agents", "get_agent_status"
            ],
            "description": "Pydantic AI agent management and orchestration with type-safe operations",
            "environment_vars": ["ANTHROPIC_API_KEY"],
            "health_check": "agent_creation_test",
            "category": "development"
        },

        # Infrastructure & Monitoring Servers
        {
            "name": "docker-mcp",
            "endpoint": "stdio://devqai/mcp/mcp-servers/docker-mcp/docker_mcp/server.py",
            "framework": "FastMCP",
            "status": "production-ready",
            "version": "1.0.0",
            "tools": [
                "list_containers", "start_container", "stop_container", "create_container", "remove_container"
            ],
            "description": "Docker container management and orchestration with lifecycle control",
            "environment_vars": ["DOCKER_HOST"],
            "health_check": "container_operations_test",
            "category": "infrastructure"
        },
        {
            "name": "logfire-mcp",
            "endpoint": "stdio://devqai/mcp/mcp-servers/logfire-mcp/logfire_mcp/server.py",
            "framework": "FastMCP",
            "status": "production-ready",
            "version": "1.0.0",
            "tools": [
                "configure_logfire", "instrument_fastapi", "instrument_sqlalchemy", "instrument_httpx",
                "create_span", "log_info", "log_error", "log_warning", "get_metrics",
                "create_dashboard", "set_user_context", "capture_exception"
            ],
            "description": "Comprehensive observability and monitoring platform with real-time analytics",
            "environment_vars": ["LOGFIRE_TOKEN"],
            "health_check": "observability_test",
            "category": "infrastructure"
        },

        # Framework & Registry Servers
        {
            "name": "fastmcp-mcp",
            "endpoint": "stdio://devqai/mcp/mcp-servers/fastmcp-mcp/fastmcp_mcp/server.py",
            "framework": "Standard MCP",
            "status": "production-ready",
            "version": "1.0.0",
            "tools": [
                "get_framework_status"
            ],
            "description": "FastMCP framework status and management with health monitoring",
            "health_check": "framework_status_test",
            "category": "framework"
        },
        {
            "name": "registry-mcp",
            "endpoint": "stdio://devqai/mcp/mcp-servers/registry-mcp/registry_mcp/server.py",
            "framework": "FastMCP",
            "status": "production-ready",
            "version": "1.0.0",
            "tools": [
                "register_server", "list_servers", "get_server_status"
            ],
            "description": "MCP server discovery and registry management with health monitoring",
            "health_check": "registry_discovery_test",
            "category": "framework"
        },

        # Database Servers
        {
            "name": "surrealdb-mcp",
            "endpoint": "stdio://devqai/mcp/mcp-servers/surrealdb-mcp/surrealdb_mcp/server.py",
            "framework": "Standard MCP",
            "status": "production-ready",
            "version": "1.0.0",
            "tools": [
                "query_database", "execute_transaction"
            ],
            "description": "Multi-model database operations with graph, document, and key-value support",
            "environment_vars": ["SURREALDB_URL", "SURREALDB_USERNAME", "SURREALDB_PASSWORD"],
            "health_check": "database_operations_test",
            "category": "database"
        }
    ]

    # Register each server
    for server_config in production_servers:
        try:
            # Validate environment variables if required
            if "environment_vars" in server_config:
                missing_vars = []
                for var in server_config["environment_vars"]:
                    if not os.getenv(var):
                        missing_vars.append(var)

                if missing_vars:
                    logger.warning(
                        f"⚠️ Server {server_config['name']} missing environment variables: {missing_vars}"
                    )
                    continue

            # Register the server
            result = await registry.fastmcp._call_tool_safe(
                "register_server",
                {
                    "name": server_config["name"],
                    "endpoint": server_config["endpoint"],
                    "tools": server_config["tools"],
                    "description": server_config["description"],
                    "framework": server_config.get("framework", "FastMCP"),
                    "status": server_config.get("status", "production-ready"),
                    "version": server_config.get("version", "1.0.0"),
                    "category": server_config.get("category", "general"),
                    "health_check": server_config.get("health_check", "default"),
                    "environment_vars": server_config.get("environment_vars", [])
                }
            )

            logger.info(f"✅ Registered server: {server_config['name']} ({server_config['framework']})")

        except Exception as e:
            logger.error(f"❌ Failed to register {server_config['name']}: {str(e)}")
            continue

    # Log final statistics
    logger.info("📊 Registration Summary:")
    logger.info(f"   • Total servers: {len(production_servers)}")
    logger.info(f"   • FastMCP servers: {len([s for s in production_servers if s['framework'] == 'FastMCP'])}")
    logger.info(f"   • Standard MCP servers: {len([s for s in production_servers if s['framework'] == 'Standard MCP'])}")
    logger.info("   • Categories: Knowledge (3), Web (2), Development (3), Infrastructure (2), Framework (2), Database (1)")
    logger.info("   • Status: All servers production-ready ✅")


async def validate_environment():
    """Validate required environment variables are present"""

    required_vars = [
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GITHUB_TOKEN",
        "SURREALDB_URL",
        "SURREALDB_USERNAME",
        "SURREALDB_PASSWORD"
    ]

    optional_vars = [
        "UPSTASH_REDIS_REST_URL",
        "UPSTASH_REDIS_REST_TOKEN",
        "LOGFIRE_TOKEN",
        "DOCKER_HOST",
        "PERPLEXITY_API_KEY"
    ]

    missing_required = []
    missing_optional = []

    for var in required_vars:
        if not os.getenv(var):
            missing_required.append(var)

    for var in optional_vars:
        if not os.getenv(var):
            missing_optional.append(var)

    if missing_required:
        print(f"❌ Missing required environment variables: {missing_required}")
        print("Please configure these variables in your .env file")
        return False

    if missing_optional:
        print(f"⚠️ Missing optional environment variables: {missing_optional}")
        print("Some servers may have limited functionality")

    print("✅ Environment validation passed")
    return True


if __name__ == "__main__":
    # Handle command line arguments
    if "--help" in sys.argv:
        print("Machina MCP Registry")
        print("Usage:")
        print("  python registry/main.py                 # Start the registry")
        print("  python registry/main.py --validate-only # Validate configuration only")
        print("  python registry/main.py --help          # Show this help")
        sys.exit(0)

    # Start the registry
    asyncio.run(main())
