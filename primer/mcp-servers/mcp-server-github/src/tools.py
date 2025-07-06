"""
MCP Tools Implementation
"""

from typing import Dict, Any, List
import mcp.types as types
from datetime import datetime
from github import Github
import os

def get_github_client():
    """Get a GitHub client."""
    return Github(os.environ.get("GITHUB_PAT"))

def get_tools() -> List[types.Tool]:
    """Define available tools"""
    return [
        types.Tool(
            name="create_repository",
            description="Create a new repository.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The name of the repository."
                    },
                    "description": {
                        "type": "string",
                        "description": "A short description of the repository."
                    },
                    "private": {
                        "type": "boolean",
                        "description": "Whether the repository is private."
                    },
                    "auto_init": {
                        "type": "boolean",
                        "description": "Whether to create an initial commit with a README."
                    }
                },
                "required": ["name"]
            }
        ),
        types.Tool(
            name="list_issues",
            description="List issues for a repository.",
            inputSchema={
                "type": "object",
                "properties": {
                    "owner": {
                        "type": "string",
                        "description": "The owner of the repository."
                    },
                    "repo": {
                        "type": "string",
                        "description": "The name of the repository."
                    },
                    "state": {
                        "type": "string",
                        "description": "The state of the issues to return. Can be either open, closed, or all."
                    }
                },
                "required": ["owner", "repo"]
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
    github = get_github_client()
    if name == "create_repository":
        try:
            user = github.get_user()
            repo = user.create_repo(**arguments)
            return {
                "status": "success",
                "repo": repo.full_name,
                "timestamp": str(datetime.now())
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "timestamp": str(datetime.now())
            }
    elif name == "list_issues":
        try:
            repo = github.get_repo(f"{arguments['owner']}/{arguments['repo']}")
            issues = repo.get_issues(state=arguments.get("state", "open"))
            return {
                "status": "success",
                "issues": [issue.title for issue in issues],
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
            "service": "mcp-server-github",
            "timestamp": str(datetime.now())
        }
    else:
        return {"error": f"Unknown tool: {name}"}
