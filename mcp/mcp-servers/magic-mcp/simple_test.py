#!/usr/bin/env python3
"""
Simple validation test for Magic MCP Server

A streamlined test to validate core functionality without complex fixtures.
Tests basic server initialization, tool registration, and core capabilities.
"""

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import patch, AsyncMock, Mock

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

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
    print("✅ Successfully imported Magic MCP Server components")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

async def test_server_initialization():
    """Test basic server initialization."""
    print("\n🔧 Testing server initialization...")

    try:
        with patch.dict('os.environ', {
            'OPENAI_API_KEY': 'test-key',
            'ANTHROPIC_API_KEY': 'test-key'
        }):
            server = MagicMCPServer()

            # Check basic attributes
            assert server.server.name == "magic-mcp"
            assert hasattr(server, 'ai_providers')
            assert hasattr(server, 'code_parsers')

            print("✅ Server initialization successful")
            return server

    except Exception as e:
        print(f"❌ Server initialization failed: {e}")
        raise

async def test_tool_registration(server):
    """Test tool registration."""
    print("\n🛠️  Testing tool registration...")

    try:
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

        for expected_tool in expected_tools:
            assert expected_tool in tool_names, f"Missing tool: {expected_tool}"

        print(f"✅ All {len(expected_tools)} tools registered successfully")
        return tools

    except Exception as e:
        print(f"❌ Tool registration test failed: {e}")
        raise

async def test_server_status(server):
    """Test server status endpoint."""
    print("\n📊 Testing server status...")

    try:
        result = await server._handle_get_server_status({})

        assert len(result) == 1
        status_data = json.loads(result[0].text)

        # Check required status fields
        required_fields = ["server_name", "status", "ai_providers", "supported_languages", "features"]
        for field in required_fields:
            assert field in status_data, f"Missing status field: {field}"

        assert status_data["server_name"] == "magic-mcp"
        assert status_data["status"] == "running"

        print("✅ Server status endpoint working correctly")
        return status_data

    except Exception as e:
        print(f"❌ Server status test failed: {e}")
        raise

async def test_code_analysis(server):
    """Test basic code analysis functionality."""
    print("\n🔍 Testing code analysis...")

    try:
        test_code = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
"""

        arguments = {
            "code": test_code,
            "language": "python",
            "detailed": True
        }

        result = await server._handle_analyze_code(arguments)

        assert len(result) == 1
        analysis_data = json.loads(result[0].text)

        # Check analysis structure
        required_fields = ["complexity", "metrics", "issues", "suggestions", "quality_score"]
        for field in required_fields:
            assert field in analysis_data, f"Missing analysis field: {field}"

        print("✅ Code analysis working correctly")
        return analysis_data

    except Exception as e:
        print(f"❌ Code analysis test failed: {e}")
        raise

async def test_code_generation_fallback(server):
    """Test code generation with fallback."""
    print("\n🎯 Testing code generation fallback...")

    try:
        # Test fallback generation (no AI providers)
        request = CodeGenerationRequest(
            prompt="Create a hello world function",
            language=CodeLanguage.PYTHON,
            mode=CodeGenerationMode.GENERATE
        )

        fallback_code = await server._generate_with_fallback(request)

        assert "def generated_function" in fallback_code
        assert "Create a hello world function" in fallback_code

        print("✅ Code generation fallback working correctly")
        return fallback_code

    except Exception as e:
        print(f"❌ Code generation fallback test failed: {e}")
        raise

async def test_code_formatting(server):
    """Test code formatting functionality."""
    print("\n🎨 Testing code formatting...")

    try:
        unformatted_code = "def test(x,y):return x+y"

        formatted = await server._format_code(unformatted_code, CodeLanguage.PYTHON)

        # Should be formatted with proper spacing
        assert "def test(x, y):" in formatted
        assert "return x + y" in formatted

        print("✅ Code formatting working correctly")
        return formatted

    except Exception as e:
        print(f"❌ Code formatting test failed: {e}")
        raise

async def test_quality_score_calculation(server):
    """Test quality score calculation."""
    print("\n📈 Testing quality score calculation...")

    try:
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

        print("✅ Quality score calculation working correctly")

    except Exception as e:
        print(f"❌ Quality score calculation test failed: {e}")
        raise

async def test_data_models():
    """Test data model creation."""
    print("\n📋 Testing data models...")

    try:
        # Test CodeGenerationRequest
        request = CodeGenerationRequest(
            prompt="Create a function",
            language=CodeLanguage.PYTHON,
            mode=CodeGenerationMode.GENERATE
        )

        assert request.prompt == "Create a function"
        assert request.language == CodeLanguage.PYTHON
        assert request.mode == CodeGenerationMode.GENERATE

        # Test CodeGenerationResponse
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

        # Test CodeAnalysisResult
        analysis = CodeAnalysisResult(
            complexity={"cyclomatic": 5},
            metrics={"lines": 100},
            issues=[{"type": "warning", "message": "Test warning"}],
            suggestions=["Improve naming"],
            quality_score=0.8
        )

        assert analysis.quality_score == 0.8
        assert len(analysis.issues) == 1

        print("✅ Data models working correctly")

    except Exception as e:
        print(f"❌ Data models test failed: {e}")
        raise

async def run_all_tests():
    """Run all validation tests."""
    print("🚀 Starting Magic MCP Server Simple Validation")
    print("=" * 50)

    try:
        # Initialize server
        server = await test_server_initialization()

        # Run tests
        await test_tool_registration(server)
        await test_server_status(server)
        await test_code_analysis(server)
        await test_code_generation_fallback(server)
        await test_code_formatting(server)
        await test_quality_score_calculation(server)
        await test_data_models()

        print("\n" + "=" * 50)
        print("🎉 ALL TESTS PASSED! Magic MCP Server is working correctly.")
        print("=" * 50)

        return True

    except Exception as e:
        print("\n" + "=" * 50)
        print(f"💥 VALIDATION FAILED: {e}")
        print("=" * 50)
        return False

def main():
    """Main entry point."""
    try:
        success = asyncio.run(run_all_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️  Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
