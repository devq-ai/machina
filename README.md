# Machina - DevQ.ai MCP Registry & Management Platform

**Machina** is DevQ.ai's unified MCP (Model Context Protocol) Registry and Management Platform that orchestrates 48 MCP servers across the DevQ.ai ecosystem.

## 🎯 Overview

Machina solves the critical problem of MCP server fragmentation by providing a centralized registry, health monitoring, service discovery, and configuration management system. The platform enables DevQ.ai projects to reliably access AI tools and services through both MCP protocol and REST API interfaces, ensuring high availability and performance for AI-powered development workflows.

### Key Features

- 🏗️ **Unified MCP Registry** - Central discovery and management of all 48 MCP servers
- 🔍 **Service Health Monitoring** - 99.9% uptime through continuous health checks and automatic failover
- ⚙️ **Configuration Management UI** - Web interface for setting REQUIRED/BUILD_PRIORITY flags
- 🔌 **Dual Protocol Support** - Both MCP protocol and REST API access
- 📊 **JSON Status Reporting** - Real-time status monitoring for external systems
- 🐳 **Docker/Kubernetes Deployment** - Production-ready containerized architecture

## 🚀 Quick Start

### Development Setup

```bash
# Navigate to project
cd /Users/dionedge/devqai/machina

# Setup environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Initialize TaskMaster AI project management
task-master init --name="Machina MCP Registry" -y

# Start development environment
docker-compose up -d postgres redis

# Run tests
pytest tests/ --cov=src/ --cov-report=html
```

### Access Services

- **Registry API**: http://localhost:8000
- **Configuration UI**: http://localhost:8000/ui
- **Health Dashboard**: http://localhost:8000/health
- **API Documentation**: http://localhost:8000/docs
- **Test Coverage**: file://./htmlcov/index.html

## 📊 Current Status

### Implementation Progress

- **Total MCP Servers**: 48 servers planned
- **Currently Implemented**: 1 server (task-master-mcp-server partial)
- **Completion Rate**: 2% (1/48)
- **Stub Implementations**: 8 servers (need complete rebuild)

### Server Categories

| Category               | Count | Status                | Description                |
| ---------------------- | ----- | --------------------- | -------------------------- |
| **✅ Stub Only**       | 8     | Need Complete Rebuild | Basic 64-line templates    |
| **🏗️ Partial**         | 1     | ~20% Complete         | task-master-mcp-server     |
| **🔄 External**        | 8     | Integration Needed    | Official providers         |
| **❌ New Development** | 31    | Not Started           | Full implementation needed |

## 🏗️ Architecture

### Five-Component DevQ.ai Stack

1. **FastAPI Foundation** - Core web framework with dual MCP/REST support
2. **Logfire Observability** - Complete monitoring and performance tracking
3. **PyTest Build-to-Test** - 90% coverage requirement with meaningful tests
4. **TaskMaster AI** - Project management and task-driven development
5. **MCP Integration** - AI-powered development acceleration

### Core Components

```
machina/
├── src/
│   ├── registry/          # FastAPI + FastMCP hybrid service
│   ├── discovery/         # Automatic service detection
│   ├── monitoring/        # Health checking and failover
│   ├── ui/               # Configuration web interface
│   └── models/           # Database schemas and domain models
├── tests/                # Comprehensive test suite (90% coverage)
├── .taskmaster/          # TaskMaster AI project management
├── docker/              # Container orchestration
└── k8s/                 # Kubernetes deployment manifests
```

## 🧪 Testing Requirements

### Mandatory PyTest Validation

**CRITICAL REQUIREMENT**: All subtasks must pass comprehensive PyTest validation before progression.

#### Test Standards

- **Minimum Coverage**: 90% line coverage required
- **Test Types**: Unit, integration, and API endpoint tests
- **Quality Gate**: No subtask completion without passing tests
- **Meaningful Tests**: Tests must validate actual functionality, not just exist

#### Test Structure

```bash
tests/
├── unit/                 # Unit tests for individual components
│   ├── test_registry.py
│   ├── test_discovery.py
│   └── test_monitoring.py
├── integration/          # Integration tests for component interaction
│   ├── test_mcp_protocol.py
│   ├── test_database.py
│   └── test_redis.py
├── api/                 # API endpoint tests
│   ├── test_service_api.py
│   ├── test_health_api.py
│   └── test_config_api.py
├── fixtures/            # Test data and fixtures
└── conftest.py         # Shared test configuration
```

#### Running Tests

```bash
# Run all tests with coverage
pytest tests/ --cov=src/ --cov-report=html --cov-fail-under=90

# Run specific test suites
pytest tests/unit/ -v
pytest tests/integration/ -v
pytest tests/api/ -v

# Run tests for specific subtask validation
pytest tests/unit/test_registry.py::test_database_connection -v
pytest tests/integration/test_mcp_protocol.py::test_server_registration -v
```

## 📋 Sprint Development Plan

### 🚀 SPRINT 1: Foundation & Critical Infrastructure (Week 1-2)

**Goal**: Complete stub implementations and build critical required servers

#### Servers (7 total)

1. **task-master-mcp-server** - Complete existing partial implementation
2. **crawl4ai-mcp** - Build web crawling functionality (Required)
3. **context7-mcp** - Build semantic search & vector embeddings
4. **surrealdb-mcp** - Build multi-model database integration
5. **magic-mcp** - Build AI-powered code generation
6. **ptolemies-mcp-server** - Build temporal knowledge graph (Required)
7. **logfire-mcp** - Build observability integration

#### Success Criteria

- [ ] All 5 stub servers have full functional implementations
- [ ] PyTest coverage ≥90% for all sprint 1 servers
- [ ] Crawl4ai and Ptolemies (Required servers) operational
- [ ] All servers deployable via Machina registry

### 🛠️ SPRINT 2: Development Tools & Database Ecosystem (Week 3-4)

**Goal**: Complete development toolchain and database integrations

#### Servers (7 total)

8. **registry-mcp** - Build complete server registry management
9. **shadcn-ui-mcp-server** - Build React component integration
10. **mcp-server-docker** - Build containerization management
11. **upstash-mcp** - Build serverless data integration
12. **solver-pysat-mcp** - Build Boolean satisfiability solver
13. **solver-z3-mcp** - Build theorem prover integration
14. **calendar-mcp** - Build Google Calendar integration

#### Success Criteria

- [ ] MCP registry enables server discovery and installation
- [ ] Docker MCP provides container management capabilities
- [ ] Solver systems operational for constraint problems
- [ ] PyTest coverage ≥90% maintained across all servers

### 💰 SPRINT 3: Financial Services & External Integrations (Week 5-6)

**Goal**: Complete financial services ecosystem and key external providers

#### Servers (6 total)

15. **paypal-mcp** - Integrate https://github.com/paypal/agent-toolkit
16. **stripe-mcp** - Integrate official Stripe provider
17. **xero-mcp-server** - Integrate https://github.com/XeroAPI/xero-mcp-server
18. **square-mcp** - Integrate https://developer.squareup.com/docs/mcp
19. **plaid-mcp** - Integrate https://plaid.com/docs/mcp/
20. **gmail-mcp** - Build email management integration

#### Success Criteria

- [ ] Complete financial services ecosystem operational
- [ ] All 5 financial providers properly authenticated and tested
- [ ] End-to-end payment and accounting workflows functional
- [ ] Gmail automation reduces manual email work by 50%

## 📋 Concrete Deliverables Per Subtask

### Subtask Completion Requirements

Each subtask must deliver:

1. **Functional Code**: Working implementation with proper error handling
2. **Comprehensive Tests**: Unit and integration tests with ≥90% coverage
3. **Documentation**: Code comments, docstrings, and usage examples
4. **Integration Proof**: Successful integration with Machina platform
5. **Performance Validation**: Response times <100ms for MCP calls

### Example: Database Integration Subtask Deliverables

**Code Deliverables**:

- ✅ PostgreSQL connection with async SQLAlchemy
- ✅ Database models with proper relationships
- ✅ Repository pattern implementation
- ✅ Migration scripts and schema validation

**Test Deliverables**:

- ✅ Connection pool testing under load
- ✅ CRUD operations validation
- ✅ Transaction rollback scenarios
- ✅ Concurrent access testing
- ✅ Data integrity validation

**Integration Deliverables**:

- ✅ FastAPI dependency injection working
- ✅ Health check endpoint responds correctly
- ✅ Database available via Machina registry
- ✅ Logfire monitoring captures all queries

## 🔧 API Reference

### Service Discovery

```bash
# List all services
GET /api/services

# Filter by build type
GET /api/services/by-type/fastmcp

# Get service details
GET /api/services/{service_name}
```

### Configuration Management

```bash
# Update service configuration
PUT /api/services/{service_name}/config
{
  "required": true,
  "build_priority": "HIGH",
  "enabled": true
}

# Get current configuration
GET /api/services/{service_name}/config
```

### Health Monitoring

```bash
# Overall system health
GET /api/health

# Individual service health
GET /api/health/{service_name}

# JSON status for monitoring
GET /api/health/status.json
```

### MCP Protocol Access

```python
from mcp import Client

# Connect to registry
async with Client("ws://machina.devq.ai/mcp") as client:
    # List available services
    services = await client.call_tool("list_available_services")

    # Call service tool
    result = await client.call_tool("call_service_tool",
        service="context7-mcp",
        tool="semantic_search",
        query="FastAPI patterns"
    )
```

## 🚀 Development Workflow

### TaskMaster AI Integration

```bash
# View current tasks and dependencies
task-master list --with-subtasks

# Get next task to work on
task-master next

# Start working on a subtask
task-master set-status --id=1.1 --status=in-progress

# Complete subtask (requires passing tests)
pytest tests/unit/test_registry.py --cov=src/registry --cov-fail-under=90
task-master set-status --id=1.1 --status=done

# Expand complex tasks into subtasks
task-master expand --id=2 --research
```

### Quality Standards

- **Code Formatting**: Black formatter (88 character limit)
- **Type Hints**: Required for all functions and classes
- **Documentation**: Google-style docstrings for all public APIs
- **Error Handling**: Comprehensive exception handling with logging
- **Performance**: All MCP calls must respond within 100ms

### Development Environment

```bash
# Required environment variables
export LOGFIRE_TOKEN="pylf_v1_us_..."
export ANTHROPIC_API_KEY="sk-ant-..."
export POSTGRES_URL="postgresql://localhost:5432/machina"
export REDIS_URL="redis://localhost:6379"

# Start development services
docker-compose up -d postgres redis logfire

# Run in development mode with hot reload
uvicorn src.main:app --reload --port 8000
```

## 📈 Post-Sprint Development (Week 7+)

### Phase 4: Project Conversions (Week 7-8)

- **bayes-mcp** - Convert existing `/archive/dev/bayes` project
- **darwin-mcp** - Convert existing `/darwin` project

### Phase 5: External Official Integrations (Week 9-10)

- **shopify-dev-mcp-server**, **sqlite-mcp**, **slack-mcp**
- **typescript-mcp**, **github-mcp**, **puppeteer-mcp**, **redis-mcp**

### Phase 6: Data & Analytics (Week 11-13)

- **jupyter-mcp**, **memory-mcp**, **bigquery-mcp**, **databricks-mcp**
- **snowflake-mcp**, **scholarly-mcp**, **wikidata-mcp**, **brightdata-mcp**

### Phase 7: Advanced Development & Infrastructure (Week 14-16)

- **databutton-mcp**, **gcp-mcp**, **pulumi-mcp-server**, **browser-tools**
- **financial-mcp**, **esignatures-mcp**, **markdownify-mcp**, **imcp**
- **solver-mzn-mcp**, **mcp-server-kalshi**

## 🔒 Security & Compliance

- **Authentication**: Bearer tokens with role-based access control
- **Encryption**: TLS 1.3 for all external communications
- **Secrets Management**: Kubernetes secrets for API keys and credentials
- **Audit Trail**: Complete logging of all configuration changes
- **Data Privacy**: GDPR-compliant data handling and retention

## 🚀 Production Deployment

### Kubernetes Deployment

```bash
# Deploy to production
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml

# Using Helm
helm install machina ./helm/ --values production-values.yaml
```

### Monitoring & Observability

- **Logfire Integration**: Complete observability with structured logging
- **Prometheus Metrics**: Performance and health metrics collection
- **Grafana Dashboards**: Real-time monitoring and alerting
- **Health Checks**: Kubernetes liveness and readiness probes

## 🤝 Contributing

1. **Follow DevQ.ai Standards**: Maintain the five-component architecture
2. **Test-Driven Development**: Write tests before implementation
3. **TaskMaster Integration**: Use TaskMaster AI for all task management
4. **Quality Gates**: All code must pass PyTest validation with ≥90% coverage
5. **Documentation**: Include comprehensive docstrings and usage examples

### Pull Request Process

1. Create feature branch from main
2. Implement changes with tests
3. Ensure all tests pass: `pytest tests/ --cov=src/ --cov-fail-under=90`
4. Update documentation as needed
5. Submit PR with detailed description of changes

## 📞 Support & Resources

- **Documentation**: `/docs/` directory contains detailed guides
- **Issues**: Use GitHub issues for bug reports and feature requests
- **Development Standards**: Follow established DevQ.ai patterns
- **Monitoring**: Check Logfire dashboards for system health
- **TaskMaster**: Use `task-master --help` for project management commands

---

**Current Status**: 🏗️ Sprint 1 Development Phase
**Next Milestone**: Complete 7 foundation MCP servers with full test coverage
**Target**: Production-ready ecosystem serving all DevQ.ai projects by Week 16
**Success Metric**: 48/48 MCP servers operational with 99.9% uptime
