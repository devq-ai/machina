# Machina - DevQ.ai MCP Registry & Management Platform

**Machina** is DevQ.ai's unified MCP (Model Context Protocol) Registry and Management Platform that orchestrates 46 MCP servers across the DevQ.ai ecosystem.

## Overview

Machina solves the critical problem of MCP server fragmentation by providing:

- 🏗️ **Centralized Registry** - Discovery and management of all 46 MCP servers
- 🔍 **Health Monitoring** - 99.9% uptime through continuous health checks and failover
- ⚙️ **Configuration Management** - Web UI for setting REQUIRED/BUILD_PRIORITY flags
- 🔌 **Dual Protocol Support** - Both MCP protocol and REST API access
- 📊 **JSON Status API** - Real-time status reporting for external integration
- 🐳 **Docker Deployment** - Production-ready containerized architecture

## Quick Start

### Development Setup

```bash
# Clone and setup
cd /Users/dionedge/devqai/machina
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start development environment
docker-compose up -d

# Access services
# - Registry API: http://localhost:8000
# - Configuration UI: http://localhost:8000/ui
# - Health Dashboard: http://localhost:8000/health
# - API Documentation: http://localhost:8000/docs
```

### Production Deployment

```bash
# Deploy to Kubernetes
kubectl apply -f k8s/
helm install machina ./helm/

# Access production
# - https://machina.devq.ai
# - https://machina.devq.ai/api/health/status.json
```

## Architecture

### Service Categories

**✅ FastMCP (35 servers)** - Simple tools and utilities
- 9 Already implemented (context7-mcp, crawl4ai-mcp, etc.)
- 2 Ready for conversion (bayes-mcp, darwin-mcp)
- 8 External integrations (stripe-mcp, redis-mcp, etc.)
- 16 New implementations

**🏗️ FastAPI (11 servers)** - Complex services with web interfaces
- ptolemies-mcp-server (temporal knowledge graph)
- jupyter-mcp, logfire-mcp, bigquery-mcp, etc.

**🔄 External (8 servers)** - Third-party integrations
- Official MCP servers and service providers

**🔧 Conversion (2 servers)** - Existing DevQ.ai projects
- Bayes and Darwin projects → MCP servers

### Core Components

1. **Registry Service** (`src/registry/`) - FastAPI + FastMCP hybrid
2. **Service Discovery** (`src/discovery/`) - Automatic service detection
3. **Health Monitor** (`src/monitoring/`) - Continuous health checking
4. **Configuration UI** (`src/ui/`) - Web interface for management
5. **Docker Stack** (`docker/`) - Multi-container deployment

## API Reference

### Service Discovery
```bash
# List all services
curl https://machina.devq.ai/api/services

# Filter by build type
curl https://machina.devq.ai/api/services/by-type/fastmcp

# Get service health
curl https://machina.devq.ai/api/health/context7-mcp
```

### Configuration Management
```bash
# Update service configuration
curl -X PUT https://machina.devq.ai/api/services/context7-mcp/config \
  -H "Content-Type: application/json" \
  -d '{"required": true, "build_priority": "HIGH"}'

# Get JSON status for monitoring
curl https://machina.devq.ai/api/health/status.json
```

### MCP Protocol Access
```python
from mcp import Client

# Connect to registry
client = Client("ws://machina.devq.ai/mcp")

# List available tools
tools = await client.call_tool("list_available_services")

# Call service tool
result = await client.call_tool("call_service_tool", 
    service="context7-mcp", 
    tool="semantic_search", 
    query="FastAPI patterns"
)
```

## Development

### Required Configuration Files

Machina follows DevQ.ai's five-component stack:

1. **FastAPI Foundation** - Core web framework
2. **Logfire Observability** - Complete monitoring
3. **PyTest Build-to-Test** - 90% test coverage required
4. **TaskMaster AI** - Project management
5. **MCP Integration** - AI-powered development

### File Structure
```
machina/
├── .claude/settings.local.json    # Claude Code configuration
├── .zed/settings.json             # Zed IDE integration
├── src/
│   ├── registry/                  # Core registry service
│   ├── discovery/                 # Service discovery
│   ├── monitoring/               # Health monitoring
│   ├── ui/                       # Configuration interface
│   └── models/                   # Data models
├── tests/                        # Test suites
├── docker/                       # Container definitions
├── k8s/                         # Kubernetes manifests
└── docs/                        # Documentation
```

### Testing

```bash
# Run all tests with coverage
pytest tests/ --cov=src/ --cov-report=html

# Run specific test suites
pytest tests/test_registry.py -v
pytest tests/test_discovery.py -v
pytest tests/test_monitoring.py -v

# Integration tests
pytest tests/integration/ -v
```

### Quality Standards

- **Coverage**: Minimum 90% test coverage
- **Formatting**: Black formatter (88 char limit)
- **Type Hints**: Required for all functions
- **Documentation**: Google-style docstrings
- **Logging**: Complete Logfire integration

## Roadmap

### Phase 1: MVP Core Registry (Week 1-2)
- [x] Service discovery for existing 9 MCP servers
- [x] Basic REST API and health checks
- [ ] Docker development environment
- [ ] Core database schema

### Phase 2: Configuration UI (Week 3)
- [ ] Single-page web interface
- [ ] REQUIRED/BUILD_PRIORITY configuration
- [ ] Real-time updates via WebSocket
- [ ] Service filtering and search

### Phase 3: External Integration (Week 4)
- [ ] 8 external service integrations
- [ ] Third-party API connections
- [ ] External health monitoring
- [ ] Configuration templates

### Phase 4: Project Conversion (Week 5)
- [ ] Bayes → bayes-mcp conversion
- [ ] Darwin → darwin-mcp conversion
- [ ] Conversion framework
- [ ] Automated deployment

### Phase 5: Advanced Monitoring (Week 6)
- [ ] Background health monitoring
- [ ] Automatic failover
- [ ] Performance metrics
- [ ] Alert system

### Phase 6: Production Deployment (Week 7-8)
- [ ] Kubernetes deployment
- [ ] All 46 services implemented
- [ ] Performance optimization
- [ ] Documentation completion

## Contributing

1. Follow DevQ.ai development standards
2. Maintain 90% test coverage
3. Use TaskMaster AI for task management
4. Include Logfire monitoring in all code
5. Follow the established project patterns

## Support

- **Documentation**: See `/docs/` directory
- **Issues**: Use GitHub issues for bug reports
- **Development**: Follow DevQ.ai coding standards
- **Monitoring**: Check Logfire dashboards for system health

---

**Status**: 🏗️ Active Development
**Current Phase**: Phase 1 - MVP Core Registry
**Services**: 9/46 implemented (19.6% complete)
**Target**: Production-ready ecosystem serving all DevQ.ai projects