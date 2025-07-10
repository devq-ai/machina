"""
MCP Tools Implementation
"""

from typing import Dict, Any, List
import mcp.types as types
from datetime import datetime
from Wikidata import Wikidata

def get_tools() -> List[types.Tool]:
    """Define available tools"""
    return [
        types.Tool(
            name="search_entity",
            description="Search for a Wikidata entity ID by its query.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The query to search for."
                    }
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="search_property",
            description="Search for a Wikidata property ID by its query.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The query to search for."
                    }
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="get_properties",
            description="Get the properties associated with a given Wikidata entity ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "string",
                        "description": "The ID of the entity to get the properties of."
                    }
                },
                "required": ["entity_id"]
            }
        ),
        types.Tool(
            name="execute_sparql",
            description="Execute a SPARQL query on Wikidata.",
            inputSchema={
                "type": "object",
                "properties": {
                    "sparql_query": {
                        "type": "string",
                        "description": "The SPARQL query to execute."
                    }
                },
                "required": ["sparql_query"]
            }
        ),
        types.Tool(
            name="get_metadata",
            description="Retrieve the English label and description for a given Wikidata entity ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "string",
                        "description": "The ID of the entity to get the metadata of."
                    },
                    "language": {
                        "type": "string",
                        "description": "The language to get the metadata in."
                    }
                },
                "required": ["entity_id"]
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
    wikidata = Wikidata()
    if name == "search_entity":
        try:
            results = wikidata.search_entities(arguments["query"])
            return {
                "status": "success",
                "results": results,
                "timestamp": str(datetime.now())
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "timestamp": str(datetime.now())
            }
    elif name == "search_property":
        try:
            results = wikidata.search_properties(arguments["query"])
            return {
                "status": "success",
                "results": results,
                "timestamp": str(datetime.now())
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "timestamp": str(datetime.now())
            }
    elif name == "get_properties":
        try:
            results = wikidata.get_entity_properties(arguments["entity_id"])
            return {
                "status": "success",
                "results": results,
                "timestamp": str(datetime.now())
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "timestamp": str(datetime.now())
            }
    elif name == "execute_sparql":
        try:
            results = wikidata.execute_sparql_query(arguments["sparql_query"])
            return {
                "status": "success",
                "results": results,
                "timestamp": str(datetime.now())
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "timestamp": str(datetime.now())
            }
    elif name == "get_metadata":
        try:
            results = wikidata.get_entity(arguments["entity_id"], arguments.get("language", "en"))
            return {
                "status": "success",
                "results": results,
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
            "service": "wikidata-mcp",
            "timestamp": str(datetime.now())
        }
    else:
        return {"error": f"Unknown tool: {name}"}
