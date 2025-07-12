#!/usr/bin/env python3
"""
Production MCP Server Template
FastMCP 2.0 template with logfire instrumentation and error handling.
"""
import asyncio
import os
from typing import Any, Dict, List, Optional
from datetime import datetime

import logfire
from fastmcp import FastMCP
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logfire
# logfire.configure(
#     token=os.getenv('LOGFIRE_WRITE_TOKEN'),
#     service_name='template-mcp-server',
#     environment='production'
# )

# Create FastMCP app instance
app = FastMCP("template-mcp")

@app.tool()
async def health_check() -> str:
    """Check server health and return status."""
    logfire.info("Health check requested")
    
    try:
        # Perform health checks
        status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "server": "template-mcp",
            "version": "1.0.0"
        }
        
        logfire.info("Health check completed", status=status)
        return f"Server healthy - {status['timestamp']}"
        
    except Exception as e:
        logfire.error("Health check failed", error=str(e))
        raise

@app.tool()
async def get_server_info() -> Dict[str, Any]:
    """Get detailed server information."""
    logfire.info("Server info requested")
    
    try:
        info = {
            "name": "template-mcp",
            "version": "1.0.0",
            "framework": "FastMCP 2.0",
            "instrumentation": "logfire",
            "environment": os.getenv("ENVIRONMENT", "production"),
            "capabilities": [
                "health_check",
                "server_info",
                "error_handling",
                "logging"
            ],
            "uptime": datetime.now().isoformat()
        }
        
        logfire.info("Server info retrieved", info=info)
        return info
        
    except Exception as e:
        logfire.error("Failed to get server info", error=str(e))
        raise

@app.tool()
async def echo_message(message: str, count: int = 1) -> str:
    """Echo a message the specified number of times."""
    logfire.info("Echo message requested", message=message, count=count)
    
    try:
        if count < 1 or count > 10:
            raise ValueError("Count must be between 1 and 10")
        
        result = " ".join([message] * count)
        
        logfire.info("Echo message completed", 
                    original_message=message, 
                    count=count, 
                    result_length=len(result))
        
        return result
        
    except Exception as e:
        logfire.error("Echo message failed", 
                     message=message, 
                     count=count, 
                     error=str(e))
        raise

@app.tool()
async def list_capabilities() -> List[str]:
    """List all available server capabilities."""
    logfire.info("Capabilities list requested")
    
    try:
        # Get tools from the FastMCP app
        capabilities = []
        
        if hasattr(app, '_tools'):
            capabilities = list(app._tools.keys())
        
        logfire.info("Capabilities listed", 
                    count=len(capabilities), 
                    capabilities=capabilities)
        
        return capabilities
        
    except Exception as e:
        logfire.error("Failed to list capabilities", error=str(e))
        raise

@app.tool()
async def test_error_handling(should_error: bool = False) -> str:
    """Test error handling capabilities."""
    logfire.info("Error handling test requested", should_error=should_error)
    
    try:
        if should_error:
            # Intentionally trigger an error for testing
            raise RuntimeError("This is a test error for validation purposes")
        
        result = "Error handling test passed - no error triggered"
        logfire.info("Error handling test completed successfully")
        return result
        
    except Exception as e:
        logfire.error("Error handling test failed", 
                     should_error=should_error, 
                     error=str(e))
        raise

# Server startup and shutdown handlers

async def startup():
    """Server startup handler."""
    logfire.info("Template MCP server starting up")

  
async def shutdown():
    """Server shutdown handler."""
    logfire.info("Template MCP server shutting down")

if __name__ == "__main__":
    import asyncio
    asyncio.run(app.run_stdio_async())