#!/usr/bin/env python3
"""
Pydantic AI MCP Server
AI agent creation and management using FastMCP framework.
"""

import asyncio
import json
import os
import uuid
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import sys
from pathlib import Path

# Add parent directory to path for FastMCP imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastmcp import FastMCP
import logfire

try:
    from pydantic import BaseModel, Field
    from pydantic_ai import Agent, RunContext
    PYDANTIC_AI_DEPS_AVAILABLE = True
except ImportError:
    PYDANTIC_AI_DEPS_AVAILABLE = False
    BaseModel = object
    def Field(*args, **kwargs):
        return None
    Agent = None
    RunContext = None


class AIAgent(BaseModel if PYDANTIC_AI_DEPS_AVAILABLE else object):
    """AI Agent model"""
    id: str = Field(..., description="Agent ID")
    name: str = Field(..., description="Agent name")
    description: Optional[str] = Field(None, description="Agent description")
    model: str = Field("gpt-4", description="AI model to use")
    system_prompt: Optional[str] = Field(None, description="System prompt")
    tools: List[str] = Field(default_factory=list, description="Available tools")
    created_at: str = Field(..., description="Creation timestamp")
    last_used: Optional[str] = Field(None, description="Last used timestamp")


class PydanticAIMCP:
    """
    Pydantic AI MCP Server using FastMCP framework

    Provides comprehensive AI agent management including:
    - Agent creation and configuration
    - Agent execution and conversation management
    - Tool integration for agents
    - Agent monitoring and analytics
    - Multi-model support
    - Agent templates and presets
    """

    def __init__(self):
        self.mcp = FastMCP("pydantic-ai-mcp", version="1.0.0",
                          description="AI agent creation and management with Pydantic AI")
        self.agents: Dict[str, AIAgent] = {}
        self.agent_instances: Dict[str, Any] = {}
        self.conversations: Dict[str, List[Dict[str, Any]]] = {}
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        self._setup_tools()

    def _generate_agent_id(self) -> str:
        """Generate unique agent ID"""
        return str(uuid.uuid4())[:8]

    def _get_agent_templates(self) -> Dict[str, Dict[str, Any]]:
        """Get predefined agent templates"""
        return {
            "assistant": {
                "name": "General Assistant",
                "description": "A helpful general-purpose assistant",
                "system_prompt": "You are a helpful, harmless, and honest assistant. Provide clear, accurate responses.",
                "model": "gpt-4"
            },
            "coder": {
                "name": "Code Assistant",
                "description": "A specialized coding assistant",
                "system_prompt": "You are an expert programmer. Help with code review, debugging, and development.",
                "model": "gpt-4"
            },
            "analyst": {
                "name": "Data Analyst",
                "description": "A data analysis specialist",
                "system_prompt": "You are a data analyst. Help analyze data, create insights, and generate reports.",
                "model": "gpt-4"
            },
            "writer": {
                "name": "Content Writer",
                "description": "A creative writing assistant",
                "system_prompt": "You are a skilled writer. Help create engaging, well-structured content.",
                "model": "gpt-4"
            }
        }

    def _setup_tools(self):
        """Setup Pydantic AI MCP tools"""

        @self.mcp.tool(
            name="create_agent",
            description="Create a new AI agent",
            input_schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Agent name"},
                    "description": {"type": "string", "description": "Agent description"},
                    "model": {"type": "string", "description": "AI model", "default": "gpt-4"},
                    "system_prompt": {"type": "string", "description": "System prompt"},
                    "template": {"type": "string", "description": "Agent template to use"}
                },
                "required": ["name"]
            }
        )
        async def create_agent(name: str, description: str = None, model: str = "gpt-4",
                             system_prompt: str = None, template: str = None) -> Dict[str, Any]:
            """Create a new AI agent"""
            try:
                if not PYDANTIC_AI_DEPS_AVAILABLE:
                    return {"error": "Pydantic AI dependencies not available"}

                agent_id = self._generate_agent_id()

                # Apply template if specified
                if template:
                    templates = self._get_agent_templates()
                    if template in templates:
                        template_data = templates[template]
                        name = template_data.get("name", name)
                        description = template_data.get("description", description)
                        model = template_data.get("model", model)
                        system_prompt = template_data.get("system_prompt", system_prompt)

                # Create agent record
                agent_data = {
                    "id": agent_id,
                    "name": name,
                    "description": description,
                    "model": model,
                    "system_prompt": system_prompt,
                    "tools": [],
                    "created_at": datetime.utcnow().isoformat(),
                    "last_used": None
                }

                if PYDANTIC_AI_DEPS_AVAILABLE:
                    agent = AIAgent(**agent_data)
                    self.agents[agent_id] = agent

                    # Create Pydantic AI agent instance
                    pydantic_agent = Agent(
                        model,
                        system_prompt=system_prompt or "You are a helpful assistant."
                    )
                    self.agent_instances[agent_id] = pydantic_agent
                else:
                    self.agents[agent_id] = agent_data

                return {
                    "status": "created",
                    "agent_id": agent_id,
                    "name": name,
                    "model": model,
                    "description": description
                }

            except Exception as e:
                logfire.error(f"Failed to create agent: {str(e)}")
                return {"error": f"Agent creation failed: {str(e)}"}

        @self.mcp.tool(
            name="list_agents",
            description="List all AI agents",
            input_schema={
                "type": "object",
                "properties": {}
            }
        )
        async def list_agents() -> Dict[str, Any]:
            """List all AI agents"""
            try:
                agents_list = []

                for agent_id, agent in self.agents.items():
                    if PYDANTIC_AI_DEPS_AVAILABLE and hasattr(agent, 'name'):
                        agent_data = {
                            "id": agent.id,
                            "name": agent.name,
                            "description": agent.description,
                            "model": agent.model,
                            "tools": agent.tools,
                            "created_at": agent.created_at,
                            "last_used": agent.last_used
                        }
                    else:
                        agent_data = {
                            "id": agent.get('id'),
                            "name": agent.get('name'),
                            "description": agent.get('description'),
                            "model": agent.get('model'),
                            "tools": agent.get('tools', []),
                            "created_at": agent.get('created_at'),
                            "last_used": agent.get('last_used')
                        }

                    agents_list.append(agent_data)

                return {
                    "total_agents": len(agents_list),
                    "agents": agents_list
                }

            except Exception as e:
                logfire.error(f"Failed to list agents: {str(e)}")
                return {"error": f"Agent listing failed: {str(e)}"}

        @self.mcp.tool(
            name="chat_with_agent",
            description="Have a conversation with an AI agent",
            input_schema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "Agent ID"},
                    "message": {"type": "string", "description": "Message to send"},
                    "conversation_id": {"type": "string", "description": "Conversation ID (optional)"}
                },
                "required": ["agent_id", "message"]
            }
        )
        async def chat_with_agent(agent_id: str, message: str, conversation_id: str = None) -> Dict[str, Any]:
            """Chat with an AI agent"""
            try:
                if agent_id not in self.agents:
                    return {"error": f"Agent '{agent_id}' not found"}

                if not PYDANTIC_AI_DEPS_AVAILABLE:
                    return {"error": "Pydantic AI dependencies not available"}

                # Get or create conversation
                if not conversation_id:
                    conversation_id = str(uuid.uuid4())[:8]

                if conversation_id not in self.conversations:
                    self.conversations[conversation_id] = []

                # Get agent instance
                if agent_id not in self.agent_instances:
                    return {"error": f"Agent instance '{agent_id}' not found"}

                pydantic_agent = self.agent_instances[agent_id]

                # Run the agent
                result = await pydantic_agent.run(message)

                # Store conversation
                self.conversations[conversation_id].append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "user": message,
                    "agent": str(result.data),
                    "agent_id": agent_id
                })

                # Update last used
                if PYDANTIC_AI_DEPS_AVAILABLE and hasattr(self.agents[agent_id], 'last_used'):
                    self.agents[agent_id].last_used = datetime.utcnow().isoformat()
                else:
                    self.agents[agent_id]['last_used'] = datetime.utcnow().isoformat()

                return {
                    "status": "success",
                    "agent_id": agent_id,
                    "conversation_id": conversation_id,
                    "user_message": message,
                    "agent_response": str(result.data),
                    "timestamp": datetime.utcnow().isoformat()
                }

            except Exception as e:
                logfire.error(f"Failed to chat with agent: {str(e)}")
                return {"error": f"Agent chat failed: {str(e)}"}

        @self.mcp.tool(
            name="get_conversation",
            description="Get conversation history",
            input_schema={
                "type": "object",
                "properties": {
                    "conversation_id": {"type": "string", "description": "Conversation ID"}
                },
                "required": ["conversation_id"]
            }
        )
        async def get_conversation(conversation_id: str) -> Dict[str, Any]:
            """Get conversation history"""
            try:
                if conversation_id not in self.conversations:
                    return {"error": f"Conversation '{conversation_id}' not found"}

                conversation = self.conversations[conversation_id]

                return {
                    "conversation_id": conversation_id,
                    "message_count": len(conversation),
                    "messages": conversation
                }

            except Exception as e:
                logfire.error(f"Failed to get conversation: {str(e)}")
                return {"error": f"Conversation retrieval failed: {str(e)}"}

        @self.mcp.tool(
            name="delete_agent",
            description="Delete an AI agent",
            input_schema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "Agent ID to delete"}
                },
                "required": ["agent_id"]
            }
        )
        async def delete_agent(agent_id: str) -> Dict[str, Any]:
            """Delete an AI agent"""
            try:
                if agent_id not in self.agents:
                    return {"error": f"Agent '{agent_id}' not found"}

                # Remove agent
                del self.agents[agent_id]

                # Remove agent instance
                if agent_id in self.agent_instances:
                    del self.agent_instances[agent_id]

                return {
                    "status": "deleted",
                    "agent_id": agent_id
                }

            except Exception as e:
                logfire.error(f"Failed to delete agent: {str(e)}")
                return {"error": f"Agent deletion failed: {str(e)}"}

        @self.mcp.tool(
            name="list_agent_templates",
            description="List available agent templates",
            input_schema={
                "type": "object",
                "properties": {}
            }
        )
        async def list_agent_templates() -> Dict[str, Any]:
            """List available agent templates"""
            try:
                templates = self._get_agent_templates()

                return {
                    "total_templates": len(templates),
                    "templates": templates
                }

            except Exception as e:
                logfire.error(f"Failed to list templates: {str(e)}")
                return {"error": f"Template listing failed: {str(e)}"}

        @self.mcp.tool(
            name="update_agent",
            description="Update an existing agent",
            input_schema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "Agent ID"},
                    "name": {"type": "string", "description": "New agent name"},
                    "description": {"type": "string", "description": "New description"},
                    "system_prompt": {"type": "string", "description": "New system prompt"}
                },
                "required": ["agent_id"]
            }
        )
        async def update_agent(agent_id: str, name: str = None, description: str = None,
                             system_prompt: str = None) -> Dict[str, Any]:
            """Update an existing agent"""
            try:
                if agent_id not in self.agents:
                    return {"error": f"Agent '{agent_id}' not found"}

                agent = self.agents[agent_id]

                # Update fields
                if name is not None:
                    if PYDANTIC_AI_DEPS_AVAILABLE and hasattr(agent, 'name'):
                        agent.name = name
                    else:
                        agent['name'] = name

                if description is not None:
                    if PYDANTIC_AI_DEPS_AVAILABLE and hasattr(agent, 'description'):
                        agent.description = description
                    else:
                        agent['description'] = description

                if system_prompt is not None:
                    if PYDANTIC_AI_DEPS_AVAILABLE and hasattr(agent, 'system_prompt'):
                        agent.system_prompt = system_prompt
                    else:
                        agent['system_prompt'] = system_prompt

                    # Update agent instance
                    if agent_id in self.agent_instances and PYDANTIC_AI_DEPS_AVAILABLE:
                        model = agent.model if hasattr(agent, 'model') else agent.get('model', 'gpt-4')
                        self.agent_instances[agent_id] = Agent(
                            model,
                            system_prompt=system_prompt
                        )

                return {
                    "status": "updated",
                    "agent_id": agent_id,
                    "updated_fields": {
                        "name": name,
                        "description": description,
                        "system_prompt": system_prompt
                    }
                }

            except Exception as e:
                logfire.error(f"Failed to update agent: {str(e)}")
                return {"error": f"Agent update failed: {str(e)}"}

        @self.mcp.tool(
            name="get_agent_stats",
            description="Get Pydantic AI system statistics",
            input_schema={
                "type": "object",
                "properties": {}
            }
        )
        async def get_agent_stats() -> Dict[str, Any]:
            """Get Pydantic AI system statistics"""
            try:
                total_agents = len(self.agents)
                total_conversations = len(self.conversations)
                total_messages = sum(len(conv) for conv in self.conversations.values())

                # Count agents by model
                model_counts = {}
                for agent in self.agents.values():
                    if PYDANTIC_AI_DEPS_AVAILABLE and hasattr(agent, 'model'):
                        model = agent.model
                    else:
                        model = agent.get('model', 'unknown')

                    model_counts[model] = model_counts.get(model, 0) + 1

                return {
                    "total_agents": total_agents,
                    "total_conversations": total_conversations,
                    "total_messages": total_messages,
                    "model_distribution": model_counts,
                    "dependencies_available": PYDANTIC_AI_DEPS_AVAILABLE,
                    "api_keys_configured": {
                        "openai": self.openai_api_key is not None,
                        "anthropic": self.anthropic_api_key is not None
                    }
                }

            except Exception as e:
                logfire.error(f"Failed to get agent stats: {str(e)}")
                return {"error": f"Agent stats query failed: {str(e)}"}

    async def run(self):
        """Run the Pydantic AI MCP server"""
        await self.mcp.run_stdio()


async def main():
    """Main entry point"""
    server = PydanticAIMCP()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
