#!/usr/bin/env python3
"""
Logfire MCP Server Package

Advanced observability and monitoring server implementing the MCP protocol.
Provides comprehensive monitoring, metrics collection, alerting, and health checks
for MCP servers and the broader DevQ.ai ecosystem using Pydantic Logfire.

This package follows DevQ.ai standards with comprehensive MCP integration,
async operations, structured logging, and robust error handling.
"""

__version__ = "1.0.0"
__author__ = "DevQ.ai Team"
__email__ = "dion@devq.ai"
__description__ = "Advanced observability and monitoring MCP server with Logfire integration"

try:
    from server import (
        LogfireMCPServer,
        MetricType,
        AlertSeverity,
        MonitoringScope,
        MetricPoint,
        Alert,
        HealthCheck
    )
except ImportError:
    # Fallback for when imported as a package
    from .server import (
        LogfireMCPServer,
        MetricType,
        AlertSeverity,
        MonitoringScope,
        MetricPoint,
        Alert,
        HealthCheck
    )

__all__ = [
    "LogfireMCPServer",
    "MetricType",
    "AlertSeverity",
    "MonitoringScope",
    "MetricPoint",
    "Alert",
    "HealthCheck"
]
