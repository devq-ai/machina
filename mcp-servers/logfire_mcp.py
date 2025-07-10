#!/usr/bin/env python3
"""
Logfire MCP Server
Integrated observability and logging with structured monitoring using FastMCP framework.
"""

import asyncio
import json
import os
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add parent directory to path for FastMCP imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastmcp import FastMCP
import logfire

try:
    import httpx
    from pydantic import BaseModel, Field
    LOGFIRE_DEPS_AVAILABLE = True
except ImportError:
    LOGFIRE_DEPS_AVAILABLE = False
    httpx = None
    BaseModel = object
    def Field(*args, **kwargs):
        return None


class LogfireQuery(BaseModel):
    """Logfire query parameters"""
    start_time: Optional[str] = Field(None, description="Start time for query (ISO format)")
    end_time: Optional[str] = Field(None, description="End time for query (ISO format)")
    level: Optional[str] = Field(None, description="Log level filter")
    service: Optional[str] = Field(None, description="Service name filter")
    message: Optional[str] = Field(None, description="Message content filter")
    limit: int = Field(100, description="Maximum number of results")


class LogfireMCP:
    """
    Logfire MCP Server using FastMCP framework

    Provides comprehensive Logfire observability operations including:
    - Log querying and filtering
    - Metrics and monitoring
    - Alert management
    - Project management
    - Dashboard operations
    - Performance monitoring
    """

    def __init__(self):
        self.mcp = FastMCP("logfire-mcp", version="1.0.0", description="Logfire observability and monitoring")
        self.logfire_token = os.getenv("LOGFIRE_TOKEN")
        self.logfire_api_url = os.getenv("LOGFIRE_API_URL", "https://logfire-us.pydantic.dev")
        self.project_name = os.getenv("LOGFIRE_PROJECT_NAME")
        self.http_client: Optional[httpx.AsyncClient] = None
        self._setup_tools()
        self._initialize_client()

    def _initialize_client(self):
        """Initialize Logfire client and HTTP client"""
        if not LOGFIRE_DEPS_AVAILABLE:
            logfire.warning("Logfire dependencies not available. Install with: pip install httpx pydantic")
            return

        if self.logfire_token:
            try:
                # Configure logfire
                logfire.configure(token=self.logfire_token)

                # Initialize HTTP client for API calls
                self.http_client = httpx.AsyncClient(
                    base_url=self.logfire_api_url,
                    headers={
                        "Authorization": f"Bearer {self.logfire_token}",
                        "Content-Type": "application/json"
                    },
                    timeout=30.0
                )
                logfire.info("Logfire MCP client initialized successfully")
            except Exception as e:
                logfire.error(f"Failed to initialize Logfire client: {str(e)}")
        else:
            logfire.warning("Logfire token not provided. Set LOGFIRE_TOKEN environment variable")

    def _setup_tools(self):
        """Setup Logfire MCP tools"""

        @self.mcp.tool(
            name="query_logs",
            description="Query Logfire logs with filtering options",
            input_schema={
                "type": "object",
                "properties": {
                    "start_time": {"type": "string", "description": "Start time (ISO format)"},
                    "end_time": {"type": "string", "description": "End time (ISO format)"},
                    "level": {"type": "string", "description": "Log level (debug, info, warning, error)"},
                    "service": {"type": "string", "description": "Service name filter"},
                    "message": {"type": "string", "description": "Message content filter"},
                    "limit": {"type": "integer", "description": "Maximum results", "default": 100}
                }
            }
        )
        async def query_logs(start_time: str = None, end_time: str = None, level: str = None,
                           service: str = None, message: str = None, limit: int = 100) -> Dict[str, Any]:
            """Query Logfire logs with filtering"""
            if not self._check_client():
                return {"error": "Logfire client not available"}

            try:
                # Build query parameters
                params = {
                    "limit": limit
                }

                if start_time:
                    params["start_time"] = start_time
                if end_time:
                    params["end_time"] = end_time
                if level:
                    params["level"] = level
                if service:
                    params["service"] = service
                if message:
                    params["message"] = message

                # Make API request
                response = await self.http_client.get(
                    f"/api/v1/projects/{self.project_name}/logs",
                    params=params
                )
                response.raise_for_status()

                data = response.json()
                return {
                    "logs": data.get("logs", []),
                    "total_count": data.get("total_count", 0),
                    "query_params": params
                }

            except Exception as e:
                logfire.error(f"Failed to query logs: {str(e)}")
                return {"error": f"Log query failed: {str(e)}"}

        @self.mcp.tool(
            name="get_metrics",
            description="Get Logfire metrics and performance data",
            input_schema={
                "type": "object",
                "properties": {
                    "metric_type": {"type": "string", "description": "Type of metric (spans, errors, performance)"},
                    "time_range": {"type": "string", "description": "Time range (1h, 6h, 24h, 7d)"},
                    "service": {"type": "string", "description": "Service name filter"}
                }
            }
        )
        async def get_metrics(metric_type: str = "spans", time_range: str = "1h", service: str = None) -> Dict[str, Any]:
            """Get Logfire metrics and performance data"""
            if not self._check_client():
                return {"error": "Logfire client not available"}

            try:
                params = {
                    "metric_type": metric_type,
                    "time_range": time_range
                }

                if service:
                    params["service"] = service

                response = await self.http_client.get(
                    f"/api/v1/projects/{self.project_name}/metrics",
                    params=params
                )
                response.raise_for_status()

                data = response.json()
                return {
                    "metrics": data.get("metrics", []),
                    "summary": data.get("summary", {}),
                    "time_range": time_range,
                    "metric_type": metric_type
                }

            except Exception as e:
                logfire.error(f"Failed to get metrics: {str(e)}")
                return {"error": f"Metrics query failed: {str(e)}"}

        @self.mcp.tool(
            name="create_alert",
            description="Create a Logfire alert rule",
            input_schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Alert name"},
                    "condition": {"type": "string", "description": "Alert condition"},
                    "threshold": {"type": "number", "description": "Alert threshold"},
                    "notification_channel": {"type": "string", "description": "Notification channel"}
                },
                "required": ["name", "condition", "threshold"]
            }
        )
        async def create_alert(name: str, condition: str, threshold: float,
                             notification_channel: str = None) -> Dict[str, Any]:
            """Create a Logfire alert rule"""
            if not self._check_client():
                return {"error": "Logfire client not available"}

            try:
                alert_data = {
                    "name": name,
                    "condition": condition,
                    "threshold": threshold,
                    "notification_channel": notification_channel,
                    "enabled": True
                }

                response = await self.http_client.post(
                    f"/api/v1/projects/{self.project_name}/alerts",
                    json=alert_data
                )
                response.raise_for_status()

                data = response.json()
                return {
                    "alert_id": data.get("id"),
                    "name": name,
                    "status": "created",
                    "alert_data": alert_data
                }

            except Exception as e:
                logfire.error(f"Failed to create alert: {str(e)}")
                return {"error": f"Alert creation failed: {str(e)}"}

        @self.mcp.tool(
            name="list_alerts",
            description="List all Logfire alerts",
            input_schema={
                "type": "object",
                "properties": {
                    "status": {"type": "string", "description": "Filter by status (active, disabled, triggered)"}
                }
            }
        )
        async def list_alerts(status: str = None) -> Dict[str, Any]:
            """List Logfire alerts"""
            if not self._check_client():
                return {"error": "Logfire client not available"}

            try:
                params = {}
                if status:
                    params["status"] = status

                response = await self.http_client.get(
                    f"/api/v1/projects/{self.project_name}/alerts",
                    params=params
                )
                response.raise_for_status()

                data = response.json()
                return {
                    "alerts": data.get("alerts", []),
                    "total_count": len(data.get("alerts", [])),
                    "filter_status": status
                }

            except Exception as e:
                logfire.error(f"Failed to list alerts: {str(e)}")
                return {"error": f"Alert listing failed: {str(e)}"}

        @self.mcp.tool(
            name="get_project_info",
            description="Get Logfire project information and statistics",
            input_schema={
                "type": "object",
                "properties": {}
            }
        )
        async def get_project_info() -> Dict[str, Any]:
            """Get Logfire project information"""
            if not self._check_client():
                return {"error": "Logfire client not available"}

            try:
                response = await self.http_client.get(
                    f"/api/v1/projects/{self.project_name}"
                )
                response.raise_for_status()

                data = response.json()
                return {
                    "project_name": self.project_name,
                    "project_info": data,
                    "api_url": self.logfire_api_url
                }

            except Exception as e:
                logfire.error(f"Failed to get project info: {str(e)}")
                return {"error": f"Project info query failed: {str(e)}"}

        @self.mcp.tool(
            name="create_custom_log",
            description="Create a custom log entry in Logfire",
            input_schema={
                "type": "object",
                "properties": {
                    "level": {"type": "string", "description": "Log level (debug, info, warning, error)"},
                    "message": {"type": "string", "description": "Log message"},
                    "service": {"type": "string", "description": "Service name"},
                    "tags": {"type": "object", "description": "Additional tags/metadata"}
                },
                "required": ["level", "message"]
            }
        )
        async def create_custom_log(level: str, message: str, service: str = None,
                                  tags: Dict[str, Any] = None) -> Dict[str, Any]:
            """Create a custom log entry"""
            if not self._check_client():
                return {"error": "Logfire client not available"}

            try:
                # Use logfire directly to create the log
                log_data = {
                    "message": message,
                    "service": service or "logfire-mcp",
                    "tags": tags or {}
                }

                if level.lower() == "debug":
                    logfire.debug(message, **log_data)
                elif level.lower() == "info":
                    logfire.info(message, **log_data)
                elif level.lower() == "warning":
                    logfire.warning(message, **log_data)
                elif level.lower() == "error":
                    logfire.error(message, **log_data)
                else:
                    logfire.info(message, **log_data)

                return {
                    "status": "logged",
                    "level": level,
                    "message": message,
                    "service": service,
                    "timestamp": datetime.utcnow().isoformat()
                }

            except Exception as e:
                logfire.error(f"Failed to create log: {str(e)}")
                return {"error": f"Log creation failed: {str(e)}"}

        @self.mcp.tool(
            name="get_performance_stats",
            description="Get performance statistics and traces",
            input_schema={
                "type": "object",
                "properties": {
                    "service": {"type": "string", "description": "Service name filter"},
                    "operation": {"type": "string", "description": "Operation name filter"},
                    "time_range": {"type": "string", "description": "Time range (1h, 6h, 24h)"}
                }
            }
        )
        async def get_performance_stats(service: str = None, operation: str = None,
                                      time_range: str = "1h") -> Dict[str, Any]:
            """Get performance statistics and traces"""
            if not self._check_client():
                return {"error": "Logfire client not available"}

            try:
                params = {
                    "time_range": time_range,
                    "type": "performance"
                }

                if service:
                    params["service"] = service
                if operation:
                    params["operation"] = operation

                response = await self.http_client.get(
                    f"/api/v1/projects/{self.project_name}/traces",
                    params=params
                )
                response.raise_for_status()

                data = response.json()
                return {
                    "traces": data.get("traces", []),
                    "performance_summary": data.get("summary", {}),
                    "filters": {
                        "service": service,
                        "operation": operation,
                        "time_range": time_range
                    }
                }

            except Exception as e:
                logfire.error(f"Failed to get performance stats: {str(e)}")
                return {"error": f"Performance query failed: {str(e)}"}

        @self.mcp.tool(
            name="export_logs",
            description="Export logs to different formats",
            input_schema={
                "type": "object",
                "properties": {
                    "format": {"type": "string", "description": "Export format (json, csv, txt)"},
                    "start_time": {"type": "string", "description": "Start time (ISO format)"},
                    "end_time": {"type": "string", "description": "End time (ISO format)"},
                    "filters": {"type": "object", "description": "Additional filters"}
                },
                "required": ["format"]
            }
        )
        async def export_logs(format: str, start_time: str = None, end_time: str = None,
                            filters: Dict[str, Any] = None) -> Dict[str, Any]:
            """Export logs to different formats"""
            if not self._check_client():
                return {"error": "Logfire client not available"}

            try:
                export_params = {
                    "format": format,
                    "start_time": start_time,
                    "end_time": end_time,
                    "filters": filters or {}
                }

                response = await self.http_client.post(
                    f"/api/v1/projects/{self.project_name}/exports",
                    json=export_params
                )
                response.raise_for_status()

                data = response.json()
                return {
                    "export_id": data.get("export_id"),
                    "format": format,
                    "status": "initiated",
                    "download_url": data.get("download_url"),
                    "parameters": export_params
                }

            except Exception as e:
                logfire.error(f"Failed to export logs: {str(e)}")
                return {"error": f"Log export failed: {str(e)}"}

    def _check_client(self) -> bool:
        """Check if Logfire client is available and configured"""
        if not LOGFIRE_DEPS_AVAILABLE:
            return False
        return self.logfire_token is not None and self.http_client is not None

    async def run(self):
        """Run the Logfire MCP server"""
        try:
            await self.mcp.run_stdio()
        finally:
            if self.http_client:
                await self.http_client.aclose()


async def main():
    """Main entry point"""
    server = LogfireMCP()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
