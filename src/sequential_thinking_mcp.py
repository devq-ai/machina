#!/usr/bin/env python
"""
Sequential Thinking MCP Server
FastMCP server for sequential reasoning and complex problem-solving workflows.
Provides step-by-step reasoning, decision trees, and workflow management.
"""
import asyncio
import os
import json
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from enum import Enum

import logfire
from fastmcp import FastMCP
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logfire
# logfire.configure(
#     token=os.getenv('LOGFIRE_WRITE_TOKEN'),
#     service_name='sequential-thinking-mcp-server',
#     environment='production'
# )

# Create FastMCP app instance
app = FastMCP("sequential-thinking-mcp")

class ThinkingStepType(Enum):
    """Types of thinking steps."""
    ANALYSIS = "analysis"
    HYPOTHESIS = "hypothesis"
    EVIDENCE = "evidence"
    CONCLUSION = "conclusion"
    DECISION = "decision"
    ACTION = "action"

class ReasoningMode(Enum):
    """Different reasoning modes."""
    DEDUCTIVE = "deductive"
    INDUCTIVE = "inductive"
    ABDUCTIVE = "abductive"
    CRITICAL = "critical"
    CREATIVE = "creative"

class ThinkingStep:
    """Individual step in sequential thinking process."""
    
    def __init__(
        self,
        step_id: str,
        step_type: ThinkingStepType,
        content: str,
        reasoning: str,
        confidence: float = 0.5,
        dependencies: Optional[List[str]] = None
    ):
        self.step_id = step_id
        self.step_type = step_type
        self.content = content
        self.reasoning = reasoning
        self.confidence = confidence
        self.dependencies = dependencies or []
        self.timestamp = datetime.now().isoformat()
        self.completed = False
        self.result = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert step to dictionary."""
        return {
            "step_id": self.step_id,
            "step_type": self.step_type.value,
            "content": self.content,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "dependencies": self.dependencies,
            "timestamp": self.timestamp,
            "completed": self.completed,
            "result": self.result
        }

class SequentialThinkingEngine:
    """Engine for managing sequential thinking processes."""
    
    def __init__(self):
        self.active_workflows = {}
        self.completed_workflows = {}
    
    def create_workflow(self, workflow_id: str, problem: str, mode: ReasoningMode) -> Dict[str, Any]:
        """Create a new thinking workflow."""
        workflow = {
            "workflow_id": workflow_id,
            "problem": problem,
            "reasoning_mode": mode.value,
            "steps": [],
            "current_step": 0,
            "status": "initialized",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        self.active_workflows[workflow_id] = workflow
        return workflow
    
    def add_step(self, workflow_id: str, step: ThinkingStep) -> bool:
        """Add a step to a workflow."""
        if workflow_id not in self.active_workflows:
            return False
        
        workflow = self.active_workflows[workflow_id]
        workflow["steps"].append(step.to_dict())
        workflow["updated_at"] = datetime.now().isoformat()
        
        return True
    
    def execute_step(self, workflow_id: str, step_id: str) -> Dict[str, Any]:
        """Execute a specific step in the workflow."""
        if workflow_id not in self.active_workflows:
            raise ValueError(f"Workflow not found: {workflow_id}")
        
        workflow = self.active_workflows[workflow_id]
        
        # Find the step
        step_data = None
        for step in workflow["steps"]:
            if step["step_id"] == step_id:
                step_data = step
                break
        
        if not step_data:
            raise ValueError(f"Step not found: {step_id}")
        
        # Check dependencies
        for dep_id in step_data["dependencies"]:
            dep_completed = any(
                s["step_id"] == dep_id and s["completed"]
                for s in workflow["steps"]
            )
            if not dep_completed:
                raise ValueError(f"Dependency not completed: {dep_id}")
        
        # Execute the step (simplified simulation)
        step_data["completed"] = True
        step_data["result"] = f"Executed: {step_data['content']}"
        
        workflow["updated_at"] = datetime.now().isoformat()
        
        return step_data

thinking_engine = SequentialThinkingEngine()

@app.tool()
@logfire.instrument("thinking_health_check")
async def thinking_health_check() -> Dict[str, Any]:
    """Check sequential thinking engine health."""
    # logfire.info("Sequential thinking health check requested")
    
    try:
        health_status = {
            "status": "healthy",
            "active_workflows": len(thinking_engine.active_workflows),
            "completed_workflows": len(thinking_engine.completed_workflows),
            "reasoning_modes": [mode.value for mode in ReasoningMode],
            "step_types": [step_type.value for step_type in ThinkingStepType],
            "timestamp": datetime.now().isoformat()
        }
        
        # logfire.info("Sequential thinking health check completed", health_status=health_status)
        return health_status
        
    except Exception as e:
        # logfire.error("Sequential thinking health check failed", error=str(e))
        pass
        raise

@app.tool()
@logfire.instrument("create_thinking_workflow")
async def create_thinking_workflow(
    problem: str,
    reasoning_mode: str = "critical",
    workflow_id: Optional[str] = None
) -> Dict[str, Any]:
    """Create a new sequential thinking workflow."""
    # logfire.info("Creating thinking workflow", problem=problem[:100], reasoning_mode=reasoning_mode)
    
    try:
        if not workflow_id:
            workflow_id = f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}"
        
        # Validate reasoning mode
        try:
            mode = ReasoningMode(reasoning_mode)
        except ValueError:
            raise ValueError(f"Invalid reasoning mode: {reasoning_mode}")
        
        workflow = thinking_engine.create_workflow(workflow_id, problem, mode)
        
        # logfire.info("Thinking workflow created", 
        #             workflow_id=workflow_id,
        #             reasoning_mode=reasoning_mode)
        
        return workflow
        
    except Exception as e:
        # logfire.error("Failed to create thinking workflow", 
        pass
        #              problem=problem[:100],
        #              error=str(e))
        raise

@app.tool()
@logfire.instrument("add_thinking_step")
async def add_thinking_step(
    workflow_id: str,
    step_type: str,
    content: str,
    reasoning: str,
    confidence: float = 0.5,
    dependencies: Optional[List[str]] = None,
    step_id: Optional[str] = None
) -> Dict[str, Any]:
    """Add a thinking step to a workflow."""
    # logfire.info("Adding thinking step", 
    #             workflow_id=workflow_id,
    #             step_type=step_type,
    #             content=content[:100])
    
    try:
        if not step_id:
            step_id = f"step_{len(thinking_engine.active_workflows[workflow_id]['steps']) + 1}"
        
        # Validate step type
        try:
            step_type_enum = ThinkingStepType(step_type)
        except ValueError:
            raise ValueError(f"Invalid step type: {step_type}")
        
        # Validate confidence
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        
        step = ThinkingStep(
            step_id=step_id,
            step_type=step_type_enum,
            content=content,
            reasoning=reasoning,
            confidence=confidence,
            dependencies=dependencies or []
        )
        
        success = thinking_engine.add_step(workflow_id, step)
        
        if not success:
            raise ValueError(f"Workflow not found: {workflow_id}")
        
        step_data = step.to_dict()
        
        # logfire.info("Thinking step added", 
        #             workflow_id=workflow_id,
        #             step_id=step_id,
        #             step_type=step_type)
        
        return step_data
        
    except Exception as e:
        # logfire.error("Failed to add thinking step", 
        pass
        #              workflow_id=workflow_id,
        #              step_type=step_type,
        #              error=str(e))
        raise

@app.tool()
@logfire.instrument("execute_thinking_step")
async def execute_thinking_step(workflow_id: str, step_id: str) -> Dict[str, Any]:
    """Execute a specific thinking step."""
    # logfire.info("Executing thinking step", workflow_id=workflow_id, step_id=step_id)
    
    try:
        step_result = thinking_engine.execute_step(workflow_id, step_id)
        
        # logfire.info("Thinking step executed", 
        #             workflow_id=workflow_id,
        #             step_id=step_id,
        #             completed=step_result["completed"])
        
        return step_result
        
    except Exception as e:
        # logfire.error("Failed to execute thinking step", 
        pass
        #              workflow_id=workflow_id,
        #              step_id=step_id,
        #              error=str(e))
        raise

@app.tool()
@logfire.instrument("get_workflow_status")
async def get_workflow_status(workflow_id: str) -> Dict[str, Any]:
    """Get the status of a thinking workflow."""
    # logfire.info("Getting workflow status", workflow_id=workflow_id)
    
    try:
        if workflow_id in thinking_engine.active_workflows:
            workflow = thinking_engine.active_workflows[workflow_id]
            workflow_status = "active"
        elif workflow_id in thinking_engine.completed_workflows:
            workflow = thinking_engine.completed_workflows[workflow_id]
            workflow_status = "completed"
        else:
            raise ValueError(f"Workflow not found: {workflow_id}")
        
        # Calculate progress
        total_steps = len(workflow["steps"])
        completed_steps = sum(1 for step in workflow["steps"] if step["completed"])
        progress = (completed_steps / total_steps * 100) if total_steps > 0 else 0
        
        status = {
            "workflow_id": workflow_id,
            "status": workflow_status,
            "problem": workflow["problem"],
            "reasoning_mode": workflow["reasoning_mode"],
            "total_steps": total_steps,
            "completed_steps": completed_steps,
            "progress_percent": round(progress, 2),
            "created_at": workflow["created_at"],
            "updated_at": workflow["updated_at"],
            "steps": workflow["steps"]
        }
        
        # logfire.info("Workflow status retrieved", 
        #             workflow_id=workflow_id,
        #             status=workflow_status,
        #             progress=progress)
        
        return status
        
    except Exception as e:
        # logfire.error("Failed to get workflow status", 
        pass
        #              workflow_id=workflow_id,
        #              error=str(e))
        raise

@app.tool()
@logfire.instrument("analyze_problem")
async def analyze_problem(
    problem: str,
    reasoning_mode: str = "critical",
    auto_generate_steps: bool = True
) -> Dict[str, Any]:
    """Analyze a problem and optionally generate thinking steps."""
    # logfire.info("Analyzing problem", 
    #             problem=problem[:100],
    #             reasoning_mode=reasoning_mode,
    #             auto_generate_steps=auto_generate_steps)
    
    try:
        # Create workflow
        workflow_id = f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}"
        workflow = thinking_engine.create_workflow(workflow_id, problem, ReasoningMode(reasoning_mode))
        
        analysis_result = {
            "workflow_id": workflow_id,
            "problem": problem,
            "reasoning_mode": reasoning_mode,
            "analysis": {
                "complexity": "medium",  # Simplified analysis
                "domain": "general",
                "estimated_steps": 5,
                "confidence": 0.7
            },
            "generated_steps": []
        }
        
        if auto_generate_steps:
            # Generate basic thinking steps based on reasoning mode
            if reasoning_mode == "critical":
                suggested_steps = [
                    ("analysis", "Break down the problem into components", "Identify key elements and relationships"),
                    ("hypothesis", "Generate potential solutions", "Consider multiple approaches"),
                    ("evidence", "Evaluate evidence for each solution", "Assess pros and cons"),
                    ("conclusion", "Select the best approach", "Make informed decision"),
                    ("action", "Plan implementation", "Define concrete next steps")
                ]
            elif reasoning_mode == "creative":
                suggested_steps = [
                    ("analysis", "Understand the problem space", "Explore context and constraints"),
                    ("hypothesis", "Brainstorm creative solutions", "Think outside conventional approaches"),
                    ("evidence", "Test feasibility of ideas", "Validate creative concepts"),
                    ("conclusion", "Synthesize best ideas", "Combine elements creatively"),
                    ("action", "Create implementation plan", "Define creative execution strategy")
                ]
            else:
                suggested_steps = [
                    ("analysis", "Analyze the problem", "Understanding key aspects"),
                    ("hypothesis", "Consider options", "Evaluate alternatives"),
                    ("conclusion", "Reach conclusion", "Make final determination"),
                    ("action", "Plan next steps", "Define implementation")
                ]
            
            for i, (step_type, content, reasoning) in enumerate(suggested_steps, 1):
                step = ThinkingStep(
                    step_id=f"auto_step_{i}",
                    step_type=ThinkingStepType(step_type),
                    content=content,
                    reasoning=reasoning,
                    confidence=0.6
                )
                
                thinking_engine.add_step(workflow_id, step)
                analysis_result["generated_steps"].append(step.to_dict())
        
        # logfire.info("Problem analysis completed", 
        #             workflow_id=workflow_id,
        #             generated_steps=len(analysis_result["generated_steps"]))
        
        return analysis_result
        
    except Exception as e:
        # logfire.error("Failed to analyze problem", 
        pass
        #              problem=problem[:100],
        #              error=str(e))
        raise

@app.tool()
@logfire.instrument("execute_workflow")
async def execute_workflow(workflow_id: str) -> Dict[str, Any]:
    """Execute all steps in a thinking workflow."""
    # logfire.info("Executing workflow", workflow_id=workflow_id)
    
    try:
        if workflow_id not in thinking_engine.active_workflows:
            raise ValueError(f"Workflow not found: {workflow_id}")
        
        workflow = thinking_engine.active_workflows[workflow_id]
        execution_results = []
        
        # Execute steps in order, respecting dependencies
        for step_data in workflow["steps"]:
            if not step_data["completed"]:
                try:
                    result = thinking_engine.execute_step(workflow_id, step_data["step_id"])
                    execution_results.append({
                        "step_id": step_data["step_id"],
                        "status": "completed",
                        "result": result["result"]
                    })
                except Exception as e:
                    execution_results.append({
                        "step_id": step_data["step_id"],
                        "status": "failed",
                        "error": str(e)
                    })
        
        # Calculate final status
        total_steps = len(workflow["steps"])
        completed_steps = sum(1 for step in workflow["steps"] if step["completed"])
        success_rate = (completed_steps / total_steps * 100) if total_steps > 0 else 0
        
        execution_summary = {
            "workflow_id": workflow_id,
            "status": "completed" if success_rate == 100 else "partially_completed",
            "total_steps": total_steps,
            "completed_steps": completed_steps,
            "success_rate": round(success_rate, 2),
            "execution_results": execution_results,
            "timestamp": datetime.now().isoformat()
        }
        
        # Move to completed if fully successful
        if success_rate == 100:
            thinking_engine.completed_workflows[workflow_id] = thinking_engine.active_workflows.pop(workflow_id)
        
        # logfire.info("Workflow execution completed", 
        #             workflow_id=workflow_id,
        #             success_rate=success_rate,
        #             completed_steps=completed_steps)
        
        return execution_summary
        
    except Exception as e:
        # logfire.error("Failed to execute workflow", 
        pass
        #              workflow_id=workflow_id,
        #              error=str(e))
        raise

@app.tool()
@logfire.instrument("list_workflows")
async def list_workflows(include_completed: bool = False) -> Dict[str, Any]:
    """List all thinking workflows."""
    # logfire.info("Listing workflows", include_completed=include_completed)
    
    try:
        workflows = {
            "active_workflows": list(thinking_engine.active_workflows.keys()),
            "active_count": len(thinking_engine.active_workflows)
        }
        
        if include_completed:
            workflows["completed_workflows"] = list(thinking_engine.completed_workflows.keys())
            workflows["completed_count"] = len(thinking_engine.completed_workflows)
        
        workflows["timestamp"] = datetime.now().isoformat()
        
        # logfire.info("Workflows listed", 
        #             active_count=workflows["active_count"],
        #             completed_count=workflows.get("completed_count", 0))
        
        return workflows
        
    except Exception as e:
        # logfire.error("Failed to list workflows", error=str(e))
        pass
        raise

@app.tool()
@logfire.instrument("get_reasoning_templates")
async def get_reasoning_templates() -> Dict[str, Any]:
    """Get templates for different reasoning modes."""
    # logfire.info("Getting reasoning templates")
    
    try:
        templates = {
            "critical": {
                "description": "Systematic analysis and evaluation",
                "steps": [
                    {"type": "analysis", "description": "Break down and examine components"},
                    {"type": "evidence", "description": "Gather and evaluate supporting evidence"},
                    {"type": "hypothesis", "description": "Consider alternative explanations"},
                    {"type": "conclusion", "description": "Draw logical conclusions"},
                    {"type": "action", "description": "Plan implementation"}
                ]
            },
            "creative": {
                "description": "Innovative and imaginative problem solving",
                "steps": [
                    {"type": "analysis", "description": "Explore problem space creatively"},
                    {"type": "hypothesis", "description": "Generate novel ideas and approaches"},
                    {"type": "evidence", "description": "Test feasibility of creative solutions"},
                    {"type": "conclusion", "description": "Synthesize best creative elements"},
                    {"type": "action", "description": "Implement creative solution"}
                ]
            },
            "deductive": {
                "description": "Reasoning from general to specific",
                "steps": [
                    {"type": "analysis", "description": "Establish general principles"},
                    {"type": "hypothesis", "description": "Apply principles to specific case"},
                    {"type": "evidence", "description": "Verify logical consistency"},
                    {"type": "conclusion", "description": "Draw specific conclusions"}
                ]
            },
            "inductive": {
                "description": "Reasoning from specific to general",
                "steps": [
                    {"type": "analysis", "description": "Gather specific observations"},
                    {"type": "evidence", "description": "Identify patterns and trends"},
                    {"type": "hypothesis", "description": "Form general principles"},
                    {"type": "conclusion", "description": "Establish general rules"}
                ]
            }
        }
        
        templates_info = {
            "templates": templates,
            "available_modes": list(templates.keys()),
            "step_types": [step_type.value for step_type in ThinkingStepType],
            "timestamp": datetime.now().isoformat()
        }
        
        # logfire.info("Reasoning templates retrieved", 
        #             template_count=len(templates))
        
        return templates_info
        
    except Exception as e:
        # logfire.error("Failed to get reasoning templates", error=str(e))
        pass
        raise

# Server startup handler

async def startup():
    """Server startup handler."""
    # logfire.info("Sequential Thinking MCP server starting up")
    
    # Test thinking engine on startup
    try:
        await thinking_health_check()
        # logfire.info("Sequential thinking engine verified on startup")
    except Exception as e:
        # logfire.warning("Sequential thinking engine test failed on startup", error=str(e))


        pass
async def shutdown():
    """Server shutdown handler."""
    # logfire.info("Sequential Thinking MCP server shutting down")

if __name__ == "__main__":
    # logfire.info("Starting Sequential Thinking MCP server")
    import asyncio
    asyncio.run(app.run_stdio_async())