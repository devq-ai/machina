"""
MCP Cerebra Legal Tools Implementation
Provides legal reasoning and analysis capabilities
"""

from typing import Dict, Any, List
import mcp.types as types
import subprocess
import json
import os
import tempfile
from pathlib import Path

# Path to the Node.js server
CEREBRA_SERVER_PATH = Path(__file__).parent.parent / "build" / "index.js"

def get_tools() -> List[types.Tool]:
    """Define available legal reasoning tools"""
    return [
        types.Tool(
            name="legal_think",
            description="""A powerful tool for structured legal reasoning that helps analyze complex legal issues.
This tool provides domain-specific guidance and templates for different legal areas including ANSC contestations, 
consumer protection, and contract analysis.

When to use this tool:
- Breaking down complex legal problems into structured steps
- Analyzing legal requirements and compliance
- Verifying that all elements of a legal test are addressed
- Building comprehensive legal arguments with proper citations

Key features:
- Automatic detection of legal domains
- Domain-specific guidance and templates
- Support for legal citations and references
- Revision capabilities for refining legal arguments
- Thought quality feedback""",
            inputSchema={
                "type": "object",
                "properties": {
                    "thought": {
                        "type": "string",
                        "description": "The main legal reasoning content"
                    },
                    "category": {
                        "type": "string",
                        "enum": [
                            "analysis", 
                            "planning", 
                            "verification", 
                            "legal_reasoning", 
                            "ansc_contestation",
                            "consumer_protection",
                            "contract_analysis"
                        ],
                        "description": "Category of legal reasoning (optional, will be auto-detected if not provided)"
                    },
                    "references": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": "References to laws, regulations, precedents, or previous thoughts (optional)"
                    },
                    "isRevision": {
                        "type": "boolean",
                        "description": "Whether this thought revises a previous legal reasoning (optional)"
                    },
                    "revisesThoughtNumber": {
                        "type": "integer",
                        "description": "The thought number being revised (if isRevision is true)"
                    },
                    "requestGuidance": {
                        "type": "boolean",
                        "description": "Set to true to receive domain-specific legal guidance"
                    },
                    "requestTemplate": {
                        "type": "boolean",
                        "description": "Set to true to receive a template for this type of legal reasoning"
                    },
                    "thoughtNumber": {
                        "type": "integer",
                        "description": "Current thought number",
                        "minimum": 1
                    },
                    "totalThoughts": {
                        "type": "integer",
                        "description": "Estimated total thoughts needed",
                        "minimum": 1
                    },
                    "nextThoughtNeeded": {
                        "type": "boolean",
                        "description": "Whether another thought step is needed"
                    }
                },
                "required": ["thought", "thoughtNumber", "totalThoughts", "nextThoughtNeeded"]
            }
        ),
        types.Tool(
            name="legal_ask_followup_question",
            description="""A specialized tool for asking follow-up questions in legal contexts.
This tool helps gather additional information needed for legal analysis by formulating precise questions 
with domain-specific options.

When to use this tool:
- When you need additional information to complete a legal analysis
- When clarification is needed on specific legal points
- When gathering evidence or documentation for a legal case
- When exploring alternative legal interpretations

Key features:
- Automatic detection of legal domains
- Domain-specific question suggestions
- Legal terminology formatting
- Structured options for efficient information gathering""",
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The legal question to ask the user"
                    },
                    "options": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": "An array of 2-5 options for the user to choose from (optional)"
                    },
                    "context": {
                        "type": "string",
                        "description": "Additional context about the legal issue (optional)"
                    }
                },
                "required": ["question"]
            }
        ),
        types.Tool(
            name="legal_attempt_completion",
            description="""A specialized tool for presenting legal analysis results and conclusions.
This tool formats legal conclusions with proper structure, extracts and formats citations, 
and provides a professional legal document format.

When to use this tool:
- When presenting the final results of a legal analysis
- When summarizing legal findings and recommendations
- When providing a structured legal opinion
- When concluding a legal reasoning process

Key features:
- Automatic detection of legal domains
- Proper legal document formatting
- Citation extraction and formatting
- Structured sections for clear communication""",
            inputSchema={
                "type": "object",
                "properties": {
                    "result": {
                        "type": "string",
                        "description": "The legal analysis result or conclusion"
                    },
                    "command": {
                        "type": "string",
                        "description": "A CLI command to execute (optional)"
                    },
                    "context": {
                        "type": "string",
                        "description": "Additional context about the legal issue (optional)"
                    }
                },
                "required": ["result"]
            }
        ),
        types.Tool(
            name="health_check",
            description="Check server health and Node.js backend status",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]

async def call_cerebra_node_server(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Call the Node.js Cerebra server via subprocess"""
    try:
        # Check if the built server exists
        if not CEREBRA_SERVER_PATH.exists():
            return {
                "error": f"Cerebra Node.js server not found at {CEREBRA_SERVER_PATH}",
                "status": "error",
                "suggestion": "Run 'npm run build' in the mcp-cerebra-legal directory"
            }

        # Prepare the input for the Node.js server
        input_data = {
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }

        # Call the Node.js server
        result = subprocess.run(
            ["node", str(CEREBRA_SERVER_PATH)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            return {
                "error": f"Node.js server error: {result.stderr}",
                "status": "error",
                "returncode": result.returncode
            }

        # Parse the response
        try:
            response = json.loads(result.stdout)
            return response
        except json.JSONDecodeError:
            return {
                "raw_output": result.stdout,
                "status": "success_raw"
            }

    except subprocess.TimeoutExpired:
        return {
            "error": "Node.js server call timed out after 30 seconds",
            "status": "timeout"
        }
    except Exception as e:
        return {
            "error": f"Failed to call Node.js server: {str(e)}",
            "status": "error"
        }

async def handle_tool_call(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Handle tool execution"""
    
    if name == "health_check":
        # Check if Node.js server is available
        server_status = "available" if CEREBRA_SERVER_PATH.exists() else "not_built"
        
        return {
            "status": "healthy",
            "server": "mcp-cerebra-legal",
            "version": "1.0.0",
            "node_server_path": str(CEREBRA_SERVER_PATH),
            "node_server_status": server_status,
            "available_tools": ["legal_think", "legal_ask_followup_question", "legal_attempt_completion"],
            "legal_domains": [
                "ansc_contestation",
                "consumer_protection", 
                "contract_analysis",
                "legal_reasoning"
            ]
        }
    
    elif name in ["legal_think", "legal_ask_followup_question", "legal_attempt_completion"]:
        # Call the Node.js server for legal tools
        return await call_cerebra_node_server(name, arguments)
    
    else:
        return {
            "error": f"Unknown tool: {name}",
            "status": "error",
            "available_tools": ["legal_think", "legal_ask_followup_question", "legal_attempt_completion", "health_check"]
        }