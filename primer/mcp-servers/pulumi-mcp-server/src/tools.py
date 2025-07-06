"""
MCP Tools Implementation
"""

from typing import Dict, Any, List
import mcp.types as types
from datetime import datetime
from pulumi.automation import LocalWorkspace

def get_tools() -> List[types.Tool]:
    """Define available tools"""
    return [
        types.Tool(
            name="preview",
            description="Runs `pulumi preview` on a specified stack.",
            inputSchema={
                "type": "object",
                "properties": {
                    "workDir": {
                        "type": "string",
                        "description": "The working directory containing the `Pulumi.yaml` project file."
                    },
                    "stackName": {
                        "type": "string",
                        "description": "The stack name to operate on (defaults to 'dev')."
                    }
                },
                "required": ["workDir"]
            }
        ),
        types.Tool(
            name="up",
            description="Runs `pulumi up` to deploy changes for a specified stack.",
            inputSchema={
                "type": "object",
                "properties": {
                    "workDir": {
                        "type": "string",
                        "description": "The working directory containing the `Pulumi.yaml` project file."
                    },
                    "stackName": {
                        "type": "string",
                        "description": "The stack name to operate on (defaults to 'dev')."
                    }
                },
                "required": ["workDir"]
            }
        ),
        types.Tool(
            name="stack_output",
            description="Retrieves outputs from a specified stack after a successful deployment.",
            inputSchema={
                "type": "object",
                "properties": {
                    "workDir": {
                        "type": "string",
                        "description": "The working directory containing the `Pulumi.yaml` project file."
                    },
                    "stackName": {
                        "type": "string",
                        "description": "The stack name to retrieve outputs from (defaults to 'dev')."
                    },
                    "outputName": {
                        "type": "string",
                        "description": "The specific stack output name to retrieve. If omitted, all outputs for the stack are returned."
                    }
                },
                "required": ["workDir"]
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
    if name == "preview":
        try:
            stack = LocalWorkspace(work_dir=arguments["workDir"]).select_stack(arguments.get("stackName", "dev"))
            preview = stack.preview()
            return {
                "status": "success",
                "preview": preview.stdout,
                "timestamp": str(datetime.now())
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "timestamp": str(datetime.now())
            }
    elif name == "up":
        try:
            stack = LocalWorkspace(work_dir=arguments["workDir"]).select_stack(arguments.get("stackName", "dev"))
            up = stack.up()
            return {
                "status": "success",
                "up": up.stdout,
                "timestamp": str(datetime.now())
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "timestamp": str(datetime.now())
            }
    elif name == "stack_output":
        try:
            stack = LocalWorkspace(work_dir=arguments["workDir"]).select_stack(arguments.get("stackName", "dev"))
            output = stack.outputs()
            if "outputName" in arguments:
                output = output[arguments["outputName"]].value
            return {
                "status": "success",
                "output": output,
                "timestamp": str(datetime.now())
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "timestamp": str(datetime.now())
            }
    elif name == "health_check":
        return {
            "status": "healthy",
            "service": "pulumi-mcp-server",
            "timestamp": str(datetime.now())
        }
    else:
        return {"error": f"Unknown tool: {name}"}
