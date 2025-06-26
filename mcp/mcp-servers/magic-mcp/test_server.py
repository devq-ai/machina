#!/usr/bin/env python3
"""
Comprehensive test suite for Magic MCP Server

Tests all code generation, analysis, refactoring, and AI-powered capabilities
following DevQ.ai testing standards with async operations and mock integrations.
"""

import pytest
import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, List
import pytest_asyncio

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

# Import server components
from server import (
    MagicMCPServer,
    CodeLanguage,
    CodeGenerationMode,
    AIProvider,
    CodeGenerationRequest,
    CodeGenerationResponse,
    CodeAnalysisResult
)

class TestMagicMCPServer:
    """Test suite for Magic MCP Server."""

    @pytest_asyncio.fixture
    async def server(self):
        """Create a test server instance."""
        with patch.dict('os.environ', {
            'OPENAI_API_KEY': 'test-openai-key',
            'ANTHROPIC_API_KEY': 'test-anthropic-key'
        }):
            server = MagicMCPServer()
            yield server

    @pytest.fixture
    def sample_python_code(self):
        """Sample Python code for testing."""
        return """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n-1)
"""

    @pytest.fixture
    def sample_javascript_code(self):
        """Sample JavaScript code for testing."""
        return """
function fibonacci(n) {
    if (n <= 1) {
        return n;
    }
    return fibonacci(n-1) + fibonacci(n-2);
}

function factorial(n) {
    if (n <= 1) {
        return 1;
    }
    return n * factorial(n-1);
}
"""

    @pytest.mark.asyncio
    async def test_server_initialization(self, server):
        """Test server initialization."""
        assert server.server.name == "magic-mcp"
        assert isinstance(server.ai_providers, dict)
        assert isinstance(server.code_parsers, dict)

    @pytest.mark.asyncio
    async def test_list_tools(self, server):
        """Test tool listing functionality."""
        tools = await server.server.list_tools()()

        expected_tools = [
            "generate_code",
            "analyze_code",
            "refactor_code",
            "translate_code",
            "generate_tests",
            "document_code",
            "fix_code",
            "get_server_status"
        ]

        tool_names = [tool.name for tool in tools]
        for tool_name in expected_tools:
            assert tool_name in tool_names

    @pytest.mark.asyncio
    async def test_generate_code_basic(self, server):
        """Test basic code generation."""
        with patch.object(server, '_generate_code', new_callable=AsyncMock) as mock_generate:
            mock_response = CodeGenerationResponse(
                generated_code="def hello_world():\n    print('Hello, World!')",
                language=CodeLanguage.PYTHON,
                mode=CodeGenerationMode.GENERATE,
                confidence=0.9,
                suggestions=["Add type hints", "Add docstring"],
                metrics={"lines": 2, "functions": 1},
                timestamp="2024-01-01T00:00:00",
                request_id="test-123"
            )
            mock_generate.return_value = mock_response

            arguments = {
                "prompt": "Create a hello world function",
                "language": "python",
                "mode": "generate"
            }

            result = await server._handle_generate_code(arguments)

            assert len(result) == 1
            assert result[0].type == "text"

            response_data = json.loads(result[0].text)
            assert response_data["generated_code"] == "def hello_world():\n    print('Hello, World!')"
            assert response_data["language"] == "python"
            assert response_data["confidence"] == 0.9

    @pytest.mark.asyncio
    async def test_analyze_code_python(self, server, sample_python_code):
        """Test Python code analysis."""
        arguments = {
            "code": sample_python_code,
            "language": "python",
            "detailed": True
        }

        result = await server._handle_analyze_code(arguments)

        assert len(result) == 1
        assert result[0].type == "text"

        analysis_data = json.loads(result[0].text)
        assert "complexity" in analysis_data
        assert "metrics" in analysis_data
        assert "issues" in analysis_data
        assert "suggestions" in analysis_data
        assert "quality_score" in analysis_data

        # Check metrics
        metrics = analysis_data["metrics"]
        assert metrics["functions"] == 2  # fibonacci and factorial
        assert metrics["lines_of_code"] > 0

    @pytest.mark.asyncio
    async def test_code_analysis_comprehensive(self, server):
        """Test comprehensive code analysis."""
        # Test with syntactically invalid code
        invalid_code = "def broken_function(\n    print('missing closing parenthesis')"

        analysis = await server._analyze_code_comprehensive(
            invalid_code,
            CodeLanguage.PYTHON,
            detailed=True
        )

        assert isinstance(analysis, CodeAnalysisResult)
        assert len(analysis.issues) > 0
        assert any(issue["type"] == "syntax" for issue in analysis.issues)
        assert analysis.quality_score < 1.0

    @pytest.mark.asyncio
    async def test_refactor_code(self, server, sample_python_code):
        """Test code refactoring."""
        with patch.object(server, '_refactor_code', new_callable=AsyncMock) as mock_refactor:
            mock_refactor.return_value = "# Refactored code\n" + sample_python_code

            arguments = {
                "code": sample_python_code,
                "language": "python",
                "refactor_type": "optimize",
                "target": "fibonacci"
            }

            result = await server._handle_refactor_code(arguments)

            assert len(result) == 1
            response_data = json.loads(result[0].text)
            assert "original_code" in response_data
            assert "refactored_code" in response_data
            assert response_data["refactor_type"] == "optimize"

    @pytest.mark.asyncio
    async def test_translate_code(self, server, sample_python_code):
        """Test code translation between languages."""
        with patch.object(server, '_translate_code', new_callable=AsyncMock) as mock_translate:
            mock_translate.return_value = """
function fibonacci(n) {
    if (n <= 1) {
        return n;
    }
    return fibonacci(n-1) + fibonacci(n-2);
}
"""

            arguments = {
                "code": sample_python_code,
                "source_language": "python",
                "target_language": "javascript",
                "preserve_comments": True
            }

            result = await server._handle_translate_code(arguments)

            assert len(result) == 1
            response_data = json.loads(result[0].text)
            assert response_data["source_language"] == "python"
            assert response_data["target_language"] == "javascript"
            assert "function fibonacci" in response_data["translated_code"]

    @pytest.mark.asyncio
    async def test_generate_tests(self, server, sample_python_code):
        """Test test generation functionality."""
        with patch.object(server, '_generate_tests', new_callable=AsyncMock) as mock_generate_tests:
            mock_test_code = """
import pytest

def test_fibonacci():
    assert fibonacci(0) == 0
    assert fibonacci(1) == 1
    assert fibonacci(5) == 5

def test_factorial():
    assert factorial(0) == 1
    assert factorial(5) == 120
"""
            mock_generate_tests.return_value = mock_test_code

            arguments = {
                "code": sample_python_code,
                "language": "python",
                "test_framework": "pytest",
                "coverage_target": 90
            }

            result = await server._handle_generate_tests(arguments)

            assert len(result) == 1
            response_data = json.loads(result[0].text)
            assert "test_code" in response_data
            assert "pytest" in response_data["test_code"]
            assert response_data["test_framework"] == "pytest"

    @pytest.mark.asyncio
    async def test_document_code(self, server, sample_python_code):
        """Test code documentation generation."""
        with patch.object(server, '_document_code', new_callable=AsyncMock) as mock_document:
            mock_documented_code = '''
def fibonacci(n):
    """
    Calculate the nth Fibonacci number using recursion.

    Args:
        n (int): The position in the Fibonacci sequence.

    Returns:
        int: The nth Fibonacci number.

    Example:
        >>> fibonacci(5)
        5
    """
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
'''
            mock_document.return_value = mock_documented_code

            arguments = {
                "code": sample_python_code,
                "language": "python",
                "doc_style": "google",
                "include_examples": True
            }

            result = await server._handle_document_code(arguments)

            assert len(result) == 1
            response_data = json.loads(result[0].text)
            assert "documented_code" in response_data
            assert "Args:" in response_data["documented_code"]
            assert "Returns:" in response_data["documented_code"]

    @pytest.mark.asyncio
    async def test_fix_code(self, server):
        """Test code fixing functionality."""
        broken_code = "def broken_func(\n    print('syntax error')"

        with patch.object(server, '_fix_code', new_callable=AsyncMock) as mock_fix:
            mock_fix.return_value = "def fixed_func():\n    print('syntax fixed')"

            arguments = {
                "code": broken_code,
                "language": "python",
                "error_message": "SyntaxError: unexpected EOF while parsing",
                "fix_type": "syntax"
            }

            result = await server._handle_fix_code(arguments)

            assert len(result) == 1
            response_data = json.loads(result[0].text)
            assert "fixed_code" in response_data
            assert response_data["fix_type"] == "syntax"

    @pytest.mark.asyncio
    async def test_server_status(self, server):
        """Test server status endpoint."""
        result = await server._handle_get_server_status({})

        assert len(result) == 1
        status_data = json.loads(result[0].text)

        assert status_data["server_name"] == "magic-mcp"
        assert status_data["status"] == "running"
        assert "ai_providers" in status_data
        assert "supported_languages" in status_data
        assert "supported_modes" in status_data
        assert "features" in status_data
        assert "timestamp" in status_data

    @pytest.mark.asyncio
    async def test_ai_provider_openai_integration(self, server):
        """Test OpenAI provider integration."""
        if AIProvider.OPENAI in server.ai_providers:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "def test_function():\n    pass"
            mock_client.chat.completions.create.return_value = mock_response

            server.ai_providers[AIProvider.OPENAI] = mock_client

            result = await server._generate_with_openai(
                mock_client,
                "You are a Python expert",
                "Generate a test function",
                CodeGenerationRequest(
                    prompt="test function",
                    language=CodeLanguage.PYTHON,
                    mode=CodeGenerationMode.GENERATE
                )
            )

            assert "def test_function" in result
            mock_client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_code_formatting_python(self, server):
        """Test Python code formatting."""
        unformatted_code = "def test(x,y):return x+y"

        formatted = await server._format_code(unformatted_code, CodeLanguage.PYTHON)

        # Should be formatted with proper spacing
        assert "def test(x, y):" in formatted
        assert "return x + y" in formatted

    @pytest.mark.asyncio
    async def test_error_handling(self, server):
        """Test error handling in tool calls."""
        # Test with invalid arguments
        arguments = {
            "prompt": "test",
            "language": "invalid_language",
            "mode": "generate"
        }

        result = await server._handle_generate_code(arguments)

        assert len(result) == 1
        assert "Error" in result[0].text

    @pytest.mark.asyncio
    async def test_quality_score_calculation(self, server):
        """Test code quality score calculation."""
        # Test with no issues
        score_perfect = server._calculate_quality_score([], {}, {})
        assert score_perfect == 1.0

        # Test with critical issues
        issues_critical = [{"severity": "critical"}]
        score_critical = server._calculate_quality_score(issues_critical, {}, {})
        assert score_critical == 0.7

        # Test with high complexity
        complexity_high = {"average_complexity": 15}
        score_complex = server._calculate_quality_score([], {}, complexity_high)
        assert score_complex == 0.8

    @pytest.mark.asyncio
    async def test_multiple_language_support(self, server):
        """Test support for multiple programming languages."""
        languages = [
            CodeLanguage.PYTHON,
            CodeLanguage.JAVASCRIPT,
            CodeLanguage.TYPESCRIPT,
            CodeLanguage.JAVA,
            CodeLanguage.CPP
        ]

        for language in languages:
            # Test basic analysis
            code = "// Sample code"
            analysis = await server._analyze_code_comprehensive(code, language, False)
            assert isinstance(analysis, CodeAnalysisResult)

    @pytest.mark.asyncio
    async def test_template_fallback(self, server):
        """Test template-based fallback generation."""
        request = CodeGenerationRequest(
            prompt="Create a function",
            language=CodeLanguage.PYTHON,
            mode=CodeGenerationMode.GENERATE
        )

        fallback_code = await server._generate_with_fallback(request)

        assert "def generated_function" in fallback_code
        assert "Create a function" in fallback_code

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, server):
        """Test handling multiple concurrent requests."""
        async def make_request():
            arguments = {
                "prompt": f"Create function {asyncio.current_task().get_name()}",
                "language": "python",
                "mode": "generate"
            }
            return await server._handle_generate_code(arguments)

        # Create multiple concurrent tasks
        tasks = [asyncio.create_task(make_request()) for _ in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All tasks should complete successfully
        assert len(results) == 5
        for result in results:
            assert not isinstance(result, Exception)

    @pytest.mark.asyncio
    async def test_code_metrics_analysis(self, server, sample_python_code):
        """Test detailed code metrics analysis."""
        analysis = await server._analyze_code_comprehensive(
            sample_python_code,
            CodeLanguage.PYTHON,
            detailed=True
        )

        assert "lines_of_code" in analysis.metrics
        assert "functions" in analysis.metrics
        assert analysis.metrics["functions"] == 2
        assert analysis.metrics["lines_of_code"] > 0

class TestCodeGenerationModels:
    """Test data models and enums."""

    def test_code_generation_request_creation(self):
        """Test CodeGenerationRequest creation."""
        request = CodeGenerationRequest(
            prompt="Create a function",
            language=CodeLanguage.PYTHON,
            mode=CodeGenerationMode.GENERATE
        )

        assert request.prompt == "Create a function"
        assert request.language == CodeLanguage.PYTHON
        assert request.mode == CodeGenerationMode.GENERATE
        assert request.max_tokens == 2000
        assert request.temperature == 0.7

    def test_code_generation_response_creation(self):
        """Test CodeGenerationResponse creation."""
        response = CodeGenerationResponse(
            generated_code="def test(): pass",
            language=CodeLanguage.PYTHON,
            mode=CodeGenerationMode.GENERATE,
            confidence=0.9,
            suggestions=["Add docstring"],
            metrics={"lines": 1},
            timestamp="2024-01-01T00:00:00",
            request_id="test-123"
        )

        assert response.generated_code == "def test(): pass"
        assert response.confidence == 0.9
        assert len(response.suggestions) == 1

    def test_code_analysis_result_creation(self):
        """Test CodeAnalysisResult creation."""
        result = CodeAnalysisResult(
            complexity={"cyclomatic": 5},
            metrics={"lines": 100},
            issues=[{"type": "warning", "message": "Test warning"}],
            suggestions=["Improve naming"],
            quality_score=0.8
        )

        assert result.quality_score == 0.8
        assert len(result.issues) == 1
        assert result.complexity["cyclomatic"] == 5

class TestIntegrationScenarios:
    """Integration test scenarios."""

    @pytest.mark.asyncio
    async def test_full_code_generation_workflow(self):
        """Test complete code generation workflow."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            server = MagicMCPServer()

            # Mock AI response
            with patch.object(server, '_generate_with_openai', new_callable=AsyncMock) as mock_ai:
                mock_ai.return_value = "def fibonacci(n):\n    return n if n <= 1 else fibonacci(n-1) + fibonacci(n-2)"

                arguments = {
                    "prompt": "Create a Fibonacci function",
                    "language": "python",
                    "mode": "generate",
                    "provider": "openai"
                }

                result = await server._handle_generate_code(arguments)
                response_data = json.loads(result[0].text)

                # Verify the complete workflow
                assert "fibonacci" in response_data["generated_code"]
                assert response_data["language"] == "python"
                assert response_data["confidence"] > 0
                assert isinstance(response_data["suggestions"], list)

    @pytest.mark.asyncio
    async def test_error_recovery_scenarios(self):
        """Test error recovery in various scenarios."""
        with patch.dict('os.environ', {}):  # No API keys
            server = MagicMCPServer()

            # Should fallback gracefully
            arguments = {
                "prompt": "Create a function",
                "language": "python",
                "mode": "generate"
            }

            result = await server._handle_generate_code(arguments)

            # Should not crash, should provide fallback response
            assert len(result) == 1
            assert result[0].type == "text"

if __name__ == "__main__":
    # Run tests with asyncio support
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
