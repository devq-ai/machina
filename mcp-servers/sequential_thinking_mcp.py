"""
Sequential Thinking MCP Server
Sequential reasoning capabilities for complex problem-solving workflows

Repository: https://github.com/loamstudios/zed-mcp-server-sequential-thinking
Instrumentation: mcp-python
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

import mcp.types as types
from mcp.server import Server
from mcp.server.models import InitializationOptions
import mcp.server.stdio


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ThoughtType(Enum):
    """Types of thoughts in sequential thinking"""
    ANALYSIS = "analysis"
    SYNTHESIS = "synthesis"
    EVALUATION = "evaluation"
    PLANNING = "planning"
    REFLECTION = "reflection"
    CONCLUSION = "conclusion"


@dataclass
class Thought:
    """A single thought in the sequential thinking process"""
    id: str
    content: str
    type: ThoughtType
    timestamp: datetime = field(default_factory=datetime.now)
    confidence: float = 0.5
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ThinkingChain:
    """A chain of sequential thoughts"""
    id: str
    title: str
    description: str
    thoughts: List[Thought] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    status: str = "active"
    metadata: Dict[str, Any] = field(default_factory=dict)


class SequentialThinkingMCPServer:
    """MCP Server for sequential thinking and complex problem-solving"""

    def __init__(self):
        self.server = Server("sequential-thinking-mcp")
        self.thinking_chains: Dict[str, ThinkingChain] = {}
        self.current_chain_id: Optional[str] = None
        self._setup_handlers()

    def _setup_handlers(self):
        """Set up MCP server handlers"""

        @self.server.list_tools()
        async def handle_list_tools() -> List[types.Tool]:
            """List available sequential thinking tools"""
            return [
                types.Tool(
                    name="create_thinking_chain",
                    description="Create a new sequential thinking chain for complex problem-solving",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "Title of the thinking chain"
                            },
                            "description": {
                                "type": "string",
                                "description": "Description of the problem or topic"
                            },
                            "initial_thought": {
                                "type": "string",
                                "description": "Initial thought or question",
                                "default": ""
                            }
                        },
                        "required": ["title", "description"]
                    }
                ),
                types.Tool(
                    name="add_thought",
                    description="Add a new thought to the current thinking chain",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "content": {
                                "type": "string",
                                "description": "Content of the thought"
                            },
                            "type": {
                                "type": "string",
                                "enum": ["analysis", "synthesis", "evaluation", "planning", "reflection", "conclusion"],
                                "description": "Type of thought",
                                "default": "analysis"
                            },
                            "confidence": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 1,
                                "description": "Confidence level (0-1)",
                                "default": 0.5
                            },
                            "dependencies": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "IDs of thoughts this depends on",
                                "default": []
                            },
                            "chain_id": {
                                "type": "string",
                                "description": "ID of the thinking chain (optional, uses current if not provided)"
                            }
                        },
                        "required": ["content"]
                    }
                ),
                types.Tool(
                    name="get_thinking_chain",
                    description="Get details of a specific thinking chain",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "chain_id": {
                                "type": "string",
                                "description": "ID of the thinking chain"
                            }
                        },
                        "required": ["chain_id"]
                    }
                ),
                types.Tool(
                    name="list_thinking_chains",
                    description="List all thinking chains",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "status": {
                                "type": "string",
                                "enum": ["active", "completed", "paused", "all"],
                                "description": "Filter by status",
                                "default": "all"
                            }
                        }
                    }
                ),
                types.Tool(
                    name="analyze_thinking_chain",
                    description="Analyze a thinking chain for patterns, gaps, and insights",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "chain_id": {
                                "type": "string",
                                "description": "ID of the thinking chain to analyze"
                            },
                            "analysis_type": {
                                "type": "string",
                                "enum": ["structure", "gaps", "patterns", "confidence", "full"],
                                "description": "Type of analysis to perform",
                                "default": "full"
                            }
                        },
                        "required": ["chain_id"]
                    }
                ),
                types.Tool(
                    name="continue_thinking",
                    description="Continue sequential thinking based on current chain state",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "chain_id": {
                                "type": "string",
                                "description": "ID of the thinking chain to continue"
                            },
                            "direction": {
                                "type": "string",
                                "enum": ["deeper", "broader", "alternative", "synthesis"],
                                "description": "Direction to continue thinking",
                                "default": "deeper"
                            },
                            "steps": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 10,
                                "description": "Number of thinking steps to generate",
                                "default": 3
                            }
                        },
                        "required": ["chain_id"]
                    }
                ),
                types.Tool(
                    name="set_current_chain",
                    description="Set the current active thinking chain",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "chain_id": {
                                "type": "string",
                                "description": "ID of the thinking chain to set as current"
                            }
                        },
                        "required": ["chain_id"]
                    }
                ),
                types.Tool(
                    name="export_thinking_chain",
                    description="Export a thinking chain in various formats",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "chain_id": {
                                "type": "string",
                                "description": "ID of the thinking chain to export"
                            },
                            "format": {
                                "type": "string",
                                "enum": ["json", "markdown", "outline", "flowchart"],
                                "description": "Export format",
                                "default": "markdown"
                            }
                        },
                        "required": ["chain_id"]
                    }
                ),
                types.Tool(
                    name="health_check",
                    description="Check the health and status of the sequential thinking server",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                )
            ]

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
            """Handle tool calls"""
            try:
                if name == "create_thinking_chain":
                    return await self._create_thinking_chain(arguments)
                elif name == "add_thought":
                    return await self._add_thought(arguments)
                elif name == "get_thinking_chain":
                    return await self._get_thinking_chain(arguments)
                elif name == "list_thinking_chains":
                    return await self._list_thinking_chains(arguments)
                elif name == "analyze_thinking_chain":
                    return await self._analyze_thinking_chain(arguments)
                elif name == "continue_thinking":
                    return await self._continue_thinking(arguments)
                elif name == "set_current_chain":
                    return await self._set_current_chain(arguments)
                elif name == "export_thinking_chain":
                    return await self._export_thinking_chain(arguments)
                elif name == "health_check":
                    return await self._health_check()
                else:
                    raise ValueError(f"Unknown tool: {name}")
            except Exception as e:
                logger.error(f"Error in tool {name}: {str(e)}")
                return [types.TextContent(
                    type="text",
                    text=f"Error: {str(e)}"
                )]

    async def _create_thinking_chain(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Create a new thinking chain"""
        title = arguments["title"]
        description = arguments["description"]
        initial_thought = arguments.get("initial_thought", "")

        # Generate unique ID
        chain_id = f"chain_{len(self.thinking_chains) + 1}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Create chain
        chain = ThinkingChain(
            id=chain_id,
            title=title,
            description=description
        )

        # Add initial thought if provided
        if initial_thought:
            thought = Thought(
                id=f"thought_1",
                content=initial_thought,
                type=ThoughtType.ANALYSIS
            )
            chain.thoughts.append(thought)

        self.thinking_chains[chain_id] = chain
        self.current_chain_id = chain_id

        logger.info(f"Created thinking chain: {chain_id}")

        return [types.TextContent(
            type="text",
            text=f"Created thinking chain '{title}' with ID: {chain_id}\n"
                 f"Description: {description}\n"
                 f"Initial thoughts: {len(chain.thoughts)}\n"
                 f"Set as current active chain."
        )]

    async def _add_thought(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Add a thought to a thinking chain"""
        content = arguments["content"]
        thought_type = ThoughtType(arguments.get("type", "analysis"))
        confidence = arguments.get("confidence", 0.5)
        dependencies = arguments.get("dependencies", [])
        chain_id = arguments.get("chain_id", self.current_chain_id)

        if not chain_id or chain_id not in self.thinking_chains:
            raise ValueError("Invalid or missing chain ID")

        chain = self.thinking_chains[chain_id]

        # Generate thought ID
        thought_id = f"thought_{len(chain.thoughts) + 1}"

        thought = Thought(
            id=thought_id,
            content=content,
            type=thought_type,
            confidence=confidence,
            dependencies=dependencies
        )

        chain.thoughts.append(thought)
        chain.updated_at = datetime.now()

        logger.info(f"Added thought to chain {chain_id}: {thought_id}")

        return [types.TextContent(
            type="text",
            text=f"Added thought '{thought_id}' to chain '{chain.title}'\n"
                 f"Type: {thought_type.value}\n"
                 f"Confidence: {confidence}\n"
                 f"Dependencies: {dependencies}\n"
                 f"Total thoughts in chain: {len(chain.thoughts)}"
        )]

    async def _get_thinking_chain(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Get details of a thinking chain"""
        chain_id = arguments["chain_id"]

        if chain_id not in self.thinking_chains:
            raise ValueError(f"Chain not found: {chain_id}")

        chain = self.thinking_chains[chain_id]

        # Format chain details
        details = f"Thinking Chain: {chain.title}\n"
        details += f"ID: {chain.id}\n"
        details += f"Description: {chain.description}\n"
        details += f"Status: {chain.status}\n"
        details += f"Created: {chain.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
        details += f"Updated: {chain.updated_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
        details += f"Total thoughts: {len(chain.thoughts)}\n\n"

        # Add thoughts
        details += "Thoughts:\n"
        for i, thought in enumerate(chain.thoughts, 1):
            details += f"{i}. [{thought.type.value}] {thought.content}\n"
            if thought.dependencies:
                details += f"   Dependencies: {', '.join(thought.dependencies)}\n"
            details += f"   Confidence: {thought.confidence:.2f}\n"
            details += f"   Time: {thought.timestamp.strftime('%H:%M:%S')}\n\n"

        return [types.TextContent(
            type="text",
            text=details
        )]

    async def _list_thinking_chains(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """List all thinking chains"""
        status_filter = arguments.get("status", "all")

        chains = []
        for chain in self.thinking_chains.values():
            if status_filter == "all" or chain.status == status_filter:
                chains.append(chain)

        if not chains:
            return [types.TextContent(
                type="text",
                text="No thinking chains found matching the criteria."
            )]

        # Format chain list
        details = f"Thinking Chains ({len(chains)} found):\n\n"
        for chain in chains:
            current_marker = " [CURRENT]" if chain.id == self.current_chain_id else ""
            details += f"• {chain.title}{current_marker}\n"
            details += f"  ID: {chain.id}\n"
            details += f"  Status: {chain.status}\n"
            details += f"  Thoughts: {len(chain.thoughts)}\n"
            details += f"  Updated: {chain.updated_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        return [types.TextContent(
            type="text",
            text=details
        )]

    async def _analyze_thinking_chain(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Analyze a thinking chain for patterns and insights"""
        chain_id = arguments["chain_id"]
        analysis_type = arguments.get("analysis_type", "full")

        if chain_id not in self.thinking_chains:
            raise ValueError(f"Chain not found: {chain_id}")

        chain = self.thinking_chains[chain_id]

        analysis = f"Analysis of Thinking Chain: {chain.title}\n"
        analysis += f"Analysis Type: {analysis_type}\n\n"

        if analysis_type in ["structure", "full"]:
            # Analyze structure
            analysis += "STRUCTURE ANALYSIS:\n"
            thought_types = {}
            for thought in chain.thoughts:
                thought_types[thought.type.value] = thought_types.get(thought.type.value, 0) + 1

            analysis += f"• Total thoughts: {len(chain.thoughts)}\n"
            analysis += f"• Thought types: {dict(thought_types)}\n"

            # Dependency analysis
            dependencies = sum(len(t.dependencies) for t in chain.thoughts)
            analysis += f"• Dependencies: {dependencies}\n\n"

        if analysis_type in ["confidence", "full"]:
            # Analyze confidence
            analysis += "CONFIDENCE ANALYSIS:\n"
            if chain.thoughts:
                confidences = [t.confidence for t in chain.thoughts]
                avg_confidence = sum(confidences) / len(confidences)
                analysis += f"• Average confidence: {avg_confidence:.2f}\n"
                analysis += f"• Confidence range: {min(confidences):.2f} - {max(confidences):.2f}\n\n"

        if analysis_type in ["gaps", "full"]:
            # Analyze gaps
            analysis += "GAP ANALYSIS:\n"
            has_conclusion = any(t.type == ThoughtType.CONCLUSION for t in chain.thoughts)
            has_evaluation = any(t.type == ThoughtType.EVALUATION for t in chain.thoughts)

            if not has_conclusion:
                analysis += "• Missing conclusion thoughts\n"
            if not has_evaluation:
                analysis += "• Missing evaluation thoughts\n"

            if has_conclusion and has_evaluation:
                analysis += "• No significant gaps detected\n"
            analysis += "\n"

        if analysis_type in ["patterns", "full"]:
            # Analyze patterns
            analysis += "PATTERN ANALYSIS:\n"
            if len(chain.thoughts) > 1:
                # Check for alternating patterns
                types_sequence = [t.type.value for t in chain.thoughts]
                analysis += f"• Thinking sequence: {' → '.join(types_sequence)}\n"

                # Check for repetitive patterns
                if len(set(types_sequence)) < len(types_sequence) / 2:
                    analysis += "• Pattern detected: Repetitive thinking\n"
                else:
                    analysis += "• Pattern detected: Diverse thinking\n"
            else:
                analysis += "• Insufficient data for pattern analysis\n"
            analysis += "\n"

        return [types.TextContent(
            type="text",
            text=analysis
        )]

    async def _continue_thinking(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Continue sequential thinking based on current chain state"""
        chain_id = arguments["chain_id"]
        direction = arguments.get("direction", "deeper")
        steps = arguments.get("steps", 3)

        if chain_id not in self.thinking_chains:
            raise ValueError(f"Chain not found: {chain_id}")

        chain = self.thinking_chains[chain_id]

        if not chain.thoughts:
            return [types.TextContent(
                type="text",
                text="Cannot continue thinking: chain has no thoughts to build upon."
            )]

        # Generate continuation suggestions based on direction
        suggestions = []
        last_thought = chain.thoughts[-1]

        if direction == "deeper":
            suggestions = [
                f"What are the underlying assumptions in: {last_thought.content[:50]}...?",
                f"What are the implications of: {last_thought.content[:50]}...?",
                f"What evidence supports or contradicts: {last_thought.content[:50]}...?"
            ]
        elif direction == "broader":
            suggestions = [
                f"What are alternative perspectives on: {last_thought.content[:50]}...?",
                f"How does this relate to broader contexts: {last_thought.content[:50]}...?",
                f"What are the parallel considerations: {last_thought.content[:50]}...?"
            ]
        elif direction == "alternative":
            suggestions = [
                f"What if the opposite were true: {last_thought.content[:50]}...?",
                f"What alternative approaches exist for: {last_thought.content[:50]}...?",
                f"What are the counter-arguments to: {last_thought.content[:50]}...?"
            ]
        elif direction == "synthesis":
            suggestions = [
                f"How do all previous thoughts connect?",
                f"What patterns emerge from the thinking so far?",
                f"What conclusions can be drawn from the chain of thought?"
            ]

        # Limit to requested number of steps
        suggestions = suggestions[:steps]

        response = f"Continuation suggestions for chain '{chain.title}' (direction: {direction}):\n\n"
        for i, suggestion in enumerate(suggestions, 1):
            response += f"{i}. {suggestion}\n"

        response += f"\nTo add any of these thoughts, use the 'add_thought' tool with the chain_id: {chain_id}"

        return [types.TextContent(
            type="text",
            text=response
        )]

    async def _set_current_chain(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Set the current active thinking chain"""
        chain_id = arguments["chain_id"]

        if chain_id not in self.thinking_chains:
            raise ValueError(f"Chain not found: {chain_id}")

        self.current_chain_id = chain_id
        chain = self.thinking_chains[chain_id]

        return [types.TextContent(
            type="text",
            text=f"Set current active chain to: {chain.title} ({chain_id})"
        )]

    async def _export_thinking_chain(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Export a thinking chain in various formats"""
        chain_id = arguments["chain_id"]
        format_type = arguments.get("format", "markdown")

        if chain_id not in self.thinking_chains:
            raise ValueError(f"Chain not found: {chain_id}")

        chain = self.thinking_chains[chain_id]

        if format_type == "json":
            export_data = {
                "id": chain.id,
                "title": chain.title,
                "description": chain.description,
                "status": chain.status,
                "created_at": chain.created_at.isoformat(),
                "updated_at": chain.updated_at.isoformat(),
                "thoughts": [
                    {
                        "id": t.id,
                        "content": t.content,
                        "type": t.type.value,
                        "confidence": t.confidence,
                        "dependencies": t.dependencies,
                        "timestamp": t.timestamp.isoformat()
                    }
                    for t in chain.thoughts
                ]
            }
            export_text = json.dumps(export_data, indent=2)

        elif format_type == "markdown":
            export_text = f"# {chain.title}\n\n"
            export_text += f"**Description:** {chain.description}\n\n"
            export_text += f"**Status:** {chain.status}\n"
            export_text += f"**Created:** {chain.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
            export_text += f"**Updated:** {chain.updated_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            export_text += "## Thoughts\n\n"

            for i, thought in enumerate(chain.thoughts, 1):
                export_text += f"### {i}. {thought.type.value.title()}\n\n"
                export_text += f"{thought.content}\n\n"
                if thought.dependencies:
                    export_text += f"*Dependencies: {', '.join(thought.dependencies)}*\n\n"
                export_text += f"*Confidence: {thought.confidence:.2f} | Time: {thought.timestamp.strftime('%H:%M:%S')}*\n\n"

        elif format_type == "outline":
            export_text = f"{chain.title}\n"
            export_text += f"{'=' * len(chain.title)}\n\n"

            for i, thought in enumerate(chain.thoughts, 1):
                export_text += f"{i}. [{thought.type.value}] {thought.content}\n"
                if thought.dependencies:
                    export_text += f"   └─ Depends on: {', '.join(thought.dependencies)}\n"

        elif format_type == "flowchart":
            export_text = f"Thinking Chain Flowchart: {chain.title}\n"
            export_text += f"{'=' * (len(chain.title) + 25)}\n\n"

            for i, thought in enumerate(chain.thoughts, 1):
                if i == 1:
                    export_text += f"START\n  ↓\n"

                export_text += f"[{thought.type.value}]\n"
                export_text += f"{thought.content[:50]}...\n"

                if thought.dependencies:
                    export_text += f"(depends on: {', '.join(thought.dependencies)})\n"

                if i < len(chain.thoughts):
                    export_text += "  ↓\n"
                else:
                    export_text += "  ↓\n[END]\n"

        return [types.TextContent(
            type="text",
            text=export_text
        )]

    async def _health_check(self) -> List[types.TextContent]:
        """Health check for the sequential thinking server"""
        status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "chains_count": len(self.thinking_chains),
            "current_chain": self.current_chain_id,
            "total_thoughts": sum(len(chain.thoughts) for chain in self.thinking_chains.values())
        }

        return [types.TextContent(
            type="text",
            text=f"Sequential Thinking MCP Server Health Check\n"
                 f"Status: {status['status']}\n"
                 f"Timestamp: {status['timestamp']}\n"
                 f"Active chains: {status['chains_count']}\n"
                 f"Current chain: {status['current_chain'] or 'None'}\n"
                 f"Total thoughts: {status['total_thoughts']}"
        )]

    async def run(self):
        """Run the MCP server"""
        logger.info("Starting Sequential Thinking MCP Server")

        # Initialize server options
        options = InitializationOptions(
            server_name="sequential-thinking-mcp",
            server_version="1.0.0",
            capabilities={
                "tools": {},
                "resources": {},
                "prompts": {}
            }
        )

        # Run server with stdio transport
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                options
            )


async def main():
    """Main entry point"""
    server = SequentialThinkingMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
