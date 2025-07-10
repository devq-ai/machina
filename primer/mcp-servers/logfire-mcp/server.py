#!/usr/bin/env python3
"""
Logfire MCP Server

Advanced observability and monitoring server implementing the MCP protocol.
Provides comprehensive monitoring, metrics collection, alerting, and health checks
for MCP servers and the broader DevQ.ai ecosystem using Pydantic Logfire.

This implementation follows DevQ.ai standards with comprehensive MCP integration,
async operations, structured logging, and robust error handling.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Set
from pathlib import Path
import sys
import os
import time
import psutil
from dataclasses import dataclass, asdict
from enum import Enum

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

try:
    from mcp import types
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from pydantic import BaseModel, Field, field_validator
    import aiofiles
    import httpx
    import logfire
    import sqlalchemy as sa
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import declarative_base, sessionmaker
    import aiosqlite
    import orjson
    import prometheus_client
    from prometheus_client import CollectorRegistry, Gauge, Counter, Histogram
    import websockets
    from opentelemetry import trace, metrics
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.metrics import MeterProvider
    import redis.asyncio as redis
    from influxdb_client import InfluxDBClient
    from dotenv import load_dotenv
    import yaml
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Please ensure all dependencies are installed: pip install -r requirements.txt")
    sys.exit(1)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configure Logfire for the monitoring server itself
logfire.configure(
    token=os.getenv("LOGFIRE_TOKEN"),
    project_name="logfire-mcp-server",
    service_name="logfire-mcp",
    environment=os.getenv("ENVIRONMENT", "development")
)

class MetricType(str, Enum):
    """Types of metrics collected."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"

class AlertSeverity(str, Enum):
    """Alert severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

class MonitoringScope(str, Enum):
    """Monitoring scope levels."""
    SERVER = "server"
    SYSTEM = "system"
    APPLICATION = "application"
    CUSTOM = "custom"

@dataclass
class MetricPoint:
    """Individual metric data point."""
    name: str
    value: float
    tags: Dict[str, str]
    timestamp: datetime
    metric_type: MetricType

@dataclass
class Alert:
    """Alert configuration and state."""
    id: str
    name: str
    description: str
    condition: str
    severity: AlertSeverity
    enabled: bool
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0

@dataclass
class HealthCheck:
    """Health check configuration."""
    name: str
    endpoint: Optional[str]
    interval: int  # seconds
    timeout: int   # seconds
    expected_status: int = 200
    last_check: Optional[datetime] = None
    status: str = "unknown"
    response_time: Optional[float] = None

# SQLAlchemy Base
Base = declarative_base()

class MetricRecord(Base):
    """Database model for storing metrics."""
    __tablename__ = "metrics"

    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String(255), nullable=False, index=True)
    value = sa.Column(sa.Float, nullable=False)
    tags = sa.Column(sa.Text)  # JSON string
    timestamp = sa.Column(sa.DateTime, nullable=False, index=True)
    metric_type = sa.Column(sa.String(50), nullable=False)

class AlertRecord(Base):
    """Database model for storing alert history."""
    __tablename__ = "alerts"

    id = sa.Column(sa.Integer, primary_key=True)
    alert_id = sa.Column(sa.String(255), nullable=False, index=True)
    name = sa.Column(sa.String(255), nullable=False)
    severity = sa.Column(sa.String(50), nullable=False)
    condition = sa.Column(sa.Text, nullable=False)
    triggered_at = sa.Column(sa.DateTime, nullable=False)
    resolved_at = sa.Column(sa.DateTime)
    status = sa.Column(sa.String(50), default="active")

class LogfireMCPServer:
    """Advanced observability and monitoring MCP server."""

    def __init__(self):
        """Initialize the Logfire MCP Server."""
        self.server = Server("logfire-mcp")
        self.metrics_registry = CollectorRegistry()
        self.metrics_cache: Dict[str, MetricPoint] = {}
        self.alerts: Dict[str, Alert] = {}
        self.health_checks: Dict[str, HealthCheck] = {}
        self.db_engine = None
        self.db_session = None
        self.redis_client = None
        self.influx_client = None
        self.websocket_clients: Set[websockets.WebSocketServerProtocol] = set()

        # Prometheus metrics
        self.setup_prometheus_metrics()

        # Initialize components
        asyncio.create_task(self._setup_database())
        asyncio.create_task(self._setup_redis())
        asyncio.create_task(self._setup_influxdb())
        self._setup_default_alerts()
        self._setup_default_health_checks()
        self._setup_tools()

        # Start background tasks
        asyncio.create_task(self._metrics_collector_loop())
        asyncio.create_task(self._health_check_loop())
        asyncio.create_task(self._alert_processor_loop())

    def setup_prometheus_metrics(self):
        """Initialize Prometheus metrics."""
        self.prom_metrics = {
            'mcp_requests_total': Counter(
                'mcp_requests_total',
                'Total MCP requests processed',
                ['server', 'method', 'status'],
                registry=self.metrics_registry
            ),
            'mcp_request_duration': Histogram(
                'mcp_request_duration_seconds',
                'MCP request duration',
                ['server', 'method'],
                registry=self.metrics_registry
            ),
            'mcp_server_health': Gauge(
                'mcp_server_health',
                'MCP server health status (1=healthy, 0=unhealthy)',
                ['server'],
                registry=self.metrics_registry
            ),
            'system_cpu_usage': Gauge(
                'system_cpu_usage_percent',
                'System CPU usage percentage',
                registry=self.metrics_registry
            ),
            'system_memory_usage': Gauge(
                'system_memory_usage_percent',
                'System memory usage percentage',
                registry=self.metrics_registry
            ),
            'system_disk_usage': Gauge(
                'system_disk_usage_percent',
                'System disk usage percentage',
                ['disk'],
                registry=self.metrics_registry
            )
        }

    async def _setup_database(self):
        """Initialize SQLite database for metrics storage."""
        try:
            db_path = os.getenv("LOGFIRE_DB_PATH", "logfire_mcp.db")
            self.db_engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")

            # Create tables
            async with self.db_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            # Create session factory
            async_session = sessionmaker(
                self.db_engine, class_=AsyncSession, expire_on_commit=False
            )
            self.db_session = async_session

            logger.info("Database initialized successfully")

        except Exception as e:
            logger.error(f"Database setup failed: {e}")

    async def _setup_redis(self):
        """Initialize Redis connection for distributed metrics."""
        try:
            redis_url = os.getenv("REDIS_URL")
            if redis_url:
                self.redis_client = redis.from_url(redis_url)
                await self.redis_client.ping()
                logger.info("Redis connection established")
        except Exception as e:
            logger.warning(f"Redis setup failed: {e}")

    async def _setup_influxdb(self):
        """Initialize InfluxDB connection for time series storage."""
        try:
            influx_url = os.getenv("INFLUXDB_URL")
            influx_token = os.getenv("INFLUXDB_TOKEN")
            influx_org = os.getenv("INFLUXDB_ORG")

            if influx_url and influx_token and influx_org:
                self.influx_client = InfluxDBClient(
                    url=influx_url,
                    token=influx_token,
                    org=influx_org
                )
                logger.info("InfluxDB connection established")
        except Exception as e:
            logger.warning(f"InfluxDB setup failed: {e}")

    def _setup_default_alerts(self):
        """Set up default alert configurations."""
        default_alerts = [
            Alert(
                id="high_cpu_usage",
                name="High CPU Usage",
                description="CPU usage exceeds 80%",
                condition="system_cpu_usage > 80",
                severity=AlertSeverity.HIGH,
                enabled=True
            ),
            Alert(
                id="high_memory_usage",
                name="High Memory Usage",
                description="Memory usage exceeds 85%",
                condition="system_memory_usage > 85",
                severity=AlertSeverity.HIGH,
                enabled=True
            ),
            Alert(
                id="mcp_server_down",
                name="MCP Server Down",
                description="MCP server health check failed",
                condition="mcp_server_health == 0",
                severity=AlertSeverity.CRITICAL,
                enabled=True
            ),
            Alert(
                id="high_error_rate",
                name="High Error Rate",
                description="Error rate exceeds 5% in last 5 minutes",
                condition="error_rate_5m > 0.05",
                severity=AlertSeverity.MEDIUM,
                enabled=True
            )
        ]

        for alert in default_alerts:
            self.alerts[alert.id] = alert

    def _setup_default_health_checks(self):
        """Set up default health check configurations."""
        # Add health checks for known MCP servers
        mcp_servers = [
            "task-master-mcp-server",
            "crawl4ai-mcp",
            "context7-mcp",
            "surrealdb-mcp",
            "magic-mcp"
        ]

        for server_name in mcp_servers:
            self.health_checks[f"{server_name}_health"] = HealthCheck(
                name=f"{server_name} Health Check",
                endpoint=f"http://localhost:8000/{server_name}/health",
                interval=30,  # 30 seconds
                timeout=10    # 10 seconds
            )

    def _setup_tools(self):
        """Register MCP tools."""

        @self.server.list_tools()
        async def list_tools() -> List[types.Tool]:
            """List available observability tools."""
            return [
                types.Tool(
                    name="collect_metrics",
                    description="Collect and store metrics from various sources",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "source": {
                                "type": "string",
                                "description": "Metrics source (system, mcp_server, custom)"
                            },
                            "metrics": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "value": {"type": "number"},
                                        "tags": {"type": "object"},
                                        "metric_type": {"type": "string", "enum": ["counter", "gauge", "histogram"]}
                                    },
                                    "required": ["name", "value", "metric_type"]
                                },
                                "description": "Array of metric data points"
                            }
                        },
                        "required": ["source", "metrics"]
                    }
                ),
                types.Tool(
                    name="query_metrics",
                    description="Query stored metrics with filters and aggregation",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "metric_name": {
                                "type": "string",
                                "description": "Name of the metric to query"
                            },
                            "start_time": {
                                "type": "string",
                                "description": "Start time for query (ISO format)"
                            },
                            "end_time": {
                                "type": "string",
                                "description": "End time for query (ISO format)"
                            },
                            "tags": {
                                "type": "object",
                                "description": "Tag filters"
                            },
                            "aggregation": {
                                "type": "string",
                                "enum": ["avg", "sum", "min", "max", "count"],
                                "description": "Aggregation function"
                            },
                            "group_by": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Group by tag keys"
                            }
                        },
                        "required": ["metric_name"]
                    }
                ),
                types.Tool(
                    name="health_check",
                    description="Perform health checks on specified endpoints",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "target": {
                                "type": "string",
                                "description": "Target to check (all, system, specific_server)"
                            },
                            "endpoints": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Specific endpoints to check"
                            }
                        },
                        "required": ["target"]
                    }
                ),
                types.Tool(
                    name="create_alert",
                    description="Create a new monitoring alert",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Alert name"
                            },
                            "description": {
                                "type": "string",
                                "description": "Alert description"
                            },
                            "condition": {
                                "type": "string",
                                "description": "Alert condition expression"
                            },
                            "severity": {
                                "type": "string",
                                "enum": ["critical", "high", "medium", "low", "info"],
                                "description": "Alert severity level"
                            },
                            "enabled": {
                                "type": "boolean",
                                "description": "Whether alert is enabled"
                            }
                        },
                        "required": ["name", "condition", "severity"]
                    }
                ),
                types.Tool(
                    name="manage_alerts",
                    description="Manage existing alerts (list, enable, disable, delete)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "action": {
                                "type": "string",
                                "enum": ["list", "enable", "disable", "delete"],
                                "description": "Action to perform"
                            },
                            "alert_id": {
                                "type": "string",
                                "description": "Alert ID for enable/disable/delete actions"
                            }
                        },
                        "required": ["action"]
                    }
                ),
                types.Tool(
                    name="system_overview",
                    description="Get comprehensive system and MCP ecosystem overview",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "include_details": {
                                "type": "boolean",
                                "description": "Include detailed metrics and health status"
                            },
                            "time_range": {
                                "type": "string",
                                "description": "Time range for metrics (1h, 24h, 7d, 30d)"
                            }
                        }
                    }
                ),
                types.Tool(
                    name="export_metrics",
                    description="Export metrics in various formats",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "format": {
                                "type": "string",
                                "enum": ["json", "csv", "prometheus", "influx"],
                                "description": "Export format"
                            },
                            "metric_names": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Specific metrics to export"
                            },
                            "start_time": {
                                "type": "string",
                                "description": "Start time for export"
                            },
                            "end_time": {
                                "type": "string",
                                "description": "End time for export"
                            }
                        },
                        "required": ["format"]
                    }
                ),
                types.Tool(
                    name="get_server_status",
                    description="Get Logfire MCP server status and configuration",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "additionalProperties": False
                    }
                )
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
            """Handle tool calls."""
            try:
                with logfire.span(f"Tool call: {name}", arguments=arguments):
                    if name == "collect_metrics":
                        return await self._handle_collect_metrics(arguments)
                    elif name == "query_metrics":
                        return await self._handle_query_metrics(arguments)
                    elif name == "health_check":
                        return await self._handle_health_check(arguments)
                    elif name == "create_alert":
                        return await self._handle_create_alert(arguments)
                    elif name == "manage_alerts":
                        return await self._handle_manage_alerts(arguments)
                    elif name == "system_overview":
                        return await self._handle_system_overview(arguments)
                    elif name == "export_metrics":
                        return await self._handle_export_metrics(arguments)
                    elif name == "get_server_status":
                        return await self._handle_get_server_status(arguments)
                    else:
                        raise ValueError(f"Unknown tool: {name}")

            except Exception as e:
                logger.error(f"Error handling tool call {name}: {e}")
                logfire.error(f"Tool call error: {name}", error=str(e))
                return [types.TextContent(
                    type="text",
                    text=f"Error: {str(e)}"
                )]

    async def _handle_collect_metrics(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Handle metrics collection."""
        try:
            source = arguments["source"]
            metrics_data = arguments["metrics"]

            collected_count = 0

            with logfire.span("Collect metrics", source=source, count=len(metrics_data)):
                for metric_data in metrics_data:
                    metric = MetricPoint(
                        name=metric_data["name"],
                        value=float(metric_data["value"]),
                        tags=metric_data.get("tags", {}),
                        timestamp=datetime.utcnow(),
                        metric_type=MetricType(metric_data["metric_type"])
                    )

                    await self._store_metric(metric)
                    collected_count += 1

                # Update Prometheus metrics
                if source == "system":
                    await self._update_prometheus_metrics()

                logfire.info("Metrics collected", source=source, count=collected_count)

            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "status": "success",
                    "collected_count": collected_count,
                    "source": source,
                    "timestamp": datetime.utcnow().isoformat()
                }, indent=2)
            )]

        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
            return [types.TextContent(
                type="text",
                text=f"Error collecting metrics: {str(e)}"
            )]

    async def _handle_query_metrics(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Handle metrics querying."""
        try:
            metric_name = arguments["metric_name"]
            start_time = arguments.get("start_time")
            end_time = arguments.get("end_time")
            tags = arguments.get("tags", {})
            aggregation = arguments.get("aggregation", "avg")
            group_by = arguments.get("group_by", [])

            with logfire.span("Query metrics", metric_name=metric_name):
                results = await self._query_metrics(
                    metric_name, start_time, end_time, tags, aggregation, group_by
                )

                logfire.info("Metrics queried", metric_name=metric_name, result_count=len(results))

            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "metric_name": metric_name,
                    "aggregation": aggregation,
                    "results": results,
                    "query_time": datetime.utcnow().isoformat()
                }, indent=2)
            )]

        except Exception as e:
            logger.error(f"Error querying metrics: {e}")
            return [types.TextContent(
                type="text",
                text=f"Error querying metrics: {str(e)}"
            )]

    async def _handle_health_check(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Handle health check requests."""
        try:
            target = arguments["target"]
            endpoints = arguments.get("endpoints", [])

            with logfire.span("Health check", target=target):
                if target == "all":
                    results = await self._check_all_health()
                elif target == "system":
                    results = await self._check_system_health()
                elif endpoints:
                    results = await self._check_specific_endpoints(endpoints)
                else:
                    results = await self._check_target_health(target)

                logfire.info("Health check completed", target=target, healthy_count=sum(1 for r in results if r.get("healthy", False)))

            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "target": target,
                    "health_checks": results,
                    "overall_healthy": all(r.get("healthy", False) for r in results),
                    "check_time": datetime.utcnow().isoformat()
                }, indent=2)
            )]

        except Exception as e:
            logger.error(f"Error performing health check: {e}")
            return [types.TextContent(
                type="text",
                text=f"Error performing health check: {str(e)}"
            )]

    async def _handle_create_alert(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Handle alert creation."""
        try:
            alert_id = str(uuid.uuid4())
            alert = Alert(
                id=alert_id,
                name=arguments["name"],
                description=arguments.get("description", ""),
                condition=arguments["condition"],
                severity=AlertSeverity(arguments["severity"]),
                enabled=arguments.get("enabled", True)
            )

            self.alerts[alert_id] = alert

            with logfire.span("Create alert", alert_id=alert_id, name=alert.name):
                logfire.info("Alert created", alert_id=alert_id, name=alert.name, severity=alert.severity)

            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "status": "success",
                    "alert_id": alert_id,
                    "alert": asdict(alert),
                    "created_at": datetime.utcnow().isoformat()
                }, indent=2)
            )]

        except Exception as e:
            logger.error(f"Error creating alert: {e}")
            return [types.TextContent(
                type="text",
                text=f"Error creating alert: {str(e)}"
            )]

    async def _handle_manage_alerts(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Handle alert management operations."""
        try:
            action = arguments["action"]
            alert_id = arguments.get("alert_id")

            with logfire.span("Manage alerts", action=action, alert_id=alert_id):
                if action == "list":
                    result = {
                        "alerts": [asdict(alert) for alert in self.alerts.values()],
                        "total_count": len(self.alerts)
                    }
                elif action == "enable" and alert_id:
                    if alert_id in self.alerts:
                        self.alerts[alert_id].enabled = True
                        result = {"status": "success", "message": f"Alert {alert_id} enabled"}
                    else:
                        result = {"status": "error", "message": f"Alert {alert_id} not found"}
                elif action == "disable" and alert_id:
                    if alert_id in self.alerts:
                        self.alerts[alert_id].enabled = False
                        result = {"status": "success", "message": f"Alert {alert_id} disabled"}
                    else:
                        result = {"status": "error", "message": f"Alert {alert_id} not found"}
                elif action == "delete" and alert_id:
                    if alert_id in self.alerts:
                        del self.alerts[alert_id]
                        result = {"status": "success", "message": f"Alert {alert_id} deleted"}
                    else:
                        result = {"status": "error", "message": f"Alert {alert_id} not found"}
                else:
                    result = {"status": "error", "message": "Invalid action or missing alert_id"}

                logfire.info("Alert management", action=action, alert_id=alert_id, result=result.get("status"))

            return [types.TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]

        except Exception as e:
            logger.error(f"Error managing alerts: {e}")
            return [types.TextContent(
                type="text",
                text=f"Error managing alerts: {str(e)}"
            )]

    async def _handle_system_overview(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Handle system overview requests."""
        try:
            include_details = arguments.get("include_details", True)
            time_range = arguments.get("time_range", "1h")

            with logfire.span("System overview", include_details=include_details):
                overview = await self._generate_system_overview(include_details, time_range)
                logfire.info("System overview generated", servers_monitored=len(overview.get("mcp_servers", {})))

            return [types.TextContent(
                type="text",
                text=json.dumps(overview, indent=2)
            )]

        except Exception as e:
            logger.error(f"Error generating system overview: {e}")
            return [types.TextContent(
                type="text",
                text=f"Error generating system overview: {str(e)}"
            )]

    async def _handle_export_metrics(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Handle metrics export requests."""
        try:
            export_format = arguments["format"]
            metric_names = arguments.get("metric_names", [])
            start_time = arguments.get("start_time")
            end_time = arguments.get("end_time")

            with logfire.span("Export metrics", format=export_format):
                exported_data = await self._export_metrics(
                    export_format, metric_names, start_time, end_time
                )
                logfire.info("Metrics exported", format=export_format, metrics_count=len(metric_names) if metric_names else "all")

            return [types.TextContent(
                type="text",
                text=exported_data
            )]

        except Exception as e:
            logger.error(f"Error exporting metrics: {e}")
            return [types.TextContent(
                type="text",
                text=f"Error exporting metrics: {str(e)}"
            )]

    async def _handle_get_server_status(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Handle server status requests."""
        try:
            status = {
                "server_name": "logfire-mcp",
                "version": "1.0.0",
                "status": "running",
                "uptime": time.time() - self.start_time if hasattr(self, 'start_time') else 0,
                "components": {
                    "database": "connected" if self.db_engine else "disconnected",
                    "redis": "connected" if self.redis_client else "not_configured",
                    "influxdb": "connected" if self.influx_client else "not_configured",
                    "prometheus": "active",
                    "logfire": "active"
                },
                "metrics": {
                    "total_metrics_stored": len(self.metrics_cache),
                    "active_alerts": len([a for a in self.alerts.values() if a.enabled]),
                    "health_checks": len(self.health_checks)
                },
                "system_info": {
                    "cpu_percent": psutil.cpu_percent(),
                    "memory_percent": psutil.virtual_memory().percent,
                    "disk_usage": psutil.disk_usage('/').percent
                },
                "timestamp": datetime.utcnow().isoformat()
            }

            return [types.TextContent(
                type="text",
                text=json.dumps(status, indent=2)
            )]

        except Exception as e:
            logger.error(f"Error getting server status: {e}")
            return [types.TextContent(
                type="text",
                text=f"Error getting server status: {str(e)}"
            )]

    async def _store_metric(self, metric: MetricPoint):
        """Store metric in cache and persistent storage."""
        # Store in cache
        cache_key = f"{metric.name}:{hash(frozenset(metric.tags.items()))}"
        self.metrics_cache[cache_key] = metric

        # Store in database if available
        if self.db_session:
            try:
                async with self.db_session() as session:
                    record = MetricRecord(
                        name=metric.name,
                        value=metric.value,
                        tags=json.dumps(metric.tags),
                        timestamp=metric.timestamp,
                        metric_type=metric.metric_type.value
                    )
                    session.add(record)
                    await session.commit()
            except Exception as e:
                logger.error(f"Error storing metric in database: {e}")

        # Store in Redis if available
        if self.redis_client:
            try:
                key = f"metric:{metric.name}:{int(metric.timestamp.timestamp())}"
                data = {
                    "value": metric.value,
                    "tags": metric.tags,
                    "type": metric.metric_type.value
                }
                await self.redis_client.setex(key, 86400, json.dumps(data))  # 24h TTL
            except Exception as e:
                logger.error(f"Error storing metric in Redis: {e}")

    async def _query_metrics(self, metric_name: str, start_time: Optional[str],
                           end_time: Optional[str], tags: Dict[str, str],
                           aggregation: str, group_by: List[str]) -> List[Dict]:
        """Query metrics from storage."""
        results = []

        try:
            if self.db_session:
                async with self.db_session() as session:
                    query = session.query(MetricRecord).filter(MetricRecord.name == metric_name)

                    if start_time:
                        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                        query = query.filter(MetricRecord.timestamp >= start_dt)

                    if end_time:
                        end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                        query = query.filter(MetricRecord.timestamp <= end_dt)

                    records = await query.all()

                    for record in records:
                        record_tags = json.loads(record.tags) if record.tags else {}

                        # Apply tag filters
                        if tags and not all(record_tags.get(k) == v for k, v in tags.items()):
                            continue

                        results.append({
                            "value": record.value,
                            "tags": record_tags,
                            "timestamp": record.timestamp.isoformat(),
                            "metric_type": record.metric_type
                        })

            # Apply aggregation
            if results and aggregation != "raw":
                values = [r["value"] for r in results]
                if aggregation == "avg":
                    agg_value = sum(values) / len(values)
                elif aggregation == "sum":
                    agg_value = sum(values)
                elif aggregation == "min":
                    agg_value = min(values)
                elif aggregation == "max":
                    agg_value = max(values)
                elif aggregation == "count":
                    agg_value = len(values)
                else:
                    agg_value = sum(values) / len(values)

                results = [{
                    "aggregation": aggregation,
                    "value": agg_value,
                    "count": len(values),
                    "time_range": f"{start_time} to {end_time}" if start_time and end_time else "all"
                }]

        except Exception as e:
            logger.error(f"Error querying metrics: {e}")

        return results

    async def _check_all_health(self) -> List[Dict]:
        """Perform health checks on all configured targets."""
        results = []

        # System health
        system_health = await self._check_system_health()
        results.extend(system_health)

        # MCP server health checks
        for health_check in self.health_checks.values():
            try:
                if health_check.endpoint:
                    start_time = time.time()
                    async with httpx.AsyncClient(timeout=health_check.timeout) as client:
                        response = await client.get(health_check.endpoint)
                        response_time = time.time() - start_time

                        healthy = response.status_code == health_check.expected_status

                        health_check.last_check = datetime.utcnow()
                        health_check.status = "healthy" if healthy else "unhealthy"
                        health_check.response_time = response_time

                        results.append({
                            "name": health_check.name,
                            "endpoint": health_check.endpoint,
                            "healthy": healthy,
                            "status_code": response.status_code,
                            "response_time": response_time,
                            "last_check": health_check.last_check.isoformat()
                        })

                        # Update Prometheus metric
                        if hasattr(self, 'prom_metrics'):
                            server_name = health_check.name.replace(" Health Check", "")
                            self.prom_metrics['mcp_server_health'].labels(server=server_name).set(1 if healthy else 0)

            except Exception as e:
                health_check.status = "error"
                health_check.last_check = datetime.utcnow()
                results.append({
                    "name": health_check.name,
                    "endpoint": health_check.endpoint,
                    "healthy": False,
                    "error": str(e),
                    "last_check": health_check.last_check.isoformat()
                })

        return results

    async def _check_system_health(self) -> List[Dict]:
        """Check system-level health metrics."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            results = [
                {
                    "name": "System CPU",
                    "healthy": cpu_percent < 80,
                    "value": cpu_percent,
                    "unit": "percent",
                    "threshold": 80
                },
                {
                    "name": "System Memory",
                    "healthy": memory.percent < 85,
                    "value": memory.percent,
                    "unit": "percent",
                    "threshold": 85
                },
                {
                    "name": "System Disk",
                    "healthy": disk.percent < 90,
                    "value": disk.percent,
                    "unit": "percent",
                    "threshold": 90
                }
            ]

            # Update Prometheus metrics
            if hasattr(self, 'prom_metrics'):
                self.prom_metrics['system_cpu_usage'].set(cpu_percent)
                self.prom_metrics['system_memory_usage'].set(memory.percent)
                self.prom_metrics['system_disk_usage'].labels(disk='/').set(disk.percent)

            return results

        except Exception as e:
            logger.error(f"Error checking system health: {e}")
            return [{"name": "System Health", "healthy": False, "error": str(e)}]

    async def _check_specific_endpoints(self, endpoints: List[str]) -> List[Dict]:
        """Check specific endpoints."""
        results = []

        for endpoint in endpoints:
            try:
                start_time = time.time()
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.get(endpoint)
                    response_time = time.time() - start_time

                    results.append({
                        "endpoint": endpoint,
                        "healthy": response.status_code == 200,
                        "status_code": response.status_code,
                        "response_time": response_time
                    })

            except Exception as e:
                results.append({
                    "endpoint": endpoint,
                    "healthy": False,
                    "error": str(e)
                })

        return results

    async def _check_target_health(self, target: str) -> List[Dict]:
        """Check health of a specific target."""
        if target in self.health_checks:
            health_check = self.health_checks[target]
            return await self._check_specific_endpoints([health_check.endpoint])
        else:
            return [{"target": target, "healthy": False, "error": "Target not found"}]

    async def _generate_system_overview(self, include_details: bool, time_range: str) -> Dict:
        """Generate comprehensive system overview."""
        overview = {
            "timestamp": datetime.utcnow().isoformat(),
            "time_range": time_range,
            "summary": {
                "total_mcp_servers": len(self.health_checks),
                "healthy_servers": 0,
                "active_alerts": len([a for a in self.alerts.values() if a.enabled]),
                "total_metrics": len(self.metrics_cache)
            },
            "system_metrics": await self._check_system_health(),
            "mcp_servers": {},
            "alerts": []
        }

        # Health check summary
        health_results = await self._check_all_health()
        overview["summary"]["healthy_servers"] = sum(1 for r in health_results if r.get("healthy", False))

        if include_details:
            # Group health results by server
            for result in health_results:
                if "endpoint" in result:
                    server_name = result["name"].replace(" Health Check", "")
                    overview["mcp_servers"][server_name] = result

            # Recent alerts
            overview["alerts"] = [asdict(alert) for alert in list(self.alerts.values())[:10]]

        return overview

    async def _export_metrics(self, export_format: str, metric_names: List[str],
                            start_time: Optional[str], end_time: Optional[str]) -> str:
        """Export metrics in specified format."""
        try:
            # Collect metrics to export
            all_metrics = []

            if metric_names:
                for metric_name in metric_names:
                    results = await self._query_metrics(metric_name, start_time, end_time, {}, "raw", [])
                    all_metrics.extend(results)
            else:
                # Export all metrics
                all_metrics = list(self.metrics_cache.values())

            if export_format == "json":
                return json.dumps([asdict(m) if hasattr(m, '__dict__') else m for m in all_metrics], indent=2)

            elif export_format == "csv":
                import csv
                import io
                output = io.StringIO()
                if all_metrics:
                    fieldnames = ["name", "value", "tags", "timestamp", "metric_type"]
                    writer = csv.DictWriter(output, fieldnames=fieldnames)
                    writer.writeheader()
                    for metric in all_metrics:
                        if hasattr(metric, '__dict__'):
                            row = asdict(metric)
                            row["tags"] = json.dumps(row["tags"])
                        else:
                            row = metric
                        writer.writerow(row)
                return output.getvalue()

            elif export_format == "prometheus":
                # Generate Prometheus format
                prom_output = []
                for metric in all_metrics:
                    if hasattr(metric, 'name'):
                        name = metric.name
                        value = metric.value
                        tags = metric.tags
                    else:
                        name = metric.get("name", "unknown")
                        value = metric.get("value", 0)
                        tags = metric.get("tags", {})

                    tag_str = ",".join([f'{k}="{v}"' for k, v in tags.items()]) if tags else ""
                    if tag_str:
                        prom_output.append(f"{name}{{{tag_str}}} {value}")
                    else:
                        prom_output.append(f"{name} {value}")

                return "\n".join(prom_output)

            elif export_format == "influx":
                # Generate InfluxDB line protocol
                influx_lines = []
                for metric in all_metrics:
                    if hasattr(metric, 'name'):
                        name = metric.name
                        value = metric.value
                        tags = metric.tags
                        timestamp = metric.timestamp
                    else:
                        name = metric.get("name", "unknown")
                        value = metric.get("value", 0)
                        tags = metric.get("tags", {})
                        timestamp = datetime.utcnow()

                    tag_str = ",".join([f"{k}={v}" for k, v in tags.items()]) if tags else ""
                    timestamp_ns = int(timestamp.timestamp() * 1e9) if hasattr(timestamp, 'timestamp') else int(time.time() * 1e9)

                    if tag_str:
                        influx_lines.append(f"{name},{tag_str} value={value} {timestamp_ns}")
                    else:
                        influx_lines.append(f"{name} value={value} {timestamp_ns}")

                return "\n".join(influx_lines)

            else:
                return f"Unsupported export format: {export_format}"

        except Exception as e:
            logger.error(f"Error exporting metrics: {e}")
            return f"Export error: {str(e)}"

    async def _update_prometheus_metrics(self):
        """Update Prometheus metrics with current system state."""
        try:
            # Update system metrics
            cpu_percent = psutil.cpu_percent()
            memory_percent = psutil.virtual_memory().percent
            disk_percent = psutil.disk_usage('/').percent

            self.prom_metrics['system_cpu_usage'].set(cpu_percent)
            self.prom_metrics['system_memory_usage'].set(memory_percent)
            self.prom_metrics['system_disk_usage'].labels(disk='/').set(disk_percent)

        except Exception as e:
            logger.error(f"Error updating Prometheus metrics: {e}")

    async def _metrics_collector_loop(self):
        """Background task for collecting system metrics."""
        self.start_time = time.time()

        while True:
            try:
                await asyncio.sleep(30)  # Collect every 30 seconds

                # Collect system metrics
                system_metrics = [
                    {
                        "name": "system_cpu_usage",
                        "value": psutil.cpu_percent(),
                        "metric_type": "gauge",
                        "tags": {"host": "localhost"}
                    },
                    {
                        "name": "system_memory_usage",
                        "value": psutil.virtual_memory().percent,
                        "metric_type": "gauge",
                        "tags": {"host": "localhost"}
                    },
                    {
                        "name": "system_disk_usage",
                        "value": psutil.disk_usage('/').percent,
                        "metric_type": "gauge",
                        "tags": {"host": "localhost", "disk": "/"}
                    }
                ]

                # Store metrics
                for metric_data in system_metrics:
                    metric = MetricPoint(
                        name=metric_data["name"],
                        value=metric_data["value"],
                        tags=metric_data["tags"],
                        timestamp=datetime.utcnow(),
                        metric_type=MetricType(metric_data["metric_type"])
                    )
                    await self._store_metric(metric)

                await self._update_prometheus_metrics()

            except Exception as e:
                logger.error(f"Error in metrics collector loop: {e}")

    async def _health_check_loop(self):
        """Background task for periodic health checks."""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                await self._check_all_health()

            except Exception as e:
                logger.error(f"Error in health check loop: {e}")

    async def _alert_processor_loop(self):
        """Background task for processing alerts."""
        while True:
            try:
                await asyncio.sleep(30)  # Check alerts every 30 seconds

                for alert in self.alerts.values():
                    if not alert.enabled:
                        continue

                    # Simple condition evaluation (in production, use proper expression evaluator)
                    condition_met = await self._evaluate_alert_condition(alert.condition)

                    if condition_met:
                        if not alert.last_triggered or (datetime.utcnow() - alert.last_triggered).seconds > 300:  # 5 min cooldown
                            alert.last_triggered = datetime.utcnow()
                            alert.trigger_count += 1

                            logfire.error(f"Alert triggered: {alert.name}",
                                        alert_id=alert.id,
                                        severity=alert.severity.value,
                                        condition=alert.condition)

                            # Store alert in database
                            if self.db_session:
                                try:
                                    async with self.db_session() as session:
                                        alert_record = AlertRecord(
                                            alert_id=alert.id,
                                            name=alert.name,
                                            severity=alert.severity.value,
                                            condition=alert.condition,
                                            triggered_at=alert.last_triggered
                                        )
                                        session.add(alert_record)
                                        await session.commit()
                                except Exception as e:
                                    logger.error(f"Error storing alert: {e}")

            except Exception as e:
                logger.error(f"Error in alert processor loop: {e}")

    async def _evaluate_alert_condition(self, condition: str) -> bool:
        """Evaluate alert condition (simplified implementation)."""
        try:
            # Simple condition evaluation for common patterns
            if "system_cpu_usage > 80" in condition:
                return psutil.cpu_percent() > 80
            elif "system_memory_usage > 85" in condition:
                return psutil.virtual_memory().percent > 85
            elif "mcp_server_health == 0" in condition:
                # Check if any MCP server is unhealthy
                health_results = await self._check_all_health()
                return any(not r.get("healthy", True) for r in health_results)

            return False

        except Exception as e:
            logger.error(f"Error evaluating alert condition: {e}")
            return False

    async def run(self):
        """Run the Logfire MCP Server."""
        logger.info("Starting Logfire MCP Server...")

        with logfire.span("Server startup"):
            logger.info("Server components initialized:")
            logger.info(f"- Database: {'connected' if self.db_engine else 'not available'}")
            logger.info(f"- Redis: {'connected' if self.redis_client else 'not configured'}")
            logger.info(f"- InfluxDB: {'connected' if self.influx_client else 'not configured'}")
            logger.info(f"- Health checks: {len(self.health_checks)} configured")
            logger.info(f"- Alerts: {len(self.alerts)} configured")

        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


def main():
    """Main entry point for the Logfire MCP Server."""
    try:
        server = LogfireMCPServer()
        asyncio.run(server.run())
    except KeyboardInterrupt:
        logger.info("Server shutting down...")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
