"""
MCP Tools Implementation
"""

from typing import Dict, Any, List
import mcp.types as types
from datetime import datetime
from jupyter_client import KernelManager
import asyncio

KERNELS = {}


def get_tools() -> List[types.Tool]:
    """Define available tools"""
    return [
        types.Tool(
            name="start_kernel",
            description="Starts a new Jupyter kernel.",
            inputSchema={
                "type": "object",
                "properties": {},
            }
        ),
        types.Tool(
            name="stop_kernel",
            description="Stops a Jupyter kernel.",
            inputSchema={
                "type": "object",
                "properties": {
                    "kernel_id": {
                        "type": "string",
                        "description": "The ID of the kernel to stop."
                    }
                },
                "required": ["kernel_id"]
            }
        ),
        types.Tool(
            name="execute_code",
            description="Executes code in a Jupyter kernel.",
            inputSchema={
                "type": "object",
                "properties": {
                    "kernel_id": {
                        "type": "string",
                        "description": "The ID of the kernel to use."
                    },
                    "code": {
                        "type": "string",
                        "description": "The code to execute."
                    }
                },
                "required": ["kernel_id", "code"]
            }
        ),
        types.Tool(
            name="health_check",
            description="Check server health",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]


async def handle_tool_call(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Handle tool execution"""
    if name == "start_kernel":
        try:
            km = KernelManager()
            km.start_kernel()
            kernel_id = km.kernel_id
            KERNELS[kernel_id] = km
            return {
                "status": "success",
                "kernel_id": kernel_id,
                "timestamp": str(datetime.now())
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "timestamp": str(datetime.now())
            }
    elif name == "stop_kernel":
        kernel_id = arguments["kernel_id"]
        if kernel_id in KERNELS:
            try:
                km = KERNELS[kernel_id]
                km.shutdown_kernel()
                del KERNELS[kernel_id]
                return {
                    "status": "success",
                    "kernel_id": kernel_id,
                    "timestamp": str(datetime.now())
                }
            except Exception as e:
                return {
                    "status": "error",
                    "message": str(e),
                    "timestamp": str(datetime.now())
                }
        else:
            return {
                "status": "error",
                "message": "Kernel not found.",
                "timestamp": str(datetime.now())
            }
    elif name == "execute_code":
        kernel_id = arguments["kernel_id"]
        if kernel_id in KERNELS:
            try:
                km = KERNELS[kernel_id]
                kc = km.client()
                kc.start_channels()
                msg_id = kc.execute(arguments["code"])
                
                # Wait for the result
                # This is a simplified approach. A real implementation would handle
                # different message types (stream, display_data, etc.)
                # and timeouts.
                while True:
                    try:
                        msg = kc.get_iopub_msg(timeout=1)
                        if msg['parent_header'].get('msg_id') == msg_id:
                            if msg['header']['msg_type'] == 'stream':
                                return {
                                    "status": "success",
                                    "result": msg['content']['text'],
                                    "timestamp": str(datetime.now())
                                }
                            elif msg['header']['msg_type'] == 'execute_result':
                                return {
                                    "status": "success",
                                    "result": msg['content']['data']['text/plain'],
                                    "timestamp": str(datetime.now())
                                }
                            elif msg['header']['msg_type'] == 'error':
                                return {
                                    "status": "error",
                                    "message": msg['content']['evalue'],
                                    "timestamp": str(datetime.now())
                                }
                    except Exception:
                        return {
                            "status": "error",
                            "message": "Timeout waiting for result.",
                            "timestamp": str(datetime.now())
                        }
            except Exception as e:
                return {
                    "status": "error",
                    "message": str(e),
                    "timestamp": str(datetime.now())
                }
        else:
            return {
                "status": "error",
                "message": "Kernel not found.",
                "timestamp": str(datetime.now())
            }
    elif name == "health_check":
        return {
            "status": "healthy",
            "service": "jupyter-mcp",
            "timestamp": str(datetime.now())
        }
    else:
        return {"error": f"Unknown tool: {name}"}
