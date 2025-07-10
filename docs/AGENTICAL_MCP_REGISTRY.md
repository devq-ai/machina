# Machina MCP Registry for Agentical

## Overview

The Machina MCP Registry provides a centralized platform for managing and accessing Model Context Protocol (MCP) servers within the Agentical AI agent orchestration platform. This registry offers 13 production-ready MCP servers spanning knowledge management, development tools, infrastructure monitoring, and database operations.

## Quick Start

### 1. Registry Startup

```bash
# Navigate to the registry
cd /Users/dionedge/devqai/machina

# Validate environment and run tests
python test_registry.py

# Start the registry server
python registry/main.py
```

### 2. Registry Status Check

```bash
# Quick health check
python -c "
import asyncio
import sys
sys.path.insert(0, '.')
from registry.main import validate_environment
result = asyncio.run(validate_environment())
print('✅ Registry Ready' if result else '❌ Configuration Issues')
"
```

## Available MCP Servers

### Knowledge & Context Servers

| Server | Tools | Description |
|--------|-------|-------------|
| **context7-mcp** | 15 | Redis-backed contextual reasoning and document management with vector search |
| **memory-mcp** | 8 | Memory management and persistence for AI workflows with search capabilities |
| **sequential-thinking-mcp** | 3 | Step-by-step problem solving and reasoning chains for complex analysis |

### Web & Data Servers

| Server | Tools | Description |
|--------|-------|-------------|
| **crawl4ai-mcp** | 3 | Web crawling and content extraction with AI processing capabilities |
| **github-mcp** | 3 | GitHub repository operations and management with full API access |

### Development & Testing Servers

| Server | Tools | Description |
|--------|-------|-------------|
| **fastapi-mcp** | 3 | FastAPI project generation and management with DevQ.ai standards |
| **pytest-mcp** | 7 | Python testing framework integration and test management |
| **pydantic-ai-mcp** | 4 | Pydantic AI agent management and orchestration with type safety |

### Infrastructure & Monitoring Servers

| Server | Tools | Description |
|--------|-------|-------------|
| **docker-mcp** | 5 | Docker container management and orchestration with lifecycle control |
| **logfire-mcp** | 12 | Comprehensive observability and monitoring platform with real-time analytics |

### Framework & Registry Servers

| Server | Tools | Description |
|--------|-------|-------------|
| **fastmcp-mcp** | 1 | FastMCP framework status and management for server coordination |
| **registry-mcp** | 3 | MCP server discovery and registry management with health monitoring |

### Database Servers

| Server | Tools | Description |
|--------|-------|-------------|
| **surrealdb-mcp** | 2 | Multi-model database operations and management with vector capabilities |

## Selective Server Subscription

### Method 1: Environment-Based Selection

Create selective environment configurations to enable only specific servers:

```bash
# Create a minimal environment for knowledge servers only
cat > .env.knowledge << EOF
# Core Requirements
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# Knowledge Server Requirements
UPSTASH_REDIS_REST_URL=https://...
UPSTASH_REDIS_REST_TOKEN=...

# Disable other services (optional)
# GITHUB_TOKEN=
# DOCKER_HOST=
# LOGFIRE_TOKEN=
EOF

# Use selective environment
cp .env.knowledge .env
python registry/main.py
```

### Method 2: Configuration-Based Selection

Modify the registry configuration to load only specific servers:

```python
# Create selective_registry.py
import asyncio
import sys
sys.path.insert(0, '.')
from fastmcp import MCPRegistry
from registry.main import validate_environment
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def register_selective_servers(registry: MCPRegistry, server_names: list):
    """Register only specified servers"""

    # Define server configurations (subset of production servers)
    server_configs = {
        "context7-mcp": {
            "name": "context7-mcp",
            "endpoint": "stdio://devqai/mcp/mcp-servers/context7-mcp/context7_mcp/server.py",
            "framework": "FastMCP",
            "tools": ["store_document", "search_documents", "get_context"],
            "description": "Redis-backed contextual reasoning",
            "environment_vars": ["OPENAI_API_KEY", "UPSTASH_REDIS_REST_URL"]
        },
        "memory-mcp": {
            "name": "memory-mcp",
            "endpoint": "stdio://devqai/mcp/mcp-servers/memory-mcp/memory_mcp/server.py",
            "framework": "FastMCP",
            "tools": ["store_memory", "retrieve_memory", "search_memories"],
            "description": "Memory management for AI workflows",
            "environment_vars": []
        },
        "pytest-mcp": {
            "name": "pytest-mcp",
            "endpoint": "stdio://devqai/mcp/mcp-servers/pytest-mcp/pytest_mcp/server.py",
            "framework": "FastMCP",
            "tools": ["run_tests", "generate_test", "test_coverage"],
            "description": "Python testing framework integration",
            "environment_vars": []
        }
    }

    # Register only requested servers
    for server_name in server_names:
        if server_name in server_configs:
            config = server_configs[server_name]
            result = await registry.fastmcp._call_tool_safe("register_server", config)
            logger.info(f"✅ Registered: {server_name}")
        else:
            logger.warning(f"⚠️ Server not found: {server_name}")

async def main():
    # Validate environment
    if not await validate_environment():
        print("❌ Environment validation failed")
        return

    # Create registry
    registry = MCPRegistry()

    # Register selective servers (customize this list)
    selected_servers = ["context7-mcp", "memory-mcp", "pytest-mcp"]
    await register_selective_servers(registry, selected_servers)

    print(f"✅ Registry started with {len(selected_servers)} servers")

    # Start the server
    await registry.run()

if __name__ == "__main__":
    asyncio.run(main())
```

### Method 3: Runtime Server Management

Use the registry's built-in tools to manage servers dynamically:

```python
# server_manager.py - Runtime server management
import asyncio
from fastmcp import MCPRegistry

async def manage_servers():
    registry = MCPRegistry()

    # List all registered servers
    servers = await registry.fastmcp._call_tool_safe("list_servers", {})
    print("📋 Registered servers:", servers)

    # Get specific server info
    server_info = await registry.fastmcp._call_tool_safe(
        "get_server_info",
        {"name": "context7-mcp"}
    )
    print("🔍 Server details:", server_info)

    # Unregister a server
    await registry.fastmcp._call_tool_safe(
        "unregister_server",
        {"name": "docker-mcp"}
    )
    print("❌ Unregistered docker-mcp")

    # Check registry status
    status = await registry.fastmcp._call_tool_safe("get_registry_status", {})
    print("📊 Registry status:", status)

# Run server management
asyncio.run(manage_servers())
```

## Environment Configuration

### Required Environment Variables

```bash
# Core API Keys (Required for most servers)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# Database Configuration
SURREALDB_URL=ws://localhost:8000/rpc
SURREALDB_USERNAME=root
SURREALDB_PASSWORD=root
```

### Optional Environment Variables

```bash
# GitHub Integration
GITHUB_TOKEN=ghp_...

# Redis/Context7 Integration
UPSTASH_REDIS_REST_URL=https://...
UPSTASH_REDIS_REST_TOKEN=...

# Infrastructure Monitoring
LOGFIRE_TOKEN=pylf_v1_us_...
DOCKER_HOST=unix:///var/run/docker.sock

# Advanced Features
PERPLEXITY_API_KEY=pplx-...
```

## Integration with Agentical

### 1. Agent Configuration

Configure Agentical agents to use specific MCP servers:

```python
# agentical_mcp_config.py
from pydantic_ai import Agent
import logfire

# Configure agent with MCP server access
@logfire.instrument()
class AgenticalMCPAgent:
    """Agentical agent with MCP server integration"""

    def __init__(self, mcp_servers: list = None):
        self.mcp_servers = mcp_servers or [
            "context7-mcp",      # For document management
            "memory-mcp",        # For persistent memory
            "pytest-mcp",        # For testing integration
            "logfire-mcp"        # For observability
        ]

        self.agent = Agent(
            'claude-3-7-sonnet-20250219',
            system_prompt=f"""You are an Agentical agent with access to MCP servers: {', '.join(self.mcp_servers)}.

            Available capabilities:
            - Document storage and retrieval via context7-mcp
            - Memory management via memory-mcp
            - Test execution via pytest-mcp
            - Performance monitoring via logfire-mcp

            Use these tools to enhance your capabilities."""
        )

    async def process_with_mcp(self, task: str) -> dict:
        """Process task using available MCP servers"""
        with logfire.span("Agentical MCP Task", task=task):
            # Use MCP servers through the registry
            result = await self.agent.run(task)
            return result
```

### 2. Workflow Integration

```python
# agentical_workflow.py
import asyncio
from agentical import WorkflowOrchestrator
from fastmcp import MCPRegistry

async def agentical_mcp_workflow():
    """Example Agentical workflow using MCP servers"""

    # Initialize MCP registry
    registry = MCPRegistry()

    # Initialize Agentical orchestrator
    orchestrator = WorkflowOrchestrator()

    # Define workflow with MCP integration
    workflow = {
        "steps": [
            {
                "name": "document_analysis",
                "mcp_server": "context7-mcp",
                "tools": ["search_documents", "get_context"]
            },
            {
                "name": "memory_storage",
                "mcp_server": "memory-mcp",
                "tools": ["store_memory", "retrieve_memory"]
            },
            {
                "name": "test_validation",
                "mcp_server": "pytest-mcp",
                "tools": ["run_tests", "test_coverage"]
            }
        ]
    }

    # Execute workflow
    results = await orchestrator.execute_workflow(workflow)
    return results
```

## Registry Management

### Start Registry

```bash
# Full registry with all servers
python registry/main.py

# Selective registry (using custom script)
python selective_registry.py

# Background mode
nohup python registry/main.py > registry.log 2>&1 &
```

### Stop Registry

```bash
# Find and stop registry process
ps aux | grep "registry/main.py" | grep -v grep
kill <PID>

# Or use pkill
pkill -f "registry/main.py"
```

### Monitor Registry

```bash
# Check registry health
python test_registry.py

# View logs
tail -f registry.log

# Monitor with Logfire (if configured)
# View dashboard at: https://logfire-us.pydantic.dev/devq-ai/devq-ai
```

## Troubleshooting

### Common Issues

1. **Registry Won't Start**
   ```bash
   # Check environment variables
   python -c "import os; print([k for k in ['ANTHROPIC_API_KEY', 'OPENAI_API_KEY'] if not os.getenv(k)])"

   # Validate configuration
   python -c "
   import asyncio, sys
   sys.path.insert(0, '.')
   from registry.main import validate_environment
   print('✅ OK' if asyncio.run(validate_environment()) else '❌ Issues')
   "
   ```

2. **Server Registration Errors**
   ```bash
   # Test individual server registration
   python -c "
   import asyncio, sys, logging
   sys.path.insert(0, '.')
   from fastmcp import MCPRegistry
   from registry.main import register_production_servers

   async def test():
       registry = MCPRegistry()
       logger = logging.getLogger()
       await register_production_servers(registry, logger)

   asyncio.run(test())
   "
   ```

3. **Missing Environment Variables**
   ```bash
   # Check which servers need which variables
   python -c "
   import yaml
   with open('tests/master_mcp-server.yaml') as f:
       config = yaml.safe_load(f)
       for name, server in config['servers'].items():
           env_vars = server.get('environment_vars', [])
           if env_vars:
               print(f'{name}: {env_vars}')
   "
   ```

### Health Checks

```bash
# Registry health check
python -c "
import asyncio, sys
sys.path.insert(0, '.')
from fastmcp import MCPRegistry

async def health_check():
    registry = MCPRegistry()
    result = await registry.fastmcp._call_tool_safe('health_check', {})
    print('Health Status:', result)

asyncio.run(health_check())
"
```

## Best Practices

### 1. Environment Management
- Use separate `.env` files for different environments (dev, staging, prod)
- Keep sensitive API keys secure and never commit to version control
- Validate environment before starting registry

### 2. Server Selection
- Start with core servers (context7, memory, pytest) for development
- Add infrastructure servers (docker, logfire) for production
- Use selective registration for testing and development

### 3. Monitoring
- Enable Logfire for production observability
- Monitor registry health with regular health checks
- Use background processes for production deployments

### 4. Integration
- Configure Agentical agents to use appropriate MCP servers
- Implement proper error handling for MCP server failures
- Use registry tools for dynamic server management

---

**Registry Status**: ✅ 13/13 servers production-ready
**Documentation**: Updated January 15, 2025
**Support**: See `TESTING_GUIDE.md` for comprehensive testing procedures
