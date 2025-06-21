# DevQ.ai MCP Service Registry Design

## Architecture Overview

The MCP Service Registry will be a **FastAPI + FastMCP hybrid service** that manages discovery, health monitoring, and routing for all 46 MCP servers.

## Core Components

### 1. **Registry Service** (`mcp-registry-service/`)

```python
# registry/main.py
from fastapi import FastAPI, Depends
from fastmcp import FastMCP
import logfire
from .models import ServiceRegistration, HealthStatus
from .discovery import ServiceDiscovery
from .health import HealthMonitor
from .router import MCPRouter

app = FastAPI(title="DevQ.ai MCP Registry", version="1.0.0")
mcp = FastMCP("DevQ.ai MCP Registry")

# Core services
registry = ServiceRegistry()
discovery = ServiceDiscovery(registry)
health_monitor = HealthMonitor(registry)
router = MCPRouter(registry)

@app.on_event("startup")
async def startup():
    await discovery.discover_all_services()
    await health_monitor.start_monitoring()
    logfire.info("MCP Registry started", services=len(registry.services))

# REST API Endpoints
@app.get("/api/services")
async def list_services():
    """List all registered MCP services"""
    return registry.get_all_services()

@app.get("/api/services/{service_name}/health")
async def service_health(service_name: str):
    """Get health status of specific service"""
    return await health_monitor.check_service(service_name)

@app.post("/api/services/{service_name}/call")
async def call_service(service_name: str, tool: str, args: dict):
    """Route tool calls to specific services"""
    return await router.route_call(service_name, tool, args)

# MCP Protocol Support
@mcp.tool
async def list_available_tools():
    """List all tools from all registered services"""
    return await registry.get_all_tools()

@mcp.tool
async def call_tool(service: str, tool: str, **kwargs):
    """Route MCP tool calls to appropriate service"""
    return await router.route_mcp_call(service, tool, **kwargs)
```

### 2. **Service Discovery** (`registry/discovery.py`)

```python
class ServiceDiscovery:
    """Automatic discovery of MCP services"""
    
    def __init__(self, registry: ServiceRegistry):
        self.registry = registry
        self.discovery_methods = [
            self._discover_local_mcp_servers,
            self._discover_fastapi_services,
            self._discover_external_services,
            self._discover_docker_services
        ]
    
    async def discover_all_services(self):
        """Run all discovery methods"""
        for method in self.discovery_methods:
            services = await method()
            for service in services:
                await self.registry.register_service(service)
    
    async def _discover_local_mcp_servers(self):
        """Discover services in /mcp/mcp-servers/"""
        servers = []
        mcp_dir = Path("/Users/dionedge/devqai/mcp/mcp-servers")
        
        for server_dir in mcp_dir.iterdir():
            if server_dir.is_dir():
                config = await self._load_server_config(server_dir)
                servers.append(ServiceRegistration(
                    name=server_dir.name,
                    type="fastmcp",
                    location=str(server_dir),
                    protocol="stdio",
                    config=config
                ))
        return servers
    
    async def _discover_fastapi_services(self):
        """Discover FastAPI services that should be MCP servers"""
        # Implementation for FastAPI service discovery
        pass
    
    async def _discover_external_services(self):
        """Discover external/third-party MCP servers"""
        external_services = [
            {"name": "stripe-mcp", "type": "external", "source": "official"},
            {"name": "paypal-mcp", "type": "external", "source": "official"},
            # ... other external services
        ]
        return [ServiceRegistration(**service) for service in external_services]
    
    async def _discover_docker_services(self):
        """Discover containerized MCP services"""
        # Implementation for Docker service discovery
        pass
```

### 3. **Health Monitoring** (`registry/health.py`)

```python
class HealthMonitor:
    """Continuous health monitoring for all services"""
    
    def __init__(self, registry: ServiceRegistry):
        self.registry = registry
        self.health_checks = {}
        self.check_interval = 30  # seconds
    
    async def start_monitoring(self):
        """Start background health monitoring"""
        asyncio.create_task(self._health_check_loop())
    
    async def _health_check_loop(self):
        """Continuous health checking"""
        while True:
            await self._check_all_services()
            await asyncio.sleep(self.check_interval)
    
    async def _check_all_services(self):
        """Check health of all registered services"""
        tasks = []
        for service in self.registry.get_all_services():
            task = asyncio.create_task(self._check_service_health(service))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        await self._process_health_results(results)
    
    async def _check_service_health(self, service: ServiceRegistration):
        """Check health of individual service"""
        try:
            if service.type == "fastmcp":
                return await self._check_fastmcp_health(service)
            elif service.type == "fastapi":
                return await self._check_fastapi_health(service)
            elif service.type == "external":
                return await self._check_external_health(service)
        except Exception as e:
            logfire.error("Health check failed", service=service.name, error=str(e))
            return HealthStatus(service=service.name, status="unhealthy", error=str(e))
    
    async def _check_fastmcp_health(self, service: ServiceRegistration):
        """Health check for FastMCP services"""
        # Try to call a status tool or ping the service
        try:
            # Implementation depends on FastMCP health check capabilities
            return HealthStatus(service=service.name, status="healthy")
        except Exception as e:
            return HealthStatus(service=service.name, status="unhealthy", error=str(e))
    
    async def _check_fastapi_health(self, service: ServiceRegistration):
        """Health check for FastAPI services"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{service.base_url}/health")
                if response.status_code == 200:
                    return HealthStatus(service=service.name, status="healthy")
                else:
                    return HealthStatus(service=service.name, status="unhealthy", 
                                      error=f"HTTP {response.status_code}")
        except Exception as e:
            return HealthStatus(service=service.name, status="unhealthy", error=str(e))
```

### 4. **Service Router** (`registry/router.py`)

```python
class MCPRouter:
    """Route calls to appropriate MCP services"""
    
    def __init__(self, registry: ServiceRegistry):
        self.registry = registry
        self.load_balancer = LoadBalancer()
    
    async def route_call(self, service_name: str, tool: str, args: dict):
        """Route API calls to services"""
        service = await self.registry.get_service(service_name)
        if not service:
            raise HTTPException(404, f"Service {service_name} not found")
        
        healthy_instances = await self.registry.get_healthy_instances(service_name)
        if not healthy_instances:
            raise HTTPException(503, f"No healthy instances of {service_name}")
        
        instance = self.load_balancer.select_instance(healthy_instances)
        return await self._call_service_instance(instance, tool, args)
    
    async def route_mcp_call(self, service: str, tool: str, **kwargs):
        """Route MCP protocol calls"""
        # Similar to route_call but for MCP protocol
        return await self.route_call(service, tool, kwargs)
    
    async def _call_service_instance(self, instance: ServiceInstance, tool: str, args: dict):
        """Make actual call to service instance"""
        if instance.type == "fastmcp":
            return await self._call_fastmcp_service(instance, tool, args)
        elif instance.type == "fastapi":
            return await self._call_fastapi_service(instance, tool, args)
        else:
            raise ValueError(f"Unsupported service type: {instance.type}")
    
    async def _call_fastmcp_service(self, instance: ServiceInstance, tool: str, args: dict):
        """Call FastMCP service"""
        # Implementation for calling FastMCP services
        pass
    
    async def _call_fastapi_service(self, instance: ServiceInstance, tool: str, args: dict):
        """Call FastAPI service"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{instance.base_url}/tools/{tool}",
                json=args,
                headers={"Authorization": f"Bearer {instance.api_key}"}
            )
            return response.json()
```

### 5. **Data Models** (`registry/models.py`)

```python
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Literal
from datetime import datetime

class ServiceRegistration(BaseModel):
    name: str
    type: Literal["fastmcp", "fastapi", "external", "docker"]
    location: str  # File path, URL, or container name
    protocol: Literal["stdio", "http", "websocket"]
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    config: Dict = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class HealthStatus(BaseModel):
    service: str
    status: Literal["healthy", "unhealthy", "unknown"]
    last_check: datetime = Field(default_factory=datetime.now)
    response_time_ms: Optional[float] = None
    error: Optional[str] = None

class ServiceInstance(BaseModel):
    service_name: str
    instance_id: str
    type: str
    base_url: Optional[str]
    health: HealthStatus
    load_score: float = 0.0  # For load balancing

class ToolDefinition(BaseModel):
    name: str
    service: str
    description: str
    input_schema: Dict
    output_schema: Optional[Dict] = None
```

## Implementation Phases

### Phase 1: Core Registry (Week 1)
- Basic service discovery for existing 9 MCP servers
- Health monitoring for local services
- REST API for service management

### Phase 2: Integration (Week 2)
- External service integration (8 services)
- Conversion of existing projects (2 services)
- Load balancing and failover

### Phase 3: Expansion (Week 3-4)
- New FastMCP implementations (16 services)
- FastAPI services for complex workloads (11 services)
- Docker orchestration

### Phase 4: Production (Week 5-6)
- Kubernetes deployment
- Monitoring dashboards
- Performance optimization
- Documentation and testing

## Registry API Examples

### REST API Usage
```bash
# List all services
curl https://registry.devq.ai/api/services

# Check service health
curl https://registry.devq.ai/api/services/context7-mcp/health

# Call a tool
curl -X POST https://registry.devq.ai/api/services/context7-mcp/call \
  -H "Content-Type: application/json" \
  -d '{"tool": "semantic_search", "args": {"query": "FastAPI patterns"}}'
```

### MCP Protocol Usage
```python
# Through MCP client
from mcp import Client

client = Client("ws://registry.devq.ai/mcp")
result = await client.call_tool("list_available_tools")
search_result = await client.call_tool("call_tool", 
    service="context7-mcp", 
    tool="semantic_search", 
    query="FastAPI patterns"
)
```

This registry design provides:
- ✅ **Automatic Discovery**: Finds all services automatically
- ✅ **Health Monitoring**: Continuous health checks with failover
- ✅ **Load Balancing**: Distributes load across healthy instances
- ✅ **Dual Protocol**: Supports both MCP and REST access
- ✅ **Observability**: Complete Logfire integration
- ✅ **Scalability**: Ready for Kubernetes deployment