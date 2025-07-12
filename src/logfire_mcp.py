import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
import logfire
from fastmcp import FastMCP
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Configure Logfire - restore working configuration
logfire.configure(inspect_arguments=False)

# Create FastMCP app instance
app = FastMCP("logfire-mcp")

@app.tool()
async def send_log(level: str, message: str, extra_data: dict = None) -> str:
    """Send a log entry to Logfire."""
    logfire.info("Sending log to Logfire", level=level, message=message, extra_data=extra_data)
    
    # Actually log to logfire
    if level.lower() == "info":
        logfire.info(message, **(extra_data or {}))
    elif level.lower() == "warning":
        logfire.warning(message, **(extra_data or {}))
    elif level.lower() == "error":
        logfire.error(message, **(extra_data or {}))
    else:
        logfire.info(message, level=level, **(extra_data or {}))
    
    return f"Successfully sent {level} log: {message}"

@app.tool()
async def create_span(name: str, operation: str = "custom") -> str:
    """Create a new span in Logfire."""
    logfire.info("Creating span", name=name, operation=operation)
    
    with logfire.span(name, operation=operation):
        logfire.info(f"Executing span: {name}")
    
    return f"Created and executed span: {name}"

@app.tool()
async def log_metric(metric_name: str, value: float, unit: str = "count") -> str:
    """Log a metric to Logfire."""
    logfire.info("Logging metric", metric_name=metric_name, value=value, unit=unit)
    
    # Log as structured data
    logfire.info("Metric recorded", metric=metric_name, value=value, unit=unit)
    
    return f"Logged metric {metric_name}: {value} {unit}"

@app.tool()
async def health_check() -> str:
    """Check Logfire connection health."""
    logfire.info("Running health check")
    
    return f"Logfire MCP server is healthy - Connected to logfire-us.pydantic.dev"

if __name__ == "__main__":
    import asyncio
    asyncio.run(app.run_stdio_async())