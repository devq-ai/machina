#!/usr/bin/env python3
"""
Minimal test for Magic MCP Server

Basic functionality test to verify the server works correctly.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

def test_imports():
    """Test that all imports work correctly."""
    print("Testing imports...")

    try:
        from server import (
            MagicMCPServer,
            CodeLanguage,
            CodeGenerationMode,
            AIProvider
        )
        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def test_enums():
    """Test that enums are working correctly."""
    print("Testing enums...")

    try:
        from server import CodeLanguage, CodeGenerationMode, AIProvider

        # Test CodeLanguage enum
        assert CodeLanguage.PYTHON == "python"
        assert CodeLanguage.JAVASCRIPT == "javascript"

        # Test CodeGenerationMode enum
        assert CodeGenerationMode.GENERATE == "generate"
        assert CodeGenerationMode.ANALYZE == "analyze"

        # Test AIProvider enum
        assert AIProvider.OPENAI == "openai"
        assert AIProvider.ANTHROPIC == "anthropic"

        print("✅ All enums working correctly")
        return True
    except Exception as e:
        print(f"❌ Enum test failed: {e}")
        return False

async def test_server_creation():
    """Test basic server creation."""
    print("Testing server creation...")

    try:
        from server import MagicMCPServer

        # Create server without API keys (should still work for basic functionality)
        server = MagicMCPServer()

        # Check basic attributes
        assert hasattr(server, 'server')
        assert hasattr(server, 'ai_providers')
        assert hasattr(server, 'code_parsers')
        assert server.server.name == "magic-mcp"

        print("✅ Server creation successful")
        return True
    except Exception as e:
        print(f"❌ Server creation failed: {e}")
        return False

async def test_data_models():
    """Test data model creation."""
    print("Testing data models...")

    try:
        from server import (
            CodeGenerationRequest,
            CodeGenerationResponse,
            CodeAnalysisResult,
            CodeLanguage,
            CodeGenerationMode
        )

        # Test CodeGenerationRequest
        request = CodeGenerationRequest(
            prompt="test prompt",
            language=CodeLanguage.PYTHON,
            mode=CodeGenerationMode.GENERATE
        )
        assert request.prompt == "test prompt"
        assert request.language == CodeLanguage.PYTHON

        # Test CodeGenerationResponse
        response = CodeGenerationResponse(
            generated_code="def test(): pass",
            language=CodeLanguage.PYTHON,
            mode=CodeGenerationMode.GENERATE,
            confidence=0.9,
            suggestions=["test"],
            metrics={"lines": 1},
            timestamp="2024-01-01T00:00:00",
            request_id="test"
        )
        assert response.generated_code == "def test(): pass"

        # Test CodeAnalysisResult
        analysis = CodeAnalysisResult(
            complexity={},
            metrics={},
            issues=[],
            suggestions=[],
            quality_score=1.0
        )
        assert analysis.quality_score == 1.0

        print("✅ Data models working correctly")
        return True
    except Exception as e:
        print(f"❌ Data model test failed: {e}")
        return False

async def test_basic_methods():
    """Test basic server methods."""
    print("Testing basic server methods...")

    try:
        from server import MagicMCPServer, CodeLanguage

        server = MagicMCPServer()

        # Test quality score calculation
        score = server._calculate_quality_score([], {}, {})
        assert score == 1.0

        # Test format code (should not crash)
        formatted = await server._format_code("def test():pass", CodeLanguage.PYTHON)
        assert "def test():" in formatted

        print("✅ Basic methods working correctly")
        return True
    except Exception as e:
        print(f"❌ Basic methods test failed: {e}")
        return False

async def run_all_tests():
    """Run all minimal tests."""
    print("🚀 Starting Magic MCP Server Minimal Tests")
    print("=" * 50)

    tests = [
        test_imports,
        test_enums,
        test_server_creation,
        test_data_models,
        test_basic_methods
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            if asyncio.iscoroutinefunction(test):
                result = await test()
            else:
                result = test()

            if result:
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")

    print("\n" + "=" * 50)
    print(f"📊 Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 ALL MINIMAL TESTS PASSED!")
        print("✅ Magic MCP Server basic functionality is working")
    else:
        print(f"⚠️  {total - passed} tests failed")
        print("❌ Some basic functionality issues detected")

    print("=" * 50)
    return passed == total

def main():
    """Main entry point."""
    try:
        success = asyncio.run(run_all_tests())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"💥 Test runner crashed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
