"""
MCP Tools Implementation
"""

from typing import Dict, Any, List
import mcp.types as types
from datetime import datetime
from pybuildkite.buildkite import Buildkite
import os

def get_buildkite_client():
    """Get a Buildkite client."""
    return Buildkite(
        access_token=os.environ.get("BUILDKITE_ACCESS_TOKEN")
    )

def get_tools() -> List[types.Tool]:
    """Define available tools"""
    return [
        types.Tool(
            name="list_pipelines",
            description="Lists all pipelines.",
            inputSchema={
                "type": "object",
                "properties": {
                    "organization": {
                        "type": "string",
                        "description": "The organization slug."
                    }
                },
                "required": ["organization"]
            }
        ),
        types.Tool(
            name="list_builds",
            description="Lists all builds for a pipeline.",
            inputSchema={
                "type": "object",
                "properties": {
                    "organization": {
                        "type": "string",
                        "description": "The organization slug."
                    },
                    "pipeline": {
                        "type": "string",
                        "description": "The pipeline slug."
                    }
                },
                "required": ["organization", "pipeline"]
            }
        ),
        types.Tool(
            name="get_build",
            description="Gets a specific build.",
            inputSchema={
                "type": "object",
                "properties": {
                    "organization": {
                        "type": "string",
                        "description": "The organization slug."
                    },
                    "pipeline": {
                        "type": "string",
                        "description": "The pipeline slug."
                    },
                    "build_number": {
                        "type": "integer",
                        "description": "The build number."
                    }
                },
                "required": ["organization", "pipeline", "build_number"]
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
    buildkite = get_buildkite_client()
    if name == "list_pipelines":
        try:
            pipelines = buildkite.pipelines().list_all_for_organization(arguments["organization"])
            return {
                "status": "success",
                "pipelines": pipelines,
                "timestamp": str(datetime.now())
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "timestamp": str(datetime.now())
            }
    elif name == "list_builds":
        try:
            builds = buildkite.builds().list_all_for_pipeline(**arguments)
            return {
                "status": "success",
                "builds": builds,
                "timestamp": str(datetime.now())
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "timestamp": str(datetime.now())
            }
    elif name == "get_build":
        try:
            build = buildkite.builds().get_build_by_number(**arguments)
            return {
                "status": "success",
                "build": build,
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
            "service": "mcp-server-buildkite",
            "timestamp": str(datetime.now())
        }
    else:
        return {"error": f"Unknown tool: {name}"}
