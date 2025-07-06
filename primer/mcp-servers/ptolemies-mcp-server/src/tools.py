"""
MCP Tools Implementation
"""

from typing import Dict, Any, List
import mcp.types as types
from datetime import datetime
from neo4j import GraphDatabase
import os

def get_neo4j_driver():
    """Get a Neo4j driver."""
    return GraphDatabase.driver(
        os.environ.get("NEO4J_URI"),
        auth=(os.environ.get("NEO4J_USERNAME"), os.environ.get("NEO4J_PASSWORD"))
    )

def get_tools() -> List[types.Tool]:
    """Define available tools"""
    return [
        types.Tool(
            name="create_node",
            description="Creates a new node in the graph.",
            inputSchema={
                "type": "object",
                "properties": {
                    "label": {
                        "type": "string",
                        "description": "The label for the new node."
                    },
                    "properties": {
                        "type": "object",
                        "description": "The properties for the new node."
                    }
                },
                "required": ["label", "properties"]
            }
        ),
        types.Tool(
            name="create_relationship",
            description="Creates a new relationship between two nodes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_node_label": {
                        "type": "string",
                        "description": "The label of the start node."
                    },
                    "start_node_properties": {
                        "type": "object",
                        "description": "The properties of the start node."
                    },
                    "end_node_label": {
                        "type": "string",
                        "description": "The label of the end node."
                    },
                    "end_node_properties": {
                        "type": "object",
                        "description": "The properties of the end node."
                    },
                    "relationship_type": {
                        "type": "string",
                        "description": "The type of the relationship."
                    },
                    "relationship_properties": {
                        "type": "object",
                        "description": "The properties of the relationship."
                    }
                },
                "required": ["start_node_label", "start_node_properties", "end_node_label", "end_node_properties", "relationship_type"]
            }
        ),
        types.Tool(
            name="query_graph",
            description="Queries the graph using Cypher.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The Cypher query to execute."
                    }
                },
                "required": ["query"]
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
    driver = get_neo4j_driver()
    with driver.session() as session:
        if name == "create_node":
            try:
                result = session.run(
                    "CREATE (n:{label} $properties) RETURN n".format(label=arguments["label"]),
                    properties=arguments["properties"]
                )
                return {
                    "status": "success",
                    "result": result.single()[0].__properties__,
                    "timestamp": str(datetime.now())
                }
            except Exception as e:
                return {
                    "status": "error",
                    "message": str(e),
                    "timestamp": str(datetime.now())
                }
        elif name == "create_relationship":
            try:
                result = session.run(
                    "MATCH (a:{start_node_label} $start_node_properties), (b:{end_node_label} $end_node_properties) "
                    "CREATE (a)-[r:{relationship_type} $relationship_properties]->(b) RETURN r".format(**arguments),
                    **arguments
                )
                return {
                    "status": "success",
                    "result": result.single()[0].__properties__,
                    "timestamp": str(datetime.now())
                }
            except Exception as e:
                return {
                    "status": "error",
                    "message": str(e),
                    "timestamp": str(datetime.now())
                }
        elif name == "query_graph":
            try:
                result = session.run(arguments["query"])
                return {
                    "status": "success",
                    "result": [record.data() for record in result],
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
                "service": "ptolemies-mcp-server",
                "timestamp": str(datetime.now())
            }
        else:
            return {"error": f"Unknown tool: {name}"}
