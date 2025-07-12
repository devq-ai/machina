#!/usr/bin/env python
"""
Pydantic AI MCP Server
FastMCP server for Pydantic AI agent development tools.
Provides agent creation, testing, and management capabilities.
"""
import asyncio
import os
import json
import tempfile
from typing import Any, Dict, List, Optional
from datetime import datetime
from pathlib import Path

import logfire
from fastmcp import FastMCP
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logfire
# logfire.configure(
#     token=os.getenv('LOGFIRE_WRITE_TOKEN'),
#     service_name='pydantic-ai-mcp-server',
#     environment='production'
# )

# Create FastMCP app instance
app = FastMCP("pydantic-ai-mcp")

class PydanticAIHelper:
    """Pydantic AI development and agent management helper."""
    
    def __init__(self):
        self.project_root = os.getenv('PROJECT_ROOT', '/Users/dionedge/devqai/machina')
        self.python_path = os.getenv('PYTHON_PATH', 'python3')
        self.default_model = os.getenv('PYDANTIC_AI_MODEL', 'claude-3-7-sonnet-20250219')
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
    
    async def run_command(self, cmd: List[str], cwd: Optional[str] = None) -> Dict[str, Any]:
        """Run command and return structured output."""
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd or self.project_root
            )
            
            stdout, stderr = await process.communicate()
            
            return {
                "command": " ".join(cmd),
                "exit_code": process.returncode,
                "stdout": stdout.decode('utf-8') if stdout else "",
                "stderr": stderr.decode('utf-8') if stderr else "",
                "success": process.returncode == 0
            }
            
        except Exception as e:
            return {
                "command": " ".join(cmd),
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e),
                "success": False,
                "error": str(e)
            }

pydantic_ai_helper = PydanticAIHelper()

@app.tool()
@logfire.instrument("pydantic_ai_health_check")
async def pydantic_ai_health_check() -> Dict[str, Any]:
    """Check Pydantic AI environment health and configuration."""
    # logfire.info("Pydantic AI health check requested")
    
    try:
        # Check Python and Pydantic AI availability
        python_check = await pydantic_ai_helper.run_command([pydantic_ai_helper.python_path, '--version'])
        pydantic_ai_check = await pydantic_ai_helper.run_command([
            pydantic_ai_helper.python_path, '-c', 'import pydantic_ai; print(pydantic_ai.__version__)'
        ])
        logfire_check = await pydantic_ai_helper.run_command([
            pydantic_ai_helper.python_path, '-c', 'import logfire; print(logfire.__version__)'
        ])
        
        health_status = {
            "status": "healthy" if all([python_check["success"], pydantic_ai_check["success"]]) else "unhealthy",
            "python_version": python_check["stdout"].strip() if python_check["success"] else "not available",
            "pydantic_ai_version": pydantic_ai_check["stdout"].strip() if pydantic_ai_check["success"] else "not installed",
            "logfire_version": logfire_check["stdout"].strip() if logfire_check["success"] else "not installed",
            "default_model": pydantic_ai_helper.default_model,
            "api_keys_configured": {
                "anthropic": bool(pydantic_ai_helper.anthropic_api_key),
                "openai": bool(pydantic_ai_helper.openai_api_key)
            },
            "project_root": pydantic_ai_helper.project_root,
            "timestamp": datetime.now().isoformat()
        }
        
        # logfire.info("Pydantic AI health check completed", health_status=health_status)
        return health_status
        
    except Exception as e:
        # logfire.error("Pydantic AI health check failed", error=str(e))
        pass
        raise

@app.tool()
@logfire.instrument("create_pydantic_agent")
async def create_pydantic_agent(
    agent_name: str,
    system_prompt: str,
    model: Optional[str] = None,
    include_logfire: bool = True,
    tools: Optional[List[str]] = None
) -> str:
    """Create a Pydantic AI agent with specified configuration."""
    # logfire.info("Creating Pydantic AI agent", 
    #             agent_name=agent_name,
    #             model=model or pydantic_ai_helper.default_model,
    #             include_logfire=include_logfire)
    
    try:
        agent_model = model or pydantic_ai_helper.default_model
        
        imports = [
            "import asyncio",
            "import os",
            "from typing import Any, Dict, List, Optional",
            "from datetime import datetime",
            "",
            "from pydantic_ai import Agent, RunContext",
            "from pydantic import BaseModel",
            "from dotenv import load_dotenv"
        ]
        
        if include_logfire:
            imports.insert(-1, "import logfire")
        
        agent_code = f'''#!/usr/bin/env python
"""
{agent_name} Pydantic AI Agent
Generated by Pydantic AI MCP Server
"""
{chr(10).join(imports)}

# Load environment variables
load_dotenv()
'''

        if include_logfire:
            agent_code += f'''
# Configure logfire
# logfire.configure(
#     token=os.getenv('LOGFIRE_WRITE_TOKEN'),
#     service_name='{agent_name.lower().replace('_', '-')}-agent',
#     environment='production'
# )
'''

        # Add data models
        agent_code += f'''
# Data models
class {agent_name.replace('_', '').title()}Request(BaseModel):
    """Request model for {agent_name} agent."""
    query: str
    context: Optional[str] = None
    max_tokens: Optional[int] = 1000

class {agent_name.replace('_', '').title()}Response(BaseModel):
    """Response model for {agent_name} agent."""
    result: str
    confidence: float
    timestamp: str
    model_used: str
'''

        # Create agent with logfire instrumentation
        if include_logfire:
            agent_code += f'''
# Create agent with logfire instrumentation
@logfire.instrument("create_{agent_name}_agent")
def create_agent() -> Agent:
    """Create and configure the {agent_name} agent."""
    
    agent = Agent(
        '{agent_model}',
        system_prompt="""{system_prompt}""",
    )
    
    # logfire.info("Agent created", agent_name="{agent_name}", model="{agent_model}")
    return agent

# Initialize agent
{agent_name}_agent = create_agent()
'''
        else:
            agent_code += f'''
# Create agent
{agent_name}_agent = Agent(
    '{agent_model}',
    system_prompt="""{system_prompt}""",
)
'''

        # Add tools if specified
        if tools:
            for tool_name in tools:
                if include_logfire:
                    agent_code += f'''
@{agent_name}_agent.tool
@logfire.instrument("{tool_name}")
async def {tool_name}(ctx: RunContext, query: str) -> str:
    """Tool: {tool_name}."""
    # logfire.info("{tool_name} called", query=query)
    
    try:
        # TODO: Implement {tool_name} logic here
        result = f"{tool_name} processed: {{query}}"
        
        # logfire.info("{tool_name} completed", query=query, result_length=len(result))
        return result
        
    except Exception as e:
        # logfire.error("{tool_name} failed", query=query, error=str(e))
        pass
        raise
'''
                else:
                    agent_code += f'''
@{agent_name}_agent.tool
async def {tool_name}(ctx: RunContext, query: str) -> str:
    """Tool: {tool_name}."""
    # TODO: Implement {tool_name} logic here
    return f"{tool_name} processed: {{query}}"
'''

        # Add main execution functions
        if include_logfire:
            agent_code += f'''
@logfire.instrument("run_{agent_name}_agent")
async def run_agent(request: {agent_name.replace('_', '').title()}Request) -> {agent_name.replace('_', '').title()}Response:
    """Run the {agent_name} agent with a request."""
    # logfire.info("Running agent", agent_name="{agent_name}", query=request.query)
    
    try:
        # Run the agent
        result = await {agent_name}_agent.run(request.query)
        
        response = {agent_name.replace('_', '').title()}Response(
            result=str(result.data),
            confidence=0.95,  # TODO: Implement confidence calculation
            timestamp=datetime.now().isoformat(),
            model_used="{agent_model}"
        )
        
        # logfire.info("Agent completed", 
        #             agent_name="{agent_name}",
        #             query=request.query,
        #             result_length=len(response.result))
        
        return response
        
    except Exception as e:
        # logfire.error("Agent failed", 
        pass
        #              agent_name="{agent_name}",
        #              query=request.query,
        #              error=str(e))
        raise

async def main():
    """Main execution function for testing."""
    # Test the agent
    test_request = {agent_name.replace('_', '').title()}Request(
        query="Hello, this is a test query",
        context="Testing context",
        max_tokens=500
    )
    
    response = await run_agent(test_request)
    print(f"Agent Response: {{response.result}}")

if __name__ == "__main__":
    # logfire.info("Starting {agent_name} agent")
    pass
    asyncio.run(main())
'''
        else:
            agent_code += f'''
async def run_agent(request: {agent_name.replace('_', '').title()}Request) -> {agent_name.replace('_', '').title()}Response:
    """Run the {agent_name} agent with a request."""
    # Run the agent
    result = await {agent_name}_agent.run(request.query)
    
    response = {agent_name.replace('_', '').title()}Response(
        result=str(result.data),
        confidence=0.95,  # TODO: Implement confidence calculation
        timestamp=datetime.now().isoformat(),
        model_used="{agent_model}"
    )
    
    return response

async def main():
    """Main execution function for testing."""
    # Test the agent
    test_request = {agent_name.replace('_', '').title()}Request(
        query="Hello, this is a test query",
        context="Testing context",
        max_tokens=500
    )
    
    response = await run_agent(test_request)
    print(f"Agent Response: {{response.result}}")

if __name__ == "__main__":
    asyncio.run(main())
'''
        
        # logfire.info("Pydantic AI agent created", 
        #             agent_name=agent_name,
        #             code_length=len(agent_code),
        #             model=agent_model)
        
        return agent_code
        
    except Exception as e:
        # logfire.error("Failed to create Pydantic AI agent", 
        pass
        #              agent_name=agent_name,
        #              error=str(e))
        raise

@app.tool()
@logfire.instrument("test_pydantic_agent")
async def test_pydantic_agent(agent_file: str, test_query: str = "Hello World") -> Dict[str, Any]:
    """Test a Pydantic AI agent by running it with a test query."""
    # logfire.info("Testing Pydantic AI agent", agent_file=agent_file, test_query=test_query)
    
    try:
        # Create a temporary test script
        test_script = f'''
import sys
import asyncio
sys.path.insert(0, "{pydantic_ai_helper.project_root}/src")

async def test_agent():
    try:
        from {agent_file.replace('.py', '')} import run_agent
        from {agent_file.replace('.py', '')} import {agent_file.replace('.py', '').replace('_', '').title()}Request
        
        # Create test request
        request = {agent_file.replace('.py', '').replace('_', '').title()}Request(
            query="{test_query}",
            context="Test context",
            max_tokens=100
        )
        
        # Run agent
        response = await run_agent(request)
        
        result = {{
            "status": "success",
            "response": response.dict() if hasattr(response, 'dict') else str(response),
            "agent_file": "{agent_file}",
            "test_query": "{test_query}"
        }}
        
        import json
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        error_result = {{
            "status": "error",
            "error": str(e),
            "agent_file": "{agent_file}",
            "test_query": "{test_query}"
        }}
        import json
        print(json.dumps(error_result, indent=2))

if __name__ == "__main__":
    asyncio.run(test_agent())
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_script)
            temp_script_path = f.name
        
        try:
            result = await pydantic_ai_helper.run_command([
                pydantic_ai_helper.python_path, temp_script_path
            ])
            
            if result["success"] and result["stdout"]:
                test_result = json.loads(result["stdout"])
                test_result["timestamp"] = datetime.now().isoformat()
                
                # logfire.info("Pydantic AI agent test completed", 
                #             agent_file=agent_file,
                #             status=test_result["status"],
                #             test_query=test_query)
                
                return test_result
            else:
                raise RuntimeError(f"Failed to test agent: {result['stderr']}")
                
        finally:
            os.unlink(temp_script_path)
            
    except Exception as e:
        # logfire.error("Failed to test Pydantic AI agent", 
        pass
        #              agent_file=agent_file,
        #              error=str(e))
        raise

@app.tool()
@logfire.instrument("list_agent_models")
async def list_agent_models() -> Dict[str, List[str]]:
    """List available models for Pydantic AI agents."""
    # logfire.info("Listing available agent models")
    
    try:
        available_models = {
            "anthropic": [
                "claude-3-7-sonnet-20250219",
                "claude-3-5-sonnet-20241022",
                "claude-3-5-haiku-20241022",
                "claude-3-opus-20240229"
            ],
            "openai": [
                "gpt-4o",
                "gpt-4o-mini",
                "gpt-4-turbo",
                "gpt-3.5-turbo"
            ],
            "gemini": [
                "gemini-1.5-pro",
                "gemini-1.5-flash",
                "gemini-pro"
            ]
        }
        
        # Filter based on available API keys
        accessible_models = {}
        
        if pydantic_ai_helper.anthropic_api_key:
            accessible_models["anthropic"] = available_models["anthropic"]
        
        if pydantic_ai_helper.openai_api_key:
            accessible_models["openai"] = available_models["openai"]
        
        # Always include Gemini (using GEMINI_API_KEY if available)
        accessible_models["gemini"] = available_models["gemini"]
        
        models_info = {
            "available_models": accessible_models,
            "default_model": pydantic_ai_helper.default_model,
            "api_keys_configured": {
                "anthropic": bool(pydantic_ai_helper.anthropic_api_key),
                "openai": bool(pydantic_ai_helper.openai_api_key),
                "gemini": bool(os.getenv('GEMINI_API_KEY'))
            },
            "total_models": sum(len(models) for models in accessible_models.values()),
            "timestamp": datetime.now().isoformat()
        }
        
        # logfire.info("Agent models listed", 
        #             total_models=models_info["total_models"],
        #             providers=list(accessible_models.keys()))
        
        return models_info
        
    except Exception as e:
        # logfire.error("Failed to list agent models", error=str(e))
        pass
        raise

@app.tool()
@logfire.instrument("create_agent_workflow")
async def create_agent_workflow(
    workflow_name: str,
    agents: List[Dict[str, str]],
    coordination_strategy: str = "sequential"
) -> str:
    """Create a multi-agent workflow with specified coordination strategy."""
    # logfire.info("Creating agent workflow", 
    #             workflow_name=workflow_name,
    #             agent_count=len(agents),
    #             coordination_strategy=coordination_strategy)
    
    try:
        imports = [
            "import asyncio",
            "import os",
            "from typing import Any, Dict, List, Optional",
            "from datetime import datetime",
            "",
            "from pydantic_ai import Agent",
            "from pydantic import BaseModel",
            "import logfire",
            "from dotenv import load_dotenv"
        ]
        
        workflow_code = f'''#!/usr/bin/env python
"""
{workflow_name} Multi-Agent Workflow
Generated by Pydantic AI MCP Server
Coordination Strategy: {coordination_strategy}
"""
{chr(10).join(imports)}

# Load environment variables
load_dotenv()

# Configure logfire
# logfire.configure(
#     token=os.getenv('LOGFIRE_WRITE_TOKEN'),
#     service_name='{workflow_name.lower().replace('_', '-')}-workflow',
#     environment='production'
# )

# Workflow data models
class WorkflowRequest(BaseModel):
    """Request model for the workflow."""
    input_data: str
    context: Optional[str] = None
    max_iterations: int = 5

class WorkflowResponse(BaseModel):
    """Response model for the workflow."""
    final_result: str
    agent_results: List[Dict[str, Any]]
    execution_time: float
    timestamp: str

class {workflow_name.replace('_', '').title()}Workflow:
    """Multi-agent workflow coordinator."""
    
    def __init__(self):
        self.agents = self._initialize_agents()
        # logfire.info("Workflow initialized", 
        #             workflow_name="{workflow_name}",
        #             agent_count=len(self.agents))
    
    def _initialize_agents(self) -> Dict[str, Agent]:
        """Initialize all agents in the workflow."""
        agents = {{}}
        
'''

        # Initialize agents
        for agent_config in agents:
            agent_name = agent_config.get("name", "unnamed_agent")
            agent_prompt = agent_config.get("prompt", "You are a helpful AI agent.")
            agent_model = agent_config.get("model", pydantic_ai_helper.default_model)
            
            workflow_code += f'''        # Initialize {agent_name} agent
        agents["{agent_name}"] = Agent(
            '{agent_model}',
            system_prompt="""{agent_prompt}"""
        )
        
'''

        workflow_code += f'''        return agents
    
    @logfire.instrument("execute_workflow")
    async def execute(self, request: WorkflowRequest) -> WorkflowResponse:
        """Execute the multi-agent workflow."""
        start_time = datetime.now()
        # logfire.info("Workflow execution started", 
        #             workflow_name="{workflow_name}",
        #             input_data=request.input_data[:100])
        
        agent_results = []
        current_data = request.input_data
        
        try:
'''

        if coordination_strategy == "sequential":
            workflow_code += f'''            # Sequential execution strategy
            for agent_name, agent in self.agents.items():
                # logfire.info("Executing agent", agent_name=agent_name)
                
                try:
                    result = await agent.run(current_data)
                    agent_result = {{
                        "agent_name": agent_name,
                        "input": current_data,
                        "output": str(result.data),
                        "success": True,
                        "timestamp": datetime.now().isoformat()
                    }}
                    
                    # Use output as input for next agent
                    current_data = str(result.data)
                    
                except Exception as e:
                    agent_result = {{
                        "agent_name": agent_name,
                        "input": current_data,
                        "output": f"Error: {{str(e)}}",
                        "success": False,
                        "timestamp": datetime.now().isoformat()
                    }}
                    
                    # logfire.error("Agent execution failed", 
                    #              agent_name=agent_name,
                    #              error=str(e))
                
                agent_results.append(agent_result)
            
            final_result = current_data
'''
        elif coordination_strategy == "parallel":
            workflow_code += f'''            # Parallel execution strategy
            tasks = []
            for agent_name, agent in self.agents.items():
                task = self._execute_agent_parallel(agent_name, agent, current_data)
                tasks.append(task)
            
            # Wait for all agents to complete
            parallel_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, (agent_name, result) in enumerate(zip(self.agents.keys(), parallel_results)):
                if isinstance(result, Exception):
                    agent_result = {{
                        "agent_name": agent_name,
                        "input": current_data,
                        "output": f"Error: {{str(result)}}",
                        "success": False,
                        "timestamp": datetime.now().isoformat()
                    }}
                else:
                    agent_result = {{
                        "agent_name": agent_name,
                        "input": current_data,
                        "output": result,
                        "success": True,
                        "timestamp": datetime.now().isoformat()
                    }}
                
                agent_results.append(agent_result)
            
            # Combine results
            successful_results = [r["output"] for r in agent_results if r["success"]]
            final_result = " | ".join(successful_results) if successful_results else "No successful results"
'''
        else:
            workflow_code += f'''            # Custom coordination strategy: {coordination_strategy}
            # TODO: Implement custom coordination logic
            final_result = "Custom coordination not implemented"
'''

        workflow_code += f'''            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            response = WorkflowResponse(
                final_result=final_result,
                agent_results=agent_results,
                execution_time=execution_time,
                timestamp=datetime.now().isoformat()
            )
            
            # logfire.info("Workflow execution completed", 
            #             workflow_name="{workflow_name}",
            #             execution_time=execution_time,
            #             agent_count=len(agent_results))
            
            return response
            
        except Exception as e:
            # logfire.error("Workflow execution failed", 
            pass
            #              workflow_name="{workflow_name}",
            #              error=str(e))
            raise
'''

        if coordination_strategy == "parallel":
            workflow_code += f'''    
    async def _execute_agent_parallel(self, agent_name: str, agent: Agent, input_data: str) -> str:
        """Execute an agent in parallel."""
        try:
            result = await agent.run(input_data)
            return str(result.data)
        except Exception as e:
            # logfire.error("Parallel agent execution failed", 
            pass
            #              agent_name=agent_name,
            #              error=str(e))
            raise
'''

        workflow_code += f'''
# Initialize workflow
{workflow_name}_workflow = {workflow_name.replace('_', '').title()}Workflow()

async def main():
    """Main execution function for testing."""
    # Test the workflow
    test_request = WorkflowRequest(
        input_data="Test input for multi-agent workflow",
        context="Testing context",
        max_iterations=3
    )
    
    response = await {workflow_name}_workflow.execute(test_request)
    print(f"Workflow Response: {{response.final_result}}")
    print(f"Execution Time: {{response.execution_time:.2f}}s")

if __name__ == "__main__":
    # logfire.info("Starting {workflow_name} workflow")
    pass
    asyncio.run(main())
'''
        
        # logfire.info("Agent workflow created", 
        #             workflow_name=workflow_name,
        #             code_length=len(workflow_code),
        #             agent_count=len(agents))
        
        return workflow_code
        
    except Exception as e:
        # logfire.error("Failed to create agent workflow", 
        pass
        #              workflow_name=workflow_name,
        #              error=str(e))
        raise

@app.tool()
@logfire.instrument("validate_pydantic_agent")
async def validate_pydantic_agent(agent_file: str) -> Dict[str, Any]:
    """Validate a Pydantic AI agent for common issues and best practices."""
    # logfire.info("Validating Pydantic AI agent", agent_file=agent_file)
    
    try:
        agent_path = Path(pydantic_ai_helper.project_root) / "src" / agent_file
        
        if not agent_path.exists():
            raise FileNotFoundError(f"Agent file not found: {agent_file}")
        
        # Read and analyze the agent file
        with open(agent_path, 'r') as f:
            content = f.read()
        
        issues = []
        warnings = []
        suggestions = []
        
        # Check for required imports
        required_imports = ['pydantic_ai', 'Agent', 'BaseModel']
        for imp in required_imports:
            if imp not in content:
                issues.append(f"Missing required import: {imp}")
        
        # Check for agent creation
        if 'Agent(' not in content:
            issues.append("No Agent instance found")
        
        # Check for system prompt
        if 'system_prompt=' not in content:
            warnings.append("No system prompt specified")
        
        # Check for logfire integration
        if 'logfire' not in content:
            suggestions.append("Consider adding logfire for observability")
        
        # Check for error handling
        if 'try:' not in content or 'except' not in content:
            warnings.append("No error handling found")
        
        # Check for async/await patterns
        if 'async def' in content and 'await' not in content:
            warnings.append("Async functions found but no await statements")
        
        # Check for data models
        if 'class' not in content or 'BaseModel' not in content:
            suggestions.append("Consider adding Pydantic data models for type safety")
        
        # Try to validate syntax
        try:
            compile(content, agent_file, 'exec')
        except SyntaxError as e:
            issues.append(f"Syntax error: {e}")
        
        validation_result = {
            "status": "valid" if len(issues) == 0 else "invalid",
            "agent_file": agent_file,
            "issues_count": len(issues),
            "warnings_count": len(warnings),
            "suggestions_count": len(suggestions),
            "issues": issues,
            "warnings": warnings,
            "suggestions": suggestions,
            "has_async_support": "async def" in content,
            "has_error_handling": "try:" in content and "except" in content,
            "has_logfire": "logfire" in content,
            "timestamp": datetime.now().isoformat()
        }
        
        # logfire.info("Pydantic AI agent validation completed", 
        #             agent_file=agent_file,
        #             status=validation_result["status"],
        #             issues_count=len(issues))
        
        return validation_result
        
    except Exception as e:
        # logfire.error("Pydantic AI agent validation failed", 
        pass
        #              agent_file=agent_file,
        #              error=str(e))
        raise

# Server startup handler

async def startup():
    """Server startup handler."""
    # logfire.info("Pydantic AI MCP server starting up")
    
    # Test Pydantic AI environment on startup
    try:
        await pydantic_ai_health_check()
        # logfire.info("Pydantic AI environment verified on startup")
    except Exception as e:
        # logfire.warning("Pydantic AI environment test failed on startup", error=str(e))


        pass
async def shutdown():
    """Server shutdown handler."""
    # logfire.info("Pydantic AI MCP server shutting down")

if __name__ == "__main__":
    # logfire.info("Starting Pydantic AI MCP server")
    import asyncio
    asyncio.run(app.run_stdio_async())