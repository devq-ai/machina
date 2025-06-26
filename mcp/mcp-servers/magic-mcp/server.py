#!/usr/bin/env python3
"""
Magic MCP Server

Advanced AI-powered code generation and transformation server implementing the MCP protocol.
Provides intelligent code generation, refactoring, optimization, and analysis capabilities
using multiple AI models and code analysis tools for enhanced development workflows.

This implementation follows DevQ.ai standards with comprehensive MCP integration,
async operations, structured logging, and robust error handling.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, Set, Tuple
from pathlib import Path
import sys
import os
import hashlib
import ast
import subprocess
from dataclasses import dataclass, asdict
from enum import Enum

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

try:
    from mcp import types
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from pydantic import BaseModel, Field, field_validator
    import aiofiles
    import httpx
    import libcst as cst
    from libcst import MetadataWrapper
    import black
    import isort
    from jinja2 import Template, Environment, FileSystemLoader
    import pygments
    from pygments.lexers import get_lexer_by_name
    from pygments.formatters import get_formatter_by_name
    import tree_sitter
    from tree_sitter import Language, Parser
    import openai
    import anthropic
    from transformers import AutoTokenizer, AutoModelForCausalLM
    import torch
    from rope.base.project import Project
    from rope.base.libutils import path_to_resource
    from rope.refactor.rename import Rename
    from rope.refactor.extract import ExtractMethod
    import radon.complexity as radon_cc
    import radon.metrics as radon_metrics
    from git import Repo
    import yaml
    from dotenv import load_dotenv
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Please ensure all dependencies are installed: pip install -r requirements.txt")
    sys.exit(1)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CodeLanguage(str, Enum):
    """Supported programming languages for code generation."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    CPP = "cpp"
    RUST = "rust"
    GO = "go"
    HTML = "html"
    CSS = "css"
    SQL = "sql"
    BASH = "bash"
    YAML = "yaml"
    JSON = "json"

class CodeGenerationMode(str, Enum):
    """Code generation modes."""
    GENERATE = "generate"
    REFACTOR = "refactor"
    OPTIMIZE = "optimize"
    ANALYZE = "analyze"
    TRANSLATE = "translate"
    DOCUMENT = "document"
    TEST = "test"
    FIX = "fix"

class AIProvider(str, Enum):
    """Supported AI providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    HUGGINGFACE = "huggingface"
    OLLAMA = "ollama"

@dataclass
class CodeGenerationRequest:
    """Request model for code generation."""
    prompt: str
    language: CodeLanguage
    mode: CodeGenerationMode
    context: Optional[str] = None
    existing_code: Optional[str] = None
    style_guide: Optional[str] = None
    max_tokens: int = 2000
    temperature: float = 0.7
    provider: AIProvider = AIProvider.OPENAI

@dataclass
class CodeGenerationResponse:
    """Response model for code generation."""
    generated_code: str
    language: CodeLanguage
    mode: CodeGenerationMode
    confidence: float
    suggestions: List[str]
    metrics: Dict[str, Any]
    timestamp: str
    request_id: str

@dataclass
class CodeAnalysisResult:
    """Result model for code analysis."""
    complexity: Dict[str, Any]
    metrics: Dict[str, Any]
    issues: List[Dict[str, Any]]
    suggestions: List[str]
    quality_score: float

class MagicMCPServer:
    """Advanced AI-powered code generation and transformation server."""

    def __init__(self):
        """Initialize the Magic MCP Server."""
        self.server = Server("magic-mcp")
        self.ai_providers = {}
        self.code_parsers = {}
        self.templates_env = None
        self.git_repo = None
        self.rope_project = None
        self._setup_ai_providers()
        self._setup_code_parsers()
        self._setup_templates()
        self._setup_git_integration()
        self._setup_tools()

    def _setup_ai_providers(self):
        """Initialize AI providers."""
        try:
            # OpenAI
            if os.getenv("OPENAI_API_KEY"):
                self.ai_providers[AIProvider.OPENAI] = openai.AsyncOpenAI(
                    api_key=os.getenv("OPENAI_API_KEY")
                )
                logger.info("OpenAI provider initialized")

            # Anthropic
            if os.getenv("ANTHROPIC_API_KEY"):
                self.ai_providers[AIProvider.ANTHROPIC] = anthropic.AsyncAnthropic(
                    api_key=os.getenv("ANTHROPIC_API_KEY")
                )
                logger.info("Anthropic provider initialized")

            # HuggingFace (local models)
            if torch.cuda.is_available():
                try:
                    tokenizer = AutoTokenizer.from_pretrained("microsoft/CodeGPT-small-py")
                    model = AutoModelForCausalLM.from_pretrained("microsoft/CodeGPT-small-py")
                    self.ai_providers[AIProvider.HUGGINGFACE] = {
                        "tokenizer": tokenizer,
                        "model": model
                    }
                    logger.info("HuggingFace provider initialized")
                except Exception as e:
                    logger.warning(f"HuggingFace provider setup failed: {e}")

        except Exception as e:
            logger.error(f"Error setting up AI providers: {e}")

    def _setup_code_parsers(self):
        """Initialize code parsers for different languages."""
        try:
            # Tree-sitter parsers
            languages = {
                CodeLanguage.PYTHON: "python",
                CodeLanguage.JAVASCRIPT: "javascript",
                CodeLanguage.TYPESCRIPT: "typescript"
            }

            for lang, parser_name in languages.items():
                try:
                    parser = Parser()
                    # Note: In production, you'd need to build the tree-sitter languages
                    # For now, we'll use a placeholder
                    self.code_parsers[lang] = parser
                    logger.info(f"Parser initialized for {lang}")
                except Exception as e:
                    logger.warning(f"Parser setup failed for {lang}: {e}")

        except Exception as e:
            logger.error(f"Error setting up code parsers: {e}")

    def _setup_templates(self):
        """Initialize Jinja2 templates for code generation."""
        try:
            templates_dir = Path(__file__).parent / "templates"
            if templates_dir.exists():
                self.templates_env = Environment(
                    loader=FileSystemLoader(str(templates_dir)),
                    trim_blocks=True,
                    lstrip_blocks=True
                )
                logger.info("Template environment initialized")
            else:
                logger.warning("Templates directory not found")
        except Exception as e:
            logger.error(f"Error setting up templates: {e}")

    def _setup_git_integration(self):
        """Initialize Git integration for context awareness."""
        try:
            current_dir = Path.cwd()
            # Try to find git repo
            for parent in [current_dir] + list(current_dir.parents):
                if (parent / ".git").exists():
                    self.git_repo = Repo(str(parent))
                    logger.info(f"Git repository found: {parent}")
                    break
        except Exception as e:
            logger.warning(f"Git integration setup failed: {e}")

    def _setup_tools(self):
        """Register MCP tools."""

        @self.server.list_tools()
        async def list_tools() -> List[types.Tool]:
            """List available code generation tools."""
            return [
                types.Tool(
                    name="generate_code",
                    description="Generate code using AI based on natural language prompts",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "prompt": {
                                "type": "string",
                                "description": "Natural language description of desired code"
                            },
                            "language": {
                                "type": "string",
                                "enum": [lang.value for lang in CodeLanguage],
                                "description": "Programming language for generation"
                            },
                            "mode": {
                                "type": "string",
                                "enum": [mode.value for mode in CodeGenerationMode],
                                "description": "Code generation mode"
                            },
                            "context": {
                                "type": "string",
                                "description": "Additional context or existing code"
                            },
                            "provider": {
                                "type": "string",
                                "enum": [provider.value for provider in AIProvider],
                                "description": "AI provider to use"
                            }
                        },
                        "required": ["prompt", "language", "mode"]
                    }
                ),
                types.Tool(
                    name="analyze_code",
                    description="Analyze code quality, complexity, and provide suggestions",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "code": {
                                "type": "string",
                                "description": "Code to analyze"
                            },
                            "language": {
                                "type": "string",
                                "enum": [lang.value for lang in CodeLanguage],
                                "description": "Programming language of the code"
                            },
                            "detailed": {
                                "type": "boolean",
                                "description": "Whether to provide detailed analysis"
                            }
                        },
                        "required": ["code", "language"]
                    }
                ),
                types.Tool(
                    name="refactor_code",
                    description="Refactor and optimize existing code",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "code": {
                                "type": "string",
                                "description": "Code to refactor"
                            },
                            "language": {
                                "type": "string",
                                "enum": [lang.value for lang in CodeLanguage],
                                "description": "Programming language"
                            },
                            "refactor_type": {
                                "type": "string",
                                "enum": ["optimize", "extract_method", "rename", "simplify"],
                                "description": "Type of refactoring to perform"
                            },
                            "target": {
                                "type": "string",
                                "description": "Specific target for refactoring (e.g., function name)"
                            }
                        },
                        "required": ["code", "language", "refactor_type"]
                    }
                ),
                types.Tool(
                    name="translate_code",
                    description="Translate code from one language to another",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "code": {
                                "type": "string",
                                "description": "Source code to translate"
                            },
                            "source_language": {
                                "type": "string",
                                "enum": [lang.value for lang in CodeLanguage],
                                "description": "Source programming language"
                            },
                            "target_language": {
                                "type": "string",
                                "enum": [lang.value for lang in CodeLanguage],
                                "description": "Target programming language"
                            },
                            "preserve_comments": {
                                "type": "boolean",
                                "description": "Whether to preserve comments"
                            }
                        },
                        "required": ["code", "source_language", "target_language"]
                    }
                ),
                types.Tool(
                    name="generate_tests",
                    description="Generate unit tests for given code",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "code": {
                                "type": "string",
                                "description": "Code to generate tests for"
                            },
                            "language": {
                                "type": "string",
                                "enum": [lang.value for lang in CodeLanguage],
                                "description": "Programming language"
                            },
                            "test_framework": {
                                "type": "string",
                                "description": "Testing framework to use (e.g., pytest, jest)"
                            },
                            "coverage_target": {
                                "type": "number",
                                "description": "Target code coverage percentage"
                            }
                        },
                        "required": ["code", "language"]
                    }
                ),
                types.Tool(
                    name="document_code",
                    description="Generate documentation for code",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "code": {
                                "type": "string",
                                "description": "Code to document"
                            },
                            "language": {
                                "type": "string",
                                "enum": [lang.value for lang in CodeLanguage],
                                "description": "Programming language"
                            },
                            "doc_style": {
                                "type": "string",
                                "enum": ["google", "sphinx", "numpy", "jsdoc"],
                                "description": "Documentation style"
                            },
                            "include_examples": {
                                "type": "boolean",
                                "description": "Include usage examples"
                            }
                        },
                        "required": ["code", "language"]
                    }
                ),
                types.Tool(
                    name="fix_code",
                    description="Fix bugs and issues in code",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "code": {
                                "type": "string",
                                "description": "Code to fix"
                            },
                            "language": {
                                "type": "string",
                                "enum": [lang.value for lang in CodeLanguage],
                                "description": "Programming language"
                            },
                            "error_message": {
                                "type": "string",
                                "description": "Error message or description of the issue"
                            },
                            "fix_type": {
                                "type": "string",
                                "enum": ["syntax", "logic", "performance", "security"],
                                "description": "Type of fix needed"
                            }
                        },
                        "required": ["code", "language"]
                    }
                ),
                types.Tool(
                    name="get_server_status",
                    description="Get current server status and configuration",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "additionalProperties": False
                    }
                )
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
            """Handle tool calls."""
            try:
                if name == "generate_code":
                    return await self._handle_generate_code(arguments)
                elif name == "analyze_code":
                    return await self._handle_analyze_code(arguments)
                elif name == "refactor_code":
                    return await self._handle_refactor_code(arguments)
                elif name == "translate_code":
                    return await self._handle_translate_code(arguments)
                elif name == "generate_tests":
                    return await self._handle_generate_tests(arguments)
                elif name == "document_code":
                    return await self._handle_document_code(arguments)
                elif name == "fix_code":
                    return await self._handle_fix_code(arguments)
                elif name == "get_server_status":
                    return await self._handle_get_server_status(arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")

            except Exception as e:
                logger.error(f"Error handling tool call {name}: {e}")
                return [types.TextContent(
                    type="text",
                    text=f"Error: {str(e)}"
                )]

    async def _handle_generate_code(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Handle code generation requests."""
        try:
            request = CodeGenerationRequest(
                prompt=arguments["prompt"],
                language=CodeLanguage(arguments["language"]),
                mode=CodeGenerationMode(arguments["mode"]),
                context=arguments.get("context"),
                provider=AIProvider(arguments.get("provider", "openai"))
            )

            response = await self._generate_code(request)

            return [types.TextContent(
                type="text",
                text=json.dumps(asdict(response), indent=2)
            )]

        except Exception as e:
            logger.error(f"Error in generate_code: {e}")
            return [types.TextContent(
                type="text",
                text=f"Error generating code: {str(e)}"
            )]

    async def _generate_code(self, request: CodeGenerationRequest) -> CodeGenerationResponse:
        """Generate code using AI providers."""
        request_id = str(uuid.uuid4())

        try:
            # Select AI provider
            if request.provider not in self.ai_providers:
                raise ValueError(f"AI provider {request.provider} not available")

            provider = self.ai_providers[request.provider]

            # Build prompt
            system_prompt = self._build_system_prompt(request)
            user_prompt = self._build_user_prompt(request)

            # Generate code
            if request.provider == AIProvider.OPENAI:
                generated_code = await self._generate_with_openai(
                    provider, system_prompt, user_prompt, request
                )
            elif request.provider == AIProvider.ANTHROPIC:
                generated_code = await self._generate_with_anthropic(
                    provider, system_prompt, user_prompt, request
                )
            else:
                generated_code = await self._generate_with_fallback(request)

            # Format code
            formatted_code = await self._format_code(generated_code, request.language)

            # Analyze generated code
            analysis = await self._analyze_generated_code(formatted_code, request.language)

            return CodeGenerationResponse(
                generated_code=formatted_code,
                language=request.language,
                mode=request.mode,
                confidence=analysis.get("confidence", 0.8),
                suggestions=analysis.get("suggestions", []),
                metrics=analysis.get("metrics", {}),
                timestamp=datetime.now().isoformat(),
                request_id=request_id
            )

        except Exception as e:
            logger.error(f"Error generating code: {e}")
            raise

    def _build_system_prompt(self, request: CodeGenerationRequest) -> str:
        """Build system prompt for AI models."""
        prompts = {
            CodeGenerationMode.GENERATE: f"""You are an expert {request.language.value} developer.
Generate clean, efficient, and well-documented code following best practices.""",

            CodeGenerationMode.REFACTOR: f"""You are an expert code refactoring specialist.
Improve the given {request.language.value} code while maintaining functionality.""",

            CodeGenerationMode.OPTIMIZE: f"""You are a performance optimization expert.
Optimize the given {request.language.value} code for better performance and efficiency.""",

            CodeGenerationMode.ANALYZE: f"""You are a code analysis expert.
Provide detailed analysis of the given {request.language.value} code.""",

            CodeGenerationMode.TRANSLATE: f"""You are an expert in multiple programming languages.
Translate code while preserving logic and best practices.""",

            CodeGenerationMode.DOCUMENT: f"""You are a technical documentation expert.
Generate clear, comprehensive documentation for the given {request.language.value} code.""",

            CodeGenerationMode.TEST: f"""You are a testing expert.
Generate comprehensive unit tests for the given {request.language.value} code.""",

            CodeGenerationMode.FIX: f"""You are a debugging expert.
Fix bugs and issues in the given {request.language.value} code."""
        }

        return prompts.get(request.mode, prompts[CodeGenerationMode.GENERATE])

    def _build_user_prompt(self, request: CodeGenerationRequest) -> str:
        """Build user prompt for AI models."""
        prompt = f"Task: {request.prompt}\n\n"

        if request.context:
            prompt += f"Context: {request.context}\n\n"

        if request.existing_code:
            prompt += f"Existing code:\n```{request.language.value}\n{request.existing_code}\n```\n\n"

        prompt += f"Please provide {request.language.value} code that:"

        if request.mode == CodeGenerationMode.GENERATE:
            prompt += "\n- Follows best practices and conventions"
            prompt += "\n- Is well-documented with comments"
            prompt += "\n- Handles errors appropriately"
            prompt += "\n- Is efficient and readable"

        return prompt

    async def _generate_with_openai(self, client, system_prompt: str, user_prompt: str, request: CodeGenerationRequest) -> str:
        """Generate code using OpenAI."""
        try:
            response = await client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=request.max_tokens,
                temperature=request.temperature
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            raise

    async def _generate_with_anthropic(self, client, system_prompt: str, user_prompt: str, request: CodeGenerationRequest) -> str:
        """Generate code using Anthropic."""
        try:
            response = await client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )

            return response.content[0].text

        except Exception as e:
            logger.error(f"Anthropic generation failed: {e}")
            raise

    async def _generate_with_fallback(self, request: CodeGenerationRequest) -> str:
        """Fallback code generation using templates."""
        templates = {
            CodeLanguage.PYTHON: """
def generated_function():
    \"\"\"
    Generated function based on: {prompt}
    \"\"\"
    # TODO: Implement functionality
    pass
""",
            CodeLanguage.JAVASCRIPT: """
function generatedFunction() {
    /**
     * Generated function based on: {prompt}
     */
    // TODO: Implement functionality
}
"""
        }

        template = templates.get(request.language, "// Generated code placeholder")
        return template.format(prompt=request.prompt)

    async def _format_code(self, code: str, language: CodeLanguage) -> str:
        """Format code according to language conventions."""
        try:
            if language == CodeLanguage.PYTHON:
                # Use black for Python formatting
                formatted = black.format_str(code, mode=black.FileMode())
                # Use isort for import sorting
                formatted = isort.code(formatted)
                return formatted
            else:
                # For other languages, return as-is for now
                return code

        except Exception as e:
            logger.warning(f"Code formatting failed: {e}")
            return code

    async def _analyze_generated_code(self, code: str, language: CodeLanguage) -> Dict[str, Any]:
        """Analyze generated code quality."""
        try:
            analysis = {
                "confidence": 0.8,
                "suggestions": [],
                "metrics": {}
            }

            if language == CodeLanguage.PYTHON:
                # Analyze Python code
                try:
                    ast.parse(code)
                    analysis["metrics"]["syntactically_valid"] = True
                    analysis["confidence"] = 0.9
                except SyntaxError:
                    analysis["metrics"]["syntactically_valid"] = False
                    analysis["confidence"] = 0.3
                    analysis["suggestions"].append("Fix syntax errors")

                # Calculate complexity
                try:
                    complexity = radon_cc.cc_visit(code)
                    analysis["metrics"]["complexity"] = len(complexity)
                    if len(complexity) > 5:
                        analysis["suggestions"].append("Consider reducing complexity")
                except Exception:
                    pass

            return analysis

        except Exception as e:
            logger.error(f"Code analysis failed: {e}")
            return {"confidence": 0.5, "suggestions": [], "metrics": {}}

    async def _handle_analyze_code(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Handle code analysis requests."""
        try:
            code = arguments["code"]
            language = CodeLanguage(arguments["language"])
            detailed = arguments.get("detailed", False)

            analysis = await self._analyze_code_comprehensive(code, language, detailed)

            return [types.TextContent(
                type="text",
                text=json.dumps(asdict(analysis), indent=2)
            )]

        except Exception as e:
            logger.error(f"Error in analyze_code: {e}")
            return [types.TextContent(
                type="text",
                text=f"Error analyzing code: {str(e)}"
            )]

    async def _analyze_code_comprehensive(self, code: str, language: CodeLanguage, detailed: bool) -> CodeAnalysisResult:
        """Perform comprehensive code analysis."""
        try:
            issues = []
            suggestions = []
            metrics = {}
            complexity = {}

            if language == CodeLanguage.PYTHON:
                # Python-specific analysis
                try:
                    # Parse AST
                    tree = ast.parse(code)

                    # Count various elements
                    functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
                    classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]

                    metrics.update({
                        "lines_of_code": len(code.splitlines()),
                        "functions": len(functions),
                        "classes": len(classes)
                    })

                    # Complexity analysis
                    try:
                        cc_results = radon_cc.cc_visit(code)
                        complexity = {
                            "cyclomatic_complexity": sum(result.complexity for result in cc_results),
                            "average_complexity": sum(result.complexity for result in cc_results) / len(cc_results) if cc_results else 0
                        }

                        if complexity["average_complexity"] > 10:
                            issues.append({
                                "type": "complexity",
                                "severity": "high",
                                "message": "High cyclomatic complexity detected"
                            })
                            suggestions.append("Consider breaking down complex functions")
                    except Exception:
                        pass

                    # Check for common issues
                    if "TODO" in code or "FIXME" in code:
                        issues.append({
                            "type": "todo",
                            "severity": "low",
                            "message": "TODO/FIXME comments found"
                        })

                except SyntaxError as e:
                    issues.append({
                        "type": "syntax",
                        "severity": "critical",
                        "message": f"Syntax error: {str(e)}"
                    })

            # Calculate quality score
            quality_score = self._calculate_quality_score(issues, metrics, complexity)

            return CodeAnalysisResult(
                complexity=complexity,
                metrics=metrics,
                issues=issues,
                suggestions=suggestions,
                quality_score=quality_score
            )

        except Exception as e:
            logger.error(f"Comprehensive code analysis failed: {e}")
            return CodeAnalysisResult(
                complexity={},
                metrics={},
                issues=[{"type": "error", "severity": "critical", "message": str(e)}],
                suggestions=[],
                quality_score=0.0
            )

    def _calculate_quality_score(self, issues: List[Dict], metrics: Dict, complexity: Dict) -> float:
        """Calculate code quality score."""
        score = 1.0

        # Deduct points for issues
        for issue in issues:
            if issue["severity"] == "critical":
                score -= 0.3
            elif issue["severity"] == "high":
                score -= 0.2
            elif issue["severity"] == "medium":
                score -= 0.1
            elif issue["severity"] == "low":
                score -= 0.05

        # Deduct points for high complexity
        if complexity.get("average_complexity", 0) > 10:
            score -= 0.2

        return max(0.0, score)

    async def _handle_refactor_code(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Handle code refactoring requests."""
        try:
            code = arguments["code"]
            language = CodeLanguage(arguments["language"])
            refactor_type = arguments["refactor_type"]
            target = arguments.get("target")

            refactored_code = await self._refactor_code(code, language, refactor_type, target)

            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "original_code": code,
                    "refactored_code": refactored_code,
                    "refactor_type": refactor_type,
                    "language": language.value
                }, indent=2)
            )]

        except Exception as e:
            logger.error(f"Error in refactor_code: {e}")
            return [types.TextContent(
                type="text",
                text=f"Error refactoring code: {str(e)}"
            )]

    async def _refactor_code(self, code: str, language: CodeLanguage, refactor_type: str, target: Optional[str]) -> str:
        """Refactor code based on specified type."""
        try:
            if language == CodeLanguage.PYTHON:
                if refactor_type == "optimize":
                    return await self._optimize_python_code(code)
                elif refactor_type == "extract_method":
                    return await self._extract_method_python(code, target)
                elif refactor_type == "simplify":
                    return await self._simplify_python_code(code)

            # Fallback to AI-based refactoring
            return await self._ai_refactor_code(code, language, refactor_type, target)

        except Exception as e:
            logger.error(f"Code refactoring failed: {e}")
            return code

    async def _optimize_python_code(self, code: str) -> str:
        """Optimize Python code for better performance."""
        try:
            # Use AST to analyze and optimize
            tree = ast.parse(code)

            # Simple optimizations (placeholder)
            optimized_code = code

            # Format with black
            optimized_code = black.format_str(optimized_code, mode=black.FileMode())

            return optimized_code
        except Exception as e:
            logger.error(f"Python optimization failed: {e}")
            return code

    async def _extract_method_python(self, code: str, target: Optional[str]) -> str:
        """Extract method from Python code."""
        try:
            # This would require more sophisticated AST manipulation
            # For now, return original code with comment
            return f"# Method extraction for {target}\n{code}"
        except Exception as e:
            logger.error(f"Method extraction failed: {e}")
            return code

    async def _simplify_python_code(self, code: str) -> str:
        """Simplify Python code structure."""
        try:
            # Simple transformations
            simplified = code.replace("    ", "  ")  # Reduce indentation
            return black.format_str(simplified, mode=black.FileMode())
        except Exception as e:
            logger.error(f"Code simplification failed: {e}")
            return code

    async def _ai_refactor_code(self, code: str, language: CodeLanguage, refactor_type: str, target: Optional[str]) -> str:
        """Use AI to refactor code."""
        try:
            if AIProvider.OPENAI in self.ai_providers:
                client = self.ai_providers[AIProvider.OPENAI]
                prompt = f"Refactor this {language.value} code using {refactor_type} approach:\n\n{code}"

                response = await client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": f"You are a code refactoring expert. Refactor the given code using {refactor_type} approach."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=2000,
                    temperature=0.3
                )

                return response.choices[0].message.content
            else:
                return code
        except Exception as e:
            logger.error(f"AI refactoring failed: {e}")
            return code

    async def _handle_translate_code(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Handle code translation requests."""
        try:
            code = arguments["code"]
            source_language = CodeLanguage(arguments["source_language"])
            target_language = CodeLanguage(arguments["target_language"])
            preserve_comments = arguments.get("preserve_comments", True)

            translated_code = await self._translate_code(code, source_language, target_language, preserve_comments)

            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "original_code": code,
                    "translated_code": translated_code,
                    "source_language": source_language.value,
                    "target_language": target_language.value,
                    "preserve_comments": preserve_comments
                }, indent=2)
            )]

        except Exception as e:
            logger.error(f"Error in translate_code: {e}")
            return [types.TextContent(
                type="text",
                text=f"Error translating code: {str(e)}"
            )]

    async def _translate_code(self, code: str, source_language: CodeLanguage, target_language: CodeLanguage, preserve_comments: bool) -> str:
        """Translate code between programming languages."""
        try:
            if AIProvider.OPENAI in self.ai_providers:
                client = self.ai_providers[AIProvider.OPENAI]

                system_prompt = f"""You are an expert programmer fluent in multiple languages.
Translate the given {source_language.value} code to {target_language.value}.
Maintain the same functionality and logic.
{"Preserve comments and documentation." if preserve_comments else ""}
Follow best practices for the target language."""

                user_prompt = f"Translate this {source_language.value} code to {target_language.value}:\n\n{code}"

                response = await client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=2000,
                    temperature=0.3
                )

                return response.choices[0].message.content
            else:
                return f"# Translated from {source_language.value} to {target_language.value}\n{code}"

        except Exception as e:
            logger.error(f"Code translation failed: {e}")
            return code

    async def _handle_generate_tests(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Handle test generation requests."""
        try:
            code = arguments["code"]
            language = CodeLanguage(arguments["language"])
            test_framework = arguments.get("test_framework", "pytest" if language == CodeLanguage.PYTHON else "jest")
            coverage_target = arguments.get("coverage_target", 90)

            test_code = await self._generate_tests(code, language, test_framework, coverage_target)

            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "original_code": code,
                    "test_code": test_code,
                    "language": language.value,
                    "test_framework": test_framework,
                    "coverage_target": coverage_target
                }, indent=2)
            )]

        except Exception as e:
            logger.error(f"Error in generate_tests: {e}")
            return [types.TextContent(
                type="text",
                text=f"Error generating tests: {str(e)}"
            )]

    async def _generate_tests(self, code: str, language: CodeLanguage, test_framework: str, coverage_target: int) -> str:
        """Generate comprehensive tests for given code."""
        try:
            if AIProvider.OPENAI in self.ai_providers:
                client = self.ai_providers[AIProvider.OPENAI]

                system_prompt = f"""You are a testing expert specializing in {language.value}.
Generate comprehensive unit tests using {test_framework} framework.
Target {coverage_target}% code coverage.
Include edge cases, error conditions, and positive/negative test cases.
Follow testing best practices and conventions."""

                user_prompt = f"Generate tests for this {language.value} code:\n\n{code}"

                response = await client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=2000,
                    temperature=0.3
                )

                return response.choices[0].message.content
            else:
                # Fallback template
                if language == CodeLanguage.PYTHON:
                    return f"""import pytest
from unittest.mock import Mock, patch

# Test for generated code
def test_generated_function():
    \"\"\"Test the generated function.\"\"\"
    # TODO: Implement test cases
    pass

# Original code being tested:
# {code}
"""
                else:
                    return f"// Test for {language.value} code\n// {code}"

        except Exception as e:
            logger.error(f"Test generation failed: {e}")
            return f"// Error generating tests: {str(e)}"

    async def _handle_document_code(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Handle code documentation requests."""
        try:
            code = arguments["code"]
            language = CodeLanguage(arguments["language"])
            doc_style = arguments.get("doc_style", "google")
            include_examples = arguments.get("include_examples", True)

            documented_code = await self._document_code(code, language, doc_style, include_examples)

            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "original_code": code,
                    "documented_code": documented_code,
                    "language": language.value,
                    "doc_style": doc_style,
                    "include_examples": include_examples
                }, indent=2)
            )]

        except Exception as e:
            logger.error(f"Error in document_code: {e}")
            return [types.TextContent(
                type="text",
                text=f"Error documenting code: {str(e)}"
            )]

    async def _document_code(self, code: str, language: CodeLanguage, doc_style: str, include_examples: bool) -> str:
        """Generate documentation for code."""
        try:
            if AIProvider.OPENAI in self.ai_providers:
                client = self.ai_providers[AIProvider.OPENAI]

                system_prompt = f"""You are a technical documentation expert.
Generate comprehensive documentation for {language.value} code using {doc_style} style.
{"Include usage examples and code samples." if include_examples else ""}
Add clear descriptions, parameter details, return values, and any exceptions.
Follow documentation best practices."""

                user_prompt = f"Document this {language.value} code:\n\n{code}"

                response = await client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=2000,
                    temperature=0.3
                )

                return response.choices[0].message.content
            else:
                # Fallback documentation
                return f'"""\nGenerated documentation for {language.value} code.\n\nCode:\n{code}\n"""'

        except Exception as e:
            logger.error(f"Code documentation failed: {e}")
            return code

    async def _handle_fix_code(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Handle code fixing requests."""
        try:
            code = arguments["code"]
            language = CodeLanguage(arguments["language"])
            error_message = arguments.get("error_message", "")
            fix_type = arguments.get("fix_type", "general")

            fixed_code = await self._fix_code(code, language, error_message, fix_type)

            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "original_code": code,
                    "fixed_code": fixed_code,
                    "language": language.value,
                    "error_message": error_message,
                    "fix_type": fix_type
                }, indent=2)
            )]

        except Exception as e:
            logger.error(f"Error in fix_code: {e}")
            return [types.TextContent(
                type="text",
                text=f"Error fixing code: {str(e)}"
            )]

    async def _fix_code(self, code: str, language: CodeLanguage, error_message: str, fix_type: str) -> str:
        """Fix bugs and issues in code."""
        try:
            if AIProvider.OPENAI in self.ai_providers:
                client = self.ai_providers[AIProvider.OPENAI]

                system_prompt = f"""You are a debugging expert for {language.value}.
Fix the given code based on the error message and fix type.
Maintain the original functionality while resolving issues.
Provide clean, working code that follows best practices."""

                user_prompt = f"""Fix this {language.value} code:

Error message: {error_message}
Fix type: {fix_type}

Code to fix:
{code}"""

                response = await client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=2000,
                    temperature=0.3
                )

                return response.choices[0].message.content
            else:
                # Basic syntax fix attempts
                if language == CodeLanguage.PYTHON:
                    try:
                        ast.parse(code)
                        return code  # Already valid
                    except SyntaxError as e:
                        return f"# Syntax error found: {str(e)}\n{code}"
                else:
                    return code

        except Exception as e:
            logger.error(f"Code fixing failed: {e}")
            return code

    async def _handle_get_server_status(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Handle server status requests."""
        try:
            status = {
                "server_name": "magic-mcp",
                "version": "1.0.0",
                "status": "running",
                "ai_providers": {
                    provider.value: "available" if provider in self.ai_providers else "unavailable"
                    for provider in AIProvider
                },
                "supported_languages": [lang.value for lang in CodeLanguage],
                "supported_modes": [mode.value for mode in CodeGenerationMode],
                "features": {
                    "code_generation": True,
                    "code_analysis": True,
                    "code_refactoring": True,
                    "code_translation": True,
                    "test_generation": True,
                    "documentation": True,
                    "bug_fixing": True,
                    "git_integration": self.git_repo is not None,
                    "template_system": self.templates_env is not None
                },
                "system_info": {
                    "python_version": sys.version,
                    "cuda_available": torch.cuda.is_available() if 'torch' in sys.modules else False
                },
                "timestamp": datetime.now().isoformat()
            }

            return [types.TextContent(
                type="text",
                text=json.dumps(status, indent=2)
            )]

        except Exception as e:
            logger.error(f"Error getting server status: {e}")
            return [types.TextContent(
                type="text",
                text=f"Error getting server status: {str(e)}"
            )]

    async def run(self):
        """Run the Magic MCP Server."""
        logger.info("Starting Magic MCP Server...")

        # Log server configuration
        logger.info(f"AI Providers available: {list(self.ai_providers.keys())}")
        logger.info(f"Supported languages: {[lang.value for lang in CodeLanguage]}")
        logger.info(f"Git integration: {'enabled' if self.git_repo else 'disabled'}")

        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


def main():
    """Main entry point for the Magic MCP Server."""
    try:
        server = MagicMCPServer()
        asyncio.run(server.run())
    except KeyboardInterrupt:
        logger.info("Server shutting down...")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
