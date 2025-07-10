"""
FastMCP Tools Module
Utilities for tool registration and management in FastMCP framework.
"""

import asyncio
import inspect
from typing import Dict, Any, Optional, Callable, Union, get_type_hints, List
from dataclasses import dataclass
from datetime import datetime
import mcp.types as types
import logfire


@dataclass
class MCPTool:
    """Represents an MCP tool with metadata"""
    name: str
    function: Callable
    description: str
    input_schema: Dict[str, Any]
    is_async: bool
    created_at: datetime
    call_count: int = 0
    last_called: Optional[datetime] = None
    error_count: int = 0
    last_error: Optional[str] = None


def tool(
    name: Optional[str] = None,
    description: Optional[str] = None,
    input_schema: Optional[Dict[str, Any]] = None,
    auto_schema: bool = True
):
    """
    Decorator to register a function as an MCP tool

    Args:
        name: Tool name (defaults to function name)
        description: Tool description (defaults to function docstring)
        input_schema: JSON schema for inputs (auto-generated if not provided)
        auto_schema: Whether to auto-generate schema from function signature
    """
    def decorator(func: Callable) -> Callable:
        tool_name = name or func.__name__
        tool_description = description or func.__doc__ or f"Execute {tool_name}"

        # Auto-generate schema from function signature if requested
        if input_schema is None and auto_schema:
            schema = _generate_schema_from_function(func)
        else:
            schema = input_schema or {
                "type": "object",
                "properties": {},
                "required": []
            }

        # Add metadata to function
        setattr(func, '_mcp_tool_metadata', {
            "name": tool_name,
            "description": tool_description,
            "input_schema": schema,
            "is_async": asyncio.iscoroutinefunction(func),
            "created_at": datetime.now()
        })

        return func

    return decorator


def _generate_schema_from_function(func: Callable) -> Dict[str, Any]:
    """
    Auto-generate JSON schema from function signature

    Args:
        func: Function to analyze

    Returns:
        JSON schema dictionary
    """
    sig = inspect.signature(func)
    type_hints = get_type_hints(func)

    properties = {}
    required = []

    for param_name, param in sig.parameters.items():
        param_type = type_hints.get(param_name, str)

        # Convert Python types to JSON schema types
        json_type = _python_type_to_json_type(param_type)

        properties[param_name] = {
            "type": json_type,
            "description": f"Parameter {param_name}"
        }

        # Add to required if no default value
        if param.default == inspect.Parameter.empty:
            required.append(param_name)

    return {
        "type": "object",
        "properties": properties,
        "required": required
    }


def _python_type_to_json_type(python_type) -> str:
    """
    Convert Python type to JSON schema type

    Args:
        python_type: Python type annotation

    Returns:
        JSON schema type string
    """
    type_mapping = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object"
    }

    # Handle Union types (Optional[T] is Union[T, None])
    if hasattr(python_type, '__origin__'):
        if python_type.__origin__ is Union:
            # For Optional types, return the non-None type
            non_none_types = [t for t in python_type.__args__ if t is not type(None)]
            if non_none_types:
                return _python_type_to_json_type(non_none_types[0])
        elif python_type.__origin__ is list:
            return "array"
        elif python_type.__origin__ is dict:
            return "object"

    return type_mapping.get(python_type, "string")


class ToolRegistry:
    """Registry for managing MCP tools"""

    def __init__(self):
        self.tools: Dict[str, MCPTool] = {}
        self.logger = logfire

    def register_tool(self, func: Callable[..., Any]) -> MCPTool:
        """
        Register a function as an MCP tool

        Args:
            func: Function to register

        Returns:
            MCPTool instance
        """
        if not hasattr(func, '_mcp_tool_metadata'):
            raise ValueError(f"Function {func.__name__} is not decorated with @tool")

        metadata = getattr(func, '_mcp_tool_metadata')

        mcp_tool = MCPTool(
            name=metadata["name"],
            function=func,
            description=metadata["description"],
            input_schema=metadata["input_schema"],
            is_async=metadata["is_async"],
            created_at=metadata["created_at"]
        )

        self.tools[metadata["name"]] = mcp_tool
        self.logger.info(f"Registered tool: {metadata['name']}")

        return mcp_tool

    def get_tool(self, name: str) -> Optional[MCPTool]:
        """Get a tool by name"""
        return self.tools.get(name)

    def list_tools(self) -> List[types.Tool]:
        """Get list of all tools in MCP format"""
        return [
            types.Tool(
                name=tool.name,
                description=tool.description,
                inputSchema=tool.input_schema
            )
            for tool in self.tools.values()
        ]

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call a registered tool

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Tool result
        """
        tool = self.get_tool(name)
        if not tool:
            raise ValueError(f"Tool '{name}' not found")

        with self.logger.span(f"tool_call_{name}", tool_name=name):
            try:
                # Update call statistics
                tool.call_count += 1
                tool.last_called = datetime.now()

                # Call the function
                if tool.is_async:
                    result = await tool.function(**arguments)
                else:
                    result = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: tool.function(**arguments)
                    )

                self.logger.info(f"Tool '{name}' executed successfully")
                return result

            except Exception as e:
                tool.error_count += 1
                tool.last_error = str(e)
                self.logger.error(f"Tool '{name}' failed", error=str(e))
                raise

    def get_tool_stats(self) -> Dict[str, Any]:
        """Get statistics about tool usage"""
        return {
            "total_tools": len(self.tools),
            "total_calls": sum(tool.call_count for tool in self.tools.values()),
            "total_errors": sum(tool.error_count for tool in self.tools.values()),
            "tools": [
                {
                    "name": tool.name,
                    "calls": tool.call_count,
                    "errors": tool.error_count,
                    "last_called": tool.last_called.isoformat() if tool.last_called else None,
                    "last_error": tool.last_error
                }
                for tool in self.tools.values()
            ]
        }

    def reset_stats(self):
        """Reset all tool statistics"""
        for tool in self.tools.values():
            tool.call_count = 0
            tool.error_count = 0
            tool.last_called = None
            tool.last_error = None

        self.logger.info("Tool statistics reset")


# Global tool registry instance
_global_registry = ToolRegistry()


def get_global_registry() -> ToolRegistry:
    """Get the global tool registry instance"""
    return _global_registry


def register_tool_function(func: Callable) -> MCPTool:
    """Register a function with the global tool registry"""
    return _global_registry.register_tool(func)


def get_all_tools() -> List[types.Tool]:
    """Get all tools from global registry"""
    return _global_registry.list_tools()


def call_global_tool(name: str, arguments: Dict[str, Any]) -> Any:
    """Call a tool from the global registry"""
    return _global_registry.call_tool(name, arguments)
