#!/usr/bin/env python3
"""
Magic MCP Server Package

AI-powered code generation and transformation server implementing the MCP protocol.
Provides intelligent code generation, analysis, refactoring, and optimization capabilities
using multiple AI models for enhanced development workflows.

This package follows DevQ.ai standards with comprehensive MCP integration,
async operations, structured logging, and robust error handling.
"""

__version__ = "1.0.0"
__author__ = "DevQ.ai Team"
__email__ = "dion@devq.ai"
__description__ = "Advanced AI-powered code generation and transformation MCP server"

try:
    from server import (
        MagicMCPServer,
        CodeLanguage,
        CodeGenerationMode,
        AIProvider,
        CodeGenerationRequest,
        CodeGenerationResponse,
        CodeAnalysisResult
    )
except ImportError:
    # Fallback for when imported as a package
    from .server import (
        MagicMCPServer,
        CodeLanguage,
        CodeGenerationMode,
        AIProvider,
        CodeGenerationRequest,
        CodeGenerationResponse,
        CodeAnalysisResult
    )

__all__ = [
    "MagicMCPServer",
    "CodeLanguage",
    "CodeGenerationMode",
    "AIProvider",
    "CodeGenerationRequest",
    "CodeGenerationResponse",
    "CodeAnalysisResult"
]
