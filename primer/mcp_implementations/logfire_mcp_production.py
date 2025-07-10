#!/usr/bin/env python3
"""
Logfire MCP Server - Production Implementation
Provides observability operations through Pydantic Logfire API.
"""

import os
import json
import asyncio
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from dataclasses import dataclass
from enum import Enum

try:
    import httpx
    from pydantic import BaseModel, Field
except ImportError:
    print("Installing required dependencies...")
    import subprocess
    subprocess.check_call(["pip", "install", "httpx", "pydantic"])
    import httpx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MCP Protocol Constants
JSONRPC_VERSION = "2.0"
MCP_VERSION = "2024-11-05"


class MCPError:
    """Standard MCP error codes"""
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603


class LogLevel(Enum):
    """Log levels"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class SpanStatus(Enum):
    """Span statuses"""
    OK = "ok"
    ERROR = "error"
    UNSET = "unset"


@dataclass
class LogQuery:
    """Query parameters for logs"""
    level: Optional[LogLevel] = None
    service: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = 100
    query: Optional[str] = None


@dataclass
class MetricQuery:
    """Query parameters for metrics"""
    name: Optional[str] = None
    service: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    aggregation: Optional[str] = None
    group_by: Optional[List[str]] = None


class LogfireClient:
    """Logfire API client wrapper"""

    def __init__(self, token: Optional[str] = None, project_name: Optional[str] = None):
        self.token = token or os.getenv("LOGFIRE_TOKEN")
        self.project_name = project_name or os.getenv("LOGFIRE_PROJECT_NAME", "default")
        self.base_url = os.getenv("LOGFIRE_API_URL", "https://logfire-us.pydantic.dev")

        if not self.token:
            raise ValueError("Logfire token is required")

        self.client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            },
            timeout=30.0
        )

    async def send_log(self, level: LogLevel, message: str,
                      extra: Optional[Dict[str, Any]] = None,
                      service: Optional[str] = None) -> Dict[str, Any]:
        """Send a log entry"""
        try:
            payload = {
                "level": level.value,
                "message": message,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "service": service or "mcp-server",
                "project": self.project_name
            }

            if extra:
                payload["extra"] = extra

            response = await self.client.post(
                f"{self.base_url}/api/logs",
                json=payload
            )
            response.raise_for_status()

            return response.json()
        except Exception as e:
            logger.error(f"Error sending log: {e}")
            raise

    async def query_logs(self, query: LogQuery) -> List[Dict[str, Any]]:
        """Query log entries"""
        try:
            params = {
                "project": self.project_name,
                "limit": query.limit
            }

            if query.level:
                params["level"] = query.level.value
            if query.service:
                params["service"] = query.service
            if query.trace_id:
                params["trace_id"] = query.trace_id
            if query.span_id:
                params["span_id"] = query.span_id
            if query.start_time:
                params["start_time"] = query.start_time.isoformat()
            if query.end_time:
                params["end_time"] = query.end_time.isoformat()
            if query.query:
                params["q"] = query.query

            response = await self.client.get(
                f"{self.base_url}/api/logs",
                params=params
            )
            response.raise_for_status()

            return response.json().get("logs", [])
        except Exception as e:
            logger.error(f"Error querying logs: {e}")
            raise

    async def create_span(self, name: str, attributes: Optional[Dict[str, Any]] = None,
                         parent_span_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a new span"""
        try:
            payload = {
                "name": name,
                "project": self.project_name,
                "start_time": datetime.now(timezone.utc).isoformat(),
                "attributes": attributes or {}
            }

            if parent_span_id:
                payload["parent_span_id"] = parent_span_id

            response = await self.client.post(
                f"{self.base_url}/api/spans",
                json=payload
            )
            response.raise_for_status()

            return response.json()
        except Exception as e:
            logger.error(f"Error creating span: {e}")
            raise

    async def end_span(self, span_id: str, status: SpanStatus = SpanStatus.OK,
                      error: Optional[str] = None) -> Dict[str, Any]:
        """End a span"""
        try:
            payload = {
                "end_time": datetime.now(timezone.utc).isoformat(),
                "status": status.value
            }

            if error:
                payload["error"] = error

            response = await self.client.patch(
                f"{self.base_url}/api/spans/{span_id}",
                json=payload
            )
            response.raise_for_status()

            return response.json()
        except Exception as e:
            logger.error(f"Error ending span: {e}")
            raise

    async def query_traces(self, service: Optional[str] = None,
                          start_time: Optional[datetime] = None,
                          end_time: Optional[datetime] = None,
                          limit: int = 20) -> List[Dict[str, Any]]:
        """Query traces"""
        try:
            params = {
                "project": self.project_name,
                "limit": limit
            }

            if service:
                params["service"] = service
            if start_time:
                params["start_time"] = start_time.isoformat()
            if end_time:
                params["end_time"] = end_time.isoformat()

            response = await self.client.get(
                f"{self.base_url}/api/traces",
                params=params
            )
            response.raise_for_status()

            return response.json().get("traces", [])
        except Exception as e:
            logger.error(f"Error querying traces: {e}")
            raise

    async def send_metric(self, name: str, value: float,
                         unit: Optional[str] = None,
                         tags: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Send a metric"""
        try:
            payload = {
                "name": name,
                "value": value,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "project": self.project_name,
                "tags": tags or {}
            }

            if unit:
                payload["unit"] = unit

            response = await self.client.post(
                f"{self.base_url}/api/metrics",
                json=payload
            )
            response.raise_for_status()

            return response.json()
        except Exception as e:
            logger.error(f"Error sending metric: {e}")
            raise

    async def query_metrics(self, query: MetricQuery) -> List[Dict[str, Any]]:
        """Query metrics"""
        try:
            params = {
                "project": self.project_name
            }

            if query.name:
                params["name"] = query.name
            if query.service:
                params["service"] = query.service
            if query.start_time:
                params["start_time"] = query.start_time.isoformat()
            if query.end_time:
                params["end_time"] = query.end_time.isoformat()
            if query.aggregation:
                params["aggregation"] = query.aggregation
            if query.group_by:
                params["group_by"] = ",".join(query.group_by)

            response = await self.client.get(
                f"{self.base_url}/api/metrics",
                params=params
            )
            response.raise_for_status()

            return response.json().get("metrics", [])
        except Exception as e:
            logger.error(f"Error querying metrics: {e}")
            raise

    async def get_project_stats(self) -> Dict[str, Any]:
        """Get project statistics"""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/projects/{self.project_name}/stats"
            )
            response.raise_for_status()

            return response.json()
        except Exception as e:
            logger.error(f"Error getting project stats: {e}")
            raise

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


class LogfireMCPServer:
    """Logfire MCP Server implementation"""

    def __init__(self):
        self.client: Optional[LogfireClient] = None
        self.server_info = {
            "name": "logfire-mcp",
            "version": "1.0.0",
            "description": "Pydantic Logfire observability operations",
            "author": "DevQ.ai Team"
        }
        self.active_spans: Dict[str, Dict[str, Any]] = {}

    async def initialize(self):
        """Initialize the server"""
        try:
            self.client = LogfireClient()
            logger.info("Logfire MCP Server initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Logfire client: {e}")
            self.client = None

    def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools"""
        return [
            {
                "name": "send_log",
                "description": "Send a log entry to Logfire",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "level": {"type": "string", "enum": ["debug", "info", "warning", "error", "critical"]},
                        "message": {"type": "string", "description": "Log message"},
                        "extra": {"type": "object", "description": "Additional context"},
                        "service": {"type": "string", "description": "Service name"}
                    },
                    "required": ["level", "message"]
                }
            },
            {
                "name": "query_logs",
                "description": "Query log entries from Logfire",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "level": {"type": "string", "enum": ["debug", "info", "warning", "error", "critical"]},
                        "service": {"type": "string", "description": "Filter by service"},
                        "trace_id": {"type": "string", "description": "Filter by trace ID"},
                        "span_id": {"type": "string", "description": "Filter by span ID"},
                        "start_time": {"type": "string", "description": "Start time (ISO format)"},
                        "end_time": {"type": "string", "description": "End time (ISO format)"},
                        "limit": {"type": "integer", "description": "Maximum results"},
                        "query": {"type": "string", "description": "Search query"}
                    }
                }
            },
            {
                "name": "start_span",
                "description": "Start a new span for tracing",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Span name"},
                        "attributes": {"type": "object", "description": "Span attributes"},
                        "parent_span_id": {"type": "string", "description": "Parent span ID"}
                    },
                    "required": ["name"]
                }
            },
            {
                "name": "end_span",
                "description": "End an active span",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "span_id": {"type": "string", "description": "Span ID to end"},
                        "status": {"type": "string", "enum": ["ok", "error", "unset"], "description": "Span status"},
                        "error": {"type": "string", "description": "Error message if status is error"}
                    },
                    "required": ["span_id"]
                }
            },
            {
                "name": "query_traces",
                "description": "Query traces from Logfire",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "service": {"type": "string", "description": "Filter by service"},
                        "start_time": {"type": "string", "description": "Start time (ISO format)"},
                        "end_time": {"type": "string", "description": "End time (ISO format)"},
                        "limit": {"type": "integer", "description": "Maximum results"}
                    }
                }
            },
            {
                "name": "send_metric",
                "description": "Send a metric to Logfire",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Metric name"},
                        "value": {"type": "number", "description": "Metric value"},
                        "unit": {"type": "string", "description": "Metric unit"},
                        "tags": {"type": "object", "description": "Metric tags"}
                    },
                    "required": ["name", "value"]
                }
            },
            {
                "name": "query_metrics",
                "description": "Query metrics from Logfire",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Metric name"},
                        "service": {"type": "string", "description": "Filter by service"},
                        "start_time": {"type": "string", "description": "Start time (ISO format)"},
                        "end_time": {"type": "string", "description": "End time (ISO format)"},
                        "aggregation": {"type": "string", "enum": ["avg", "sum", "min", "max", "count"]},
                        "group_by": {"type": "array", "items": {"type": "string"}, "description": "Group by tags"}
                    }
                }
            },
            {
                "name": "get_project_stats",
                "description": "Get project statistics from Logfire",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            }
        ]

    async def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tool execution"""
        if not self.client:
            return {"error": "Logfire client not initialized. Please provide LOGFIRE_TOKEN."}

        try:
            if tool_name == "send_log":
                level = LogLevel(arguments["level"])
                result = await self.client.send_log(
                    level=level,
                    message=arguments["message"],
                    extra=arguments.get("extra"),
                    service=arguments.get("service")
                )
                return {
                    "logged": True,
                    "level": level.value,
                    "message": arguments["message"]
                }

            elif tool_name == "query_logs":
                query = LogQuery(
                    level=LogLevel(arguments["level"]) if "level" in arguments else None,
                    service=arguments.get("service"),
                    trace_id=arguments.get("trace_id"),
                    span_id=arguments.get("span_id"),
                    start_time=datetime.fromisoformat(arguments["start_time"]) if "start_time" in arguments else None,
                    end_time=datetime.fromisoformat(arguments["end_time"]) if "end_time" in arguments else None,
                    limit=arguments.get("limit", 100),
                    query=arguments.get("query")
                )

                logs = await self.client.query_logs(query)
                return {
                    "logs": logs,
                    "count": len(logs)
                }

            elif tool_name == "start_span":
                result = await self.client.create_span(
                    name=arguments["name"],
                    attributes=arguments.get("attributes"),
                    parent_span_id=arguments.get("parent_span_id")
                )

                span_id = result.get("span_id")
                if span_id:
                    self.active_spans[span_id] = result

                return {
                    "span_id": span_id,
                    "trace_id": result.get("trace_id"),
                    "started": True
                }

            elif tool_name == "end_span":
                span_id = arguments["span_id"]
                status = SpanStatus(arguments.get("status", "ok"))

                result = await self.client.end_span(
                    span_id=span_id,
                    status=status,
                    error=arguments.get("error")
                )

                if span_id in self.active_spans:
                    del self.active_spans[span_id]

                return {
                    "span_id": span_id,
                    "ended": True,
                    "status": status.value
                }

            elif tool_name == "query_traces":
                traces = await self.client.query_traces(
                    service=arguments.get("service"),
                    start_time=datetime.fromisoformat(arguments["start_time"]) if "start_time" in arguments else None,
                    end_time=datetime.fromisoformat(arguments["end_time"]) if "end_time" in arguments else None,
                    limit=arguments.get("limit", 20)
                )

                return {
                    "traces": traces,
                    "count": len(traces)
                }

            elif tool_name == "send_metric":
                result = await self.client.send_metric(
                    name=arguments["name"],
                    value=arguments["value"],
                    unit=arguments.get("unit"),
                    tags=arguments.get("tags")
                )

                return {
                    "sent": True,
                    "metric": arguments["name"],
                    "value": arguments["value"]
                }

            elif tool_name == "query_metrics":
                query = MetricQuery(
                    name=arguments.get("name"),
                    service=arguments.get("service"),
                    start_time=datetime.fromisoformat(arguments["start_time"]) if "start_time" in arguments else None,
                    end_time=datetime.fromisoformat(arguments["end_time"]) if "end_time" in arguments else None,
                    aggregation=arguments.get("aggregation"),
                    group_by=arguments.get("group_by")
                )

                metrics = await self.client.query_metrics(query)
                return {
                    "metrics": metrics,
                    "count": len(metrics)
                }

            elif tool_name == "get_project_stats":
                stats = await self.client.get_project_stats()
                return stats

            else:
                raise ValueError(f"Unknown tool: {tool_name}")

        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return {"error": str(e)}

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle JSON-RPC request"""
        request_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})

        try:
            if method == "initialize":
                await self.initialize()
                result = {
                    "protocolVersion": MCP_VERSION,
                    "serverInfo": self.server_info,
                    "capabilities": {
                        "tools": True,
                        "resources": False,
                        "prompts": False,
                        "logging": False
                    },
                    "instructions": "Logfire MCP server for observability operations"
                }
            elif method == "tools/list":
                result = {"tools": self.list_tools()}
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                result = await self.handle_tool_call(tool_name, arguments)
            elif method == "health":
                result = {
                    "status": "healthy" if self.client else "no_auth",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "authenticated": self.client is not None,
                    "active_spans": len(self.active_spans)
                }
            else:
                return {
                    "jsonrpc": JSONRPC_VERSION,
                    "id": request_id,
                    "error": {
                        "code": MCPError.METHOD_NOT_FOUND,
                        "message": f"Method not found: {method}"
                    }
                }

            return {
                "jsonrpc": JSONRPC_VERSION,
                "id": request_id,
                "result": result
            }

        except Exception as e:
            logger.error(f"Request handling error: {e}")
            return {
                "jsonrpc": JSONRPC_VERSION,
                "id": request_id,
                "error": {
                    "code": MCPError.INTERNAL_ERROR,
                    "message": str(e)
                }
            }

    async def cleanup(self):
        """Cleanup resources"""
        if self.client:
            await self.client.close()

    async def run_stdio(self):
        """Run the server in stdio mode"""
        logger.info("Starting Logfire MCP Server in stdio mode")

        try:
            while True:
                # Read request from stdin
                line = await asyncio.get_event_loop().run_in_executor(
                    None, input
                )

                if not line:
                    continue

                try:
                    request = json.loads(line)
                    response = await self.handle_request(request)

                    # Write response to stdout
                    print(json.dumps(response))

                except json.JSONDecodeError as e:
                    error_response = {
                        "jsonrpc": JSONRPC_VERSION,
                        "id": None,
                        "error": {
                            "code": MCPError.PARSE_ERROR,
                            "message": f"Parse error: {e}"
                        }
                    }
                    print(json.dumps(error_response))

        except KeyboardInterrupt:
            logger.info("Server shutdown requested")
        except Exception as e:
            logger.error(f"Server error: {e}")
        finally:
            await self.cleanup()


async def main():
    """Main entry point"""
    server = LogfireMCPServer()
    await server.run_stdio()


if __name__ == "__main__":
    asyncio.run(main())
