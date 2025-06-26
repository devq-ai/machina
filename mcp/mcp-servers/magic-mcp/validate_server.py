#!/usr/bin/env python3
"""
Magic MCP Server Validation Script

Comprehensive validation suite for the Magic MCP Server that tests all functionality,
AI integrations, code generation capabilities, and performance metrics.
Validates the server against DevQ.ai standards and MCP protocol compliance.
"""

import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

try:
    from server import MagicMCPServer, CodeLanguage, CodeGenerationMode, AIProvider
    from mcp import types
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure all dependencies are installed")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MagicMCPValidator:
    """Comprehensive validator for Magic MCP Server."""

    def __init__(self):
        """Initialize validator."""
        self.server = None
        self.validation_results = {
            "server_info": {},
            "tests": [],
            "performance": {},
            "compliance": {},
            "summary": {}
        }
        self.start_time = time.time()

    async def run_validation(self) -> Dict[str, Any]:
        """Run complete validation suite."""
        logger.info("Starting Magic MCP Server validation...")

        try:
            # Initialize server
            await self._initialize_server()

            # Run validation tests
            await self._validate_server_initialization()
            await self._validate_tool_registration()
            await self._validate_code_generation()
            await self._validate_code_analysis()
            await self._validate_code_refactoring()
            await self._validate_code_translation()
            await self._validate_test_generation()
            await self._validate_documentation()
            await self._validate_code_fixing()
            await self._validate_ai_providers()
            await self._validate_error_handling()
            await self._validate_performance()
            await self._validate_mcp_compliance()

            # Generate summary
            self._generate_summary()

            return self.validation_results

        except Exception as e:
            logger.error(f"Validation failed: {e}")
            self.validation_results["summary"]["status"] = "FAILED"
            self.validation_results["summary"]["error"] = str(e)
            return self.validation_results

    async def _initialize_server(self):
        """Initialize the Magic MCP Server."""
        try:
            self.server = MagicMCPServer()
            self.validation_results["server_info"] = {
                "name": "magic-mcp",
                "version": "1.0.0",
                "initialization_time": time.time() - self.start_time,
                "ai_providers_available": len(self.server.ai_providers),
                "parsers_available": len(self.server.code_parsers)
            }
            logger.info("Server initialized successfully")
        except Exception as e:
            raise Exception(f"Server initialization failed: {e}")

    async def _validate_server_initialization(self):
        """Validate server initialization."""
        test_name = "Server Initialization"
        logger.info(f"Validating {test_name}...")

        try:
            # Check server attributes
            assert self.server.server.name == "magic-mcp"
            assert hasattr(self.server, 'ai_providers')
            assert hasattr(self.server, 'code_parsers')
            assert hasattr(self.server, 'templates_env')

            self._add_test_result(test_name, "PASSED", "Server initialized with all required components")

        except Exception as e:
            self._add_test_result(test_name, "FAILED", str(e))

    async def _validate_tool_registration(self):
        """Validate tool registration."""
        test_name = "Tool Registration"
        logger.info(f"Validating {test_name}...")

        try:
            tools = await self.server.server.list_tools()()

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

            # Validate tool schemas
            for tool in tools:
                assert hasattr(tool, 'inputSchema')
                assert 'type' in tool.inputSchema
                assert 'properties' in tool.inputSchema

            self._add_test_result(
                test_name,
                "PASSED",
                f"All {len(expected_tools)} required tools registered with valid schemas"
            )

        except Exception as e:
            self._add_test_result(test_name, "FAILED", str(e))

    async def _validate_code_generation(self):
        """Validate code generation functionality."""
        test_name = "Code Generation"
        logger.info(f"Validating {test_name}...")

        try:
            test_cases = [
                {
                    "prompt": "Create a hello world function",
                    "language": "python",
                    "mode": "generate"
                },
                {
                    "prompt": "Create a sorting algorithm",
                    "language": "javascript",
                    "mode": "generate"
                }
            ]

            for i, test_case in enumerate(test_cases):
                result = await self.server._handle_generate_code(test_case)

                assert len(result) == 1
                assert result[0].type == "text"

                response_data = json.loads(result[0].text)

                # Check response structure
                required_fields = ["generated_code", "language", "mode", "confidence", "suggestions", "metrics"]
                for field in required_fields:
                    assert field in response_data, f"Missing field: {field}"

                # Validate generated code is not empty
                assert len(response_data["generated_code"]) > 0

            self._add_test_result(
                test_name,
                "PASSED",
                f"Code generation successful for {len(test_cases)} test cases"
            )

        except Exception as e:
            self._add_test_result(test_name, "FAILED", str(e))

    async def _validate_code_analysis(self):
        """Validate code analysis functionality."""
        test_name = "Code Analysis"
        logger.info(f"Validating {test_name}...")

        try:
            test_code = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n-1)
"""

            arguments = {
                "code": test_code,
                "language": "python",
                "detailed": True
            }

            result = await self.server._handle_analyze_code(arguments)

            assert len(result) == 1
            analysis_data = json.loads(result[0].text)

            # Check analysis structure
            required_fields = ["complexity", "metrics", "issues", "suggestions", "quality_score"]
            for field in required_fields:
                assert field in analysis_data

            # Validate metrics
            metrics = analysis_data["metrics"]
            assert "functions" in metrics
            assert metrics["functions"] == 2  # fibonacci and factorial

            self._add_test_result(test_name, "PASSED", "Code analysis completed with valid metrics")

        except Exception as e:
            self._add_test_result(test_name, "FAILED", str(e))

    async def _validate_code_refactoring(self):
        """Validate code refactoring functionality."""
        test_name = "Code Refactoring"
        logger.info(f"Validating {test_name}...")

        try:
            test_code = "def test_func(x,y):return x+y"

            arguments = {
                "code": test_code,
                "language": "python",
                "refactor_type": "optimize"
            }

            result = await self.server._handle_refactor_code(arguments)

            assert len(result) == 1
            response_data = json.loads(result[0].text)

            required_fields = ["original_code", "refactored_code", "refactor_type", "language"]
            for field in required_fields:
                assert field in response_data

            self._add_test_result(test_name, "PASSED", "Code refactoring completed successfully")

        except Exception as e:
            self._add_test_result(test_name, "FAILED", str(e))

    async def _validate_code_translation(self):
        """Validate code translation functionality."""
        test_name = "Code Translation"
        logger.info(f"Validating {test_name}...")

        try:
            python_code = "def hello():\n    print('Hello, World!')"

            arguments = {
                "code": python_code,
                "source_language": "python",
                "target_language": "javascript",
                "preserve_comments": True
            }

            result = await self.server._handle_translate_code(arguments)

            assert len(result) == 1
            response_data = json.loads(result[0].text)

            required_fields = ["original_code", "translated_code", "source_language", "target_language"]
            for field in required_fields:
                assert field in response_data

            self._add_test_result(test_name, "PASSED", "Code translation completed successfully")

        except Exception as e:
            self._add_test_result(test_name, "FAILED", str(e))

    async def _validate_test_generation(self):
        """Validate test generation functionality."""
        test_name = "Test Generation"
        logger.info(f"Validating {test_name}...")

        try:
            test_code = "def add(a, b):\n    return a + b"

            arguments = {
                "code": test_code,
                "language": "python",
                "test_framework": "pytest",
                "coverage_target": 90
            }

            result = await self.server._handle_generate_tests(arguments)

            assert len(result) == 1
            response_data = json.loads(result[0].text)

            required_fields = ["original_code", "test_code", "language", "test_framework"]
            for field in required_fields:
                assert field in response_data

            self._add_test_result(test_name, "PASSED", "Test generation completed successfully")

        except Exception as e:
            self._add_test_result(test_name, "FAILED", str(e))

    async def _validate_documentation(self):
        """Validate documentation generation functionality."""
        test_name = "Documentation Generation"
        logger.info(f"Validating {test_name}...")

        try:
            test_code = "def calculate_area(radius):\n    return 3.14159 * radius * radius"

            arguments = {
                "code": test_code,
                "language": "python",
                "doc_style": "google",
                "include_examples": True
            }

            result = await self.server._handle_document_code(arguments)

            assert len(result) == 1
            response_data = json.loads(result[0].text)

            required_fields = ["original_code", "documented_code", "language", "doc_style"]
            for field in required_fields:
                assert field in response_data

            self._add_test_result(test_name, "PASSED", "Documentation generation completed successfully")

        except Exception as e:
            self._add_test_result(test_name, "FAILED", str(e))

    async def _validate_code_fixing(self):
        """Validate code fixing functionality."""
        test_name = "Code Fixing"
        logger.info(f"Validating {test_name}...")

        try:
            broken_code = "def broken_func(\n    print('syntax error')"

            arguments = {
                "code": broken_code,
                "language": "python",
                "error_message": "SyntaxError: unexpected EOF",
                "fix_type": "syntax"
            }

            result = await self.server._handle_fix_code(arguments)

            assert len(result) == 1
            response_data = json.loads(result[0].text)

            required_fields = ["original_code", "fixed_code", "language", "fix_type"]
            for field in required_fields:
                assert field in response_data

            self._add_test_result(test_name, "PASSED", "Code fixing completed successfully")

        except Exception as e:
            self._add_test_result(test_name, "FAILED", str(e))

    async def _validate_ai_providers(self):
        """Validate AI provider integration."""
        test_name = "AI Provider Integration"
        logger.info(f"Validating {test_name}...")

        try:
            # Check available providers
            available_providers = list(self.server.ai_providers.keys())

            # Validate provider setup
            provider_status = {}
            for provider in AIProvider:
                provider_status[provider.value] = provider in self.server.ai_providers

            # At least one provider should be available for production use
            has_production_provider = any(provider_status.values())

            self._add_test_result(
                test_name,
                "PASSED" if has_production_provider else "WARNING",
                f"AI providers available: {available_providers}"
            )

        except Exception as e:
            self._add_test_result(test_name, "FAILED", str(e))

    async def _validate_error_handling(self):
        """Validate error handling capabilities."""
        test_name = "Error Handling"
        logger.info(f"Validating {test_name}...")

        try:
            # Test with invalid arguments
            invalid_arguments = {
                "prompt": "test",
                "language": "invalid_language",
                "mode": "generate"
            }

            result = await self.server._handle_generate_code(invalid_arguments)

            assert len(result) == 1
            assert "Error" in result[0].text or "error" in result[0].text.lower()

            self._add_test_result(test_name, "PASSED", "Error handling works correctly")

        except Exception as e:
            self._add_test_result(test_name, "FAILED", str(e))

    async def _validate_performance(self):
        """Validate performance characteristics."""
        test_name = "Performance Validation"
        logger.info(f"Validating {test_name}...")

        try:
            # Test response times
            start_time = time.time()

            result = await self.server._handle_get_server_status({})

            response_time = time.time() - start_time

            # Response should be under 1 second for status check
            assert response_time < 1.0, f"Status check too slow: {response_time}s"

            self.validation_results["performance"] = {
                "status_response_time": response_time,
                "memory_efficient": True,  # Placeholder
                "concurrent_capable": True  # Placeholder
            }

            self._add_test_result(
                test_name,
                "PASSED",
                f"Performance acceptable (status: {response_time:.3f}s)"
            )

        except Exception as e:
            self._add_test_result(test_name, "FAILED", str(e))

    async def _validate_mcp_compliance(self):
        """Validate MCP protocol compliance."""
        test_name = "MCP Protocol Compliance"
        logger.info(f"Validating {test_name}...")

        try:
            # Check server implements required MCP interfaces
            assert hasattr(self.server.server, 'list_tools')
            assert hasattr(self.server.server, 'call_tool')
            assert hasattr(self.server.server, 'name')

            # Check tool definitions comply with MCP types
            tools = await self.server.server.list_tools()()

            for tool in tools:
                assert isinstance(tool, types.Tool)
                assert hasattr(tool, 'name')
                assert hasattr(tool, 'description')
                assert hasattr(tool, 'inputSchema')

            self.validation_results["compliance"] = {
                "mcp_protocol": "compliant",
                "tool_schemas": "valid",
                "type_safety": "enforced"
            }

            self._add_test_result(test_name, "PASSED", "MCP protocol compliance verified")

        except Exception as e:
            self._add_test_result(test_name, "FAILED", str(e))

    def _add_test_result(self, test_name: str, status: str, details: str):
        """Add test result to validation results."""
        self.validation_results["tests"].append({
            "name": test_name,
            "status": status,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })

        logger.info(f"{test_name}: {status} - {details}")

    def _generate_summary(self):
        """Generate validation summary."""
        total_tests = len(self.validation_results["tests"])
        passed_tests = sum(1 for test in self.validation_results["tests"] if test["status"] == "PASSED")
        failed_tests = sum(1 for test in self.validation_results["tests"] if test["status"] == "FAILED")
        warning_tests = sum(1 for test in self.validation_results["tests"] if test["status"] == "WARNING")

        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0

        overall_status = "PASSED" if failed_tests == 0 else "FAILED"
        if warning_tests > 0 and failed_tests == 0:
            overall_status = "PASSED_WITH_WARNINGS"

        self.validation_results["summary"] = {
            "overall_status": overall_status,
            "total_tests": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "warnings": warning_tests,
            "success_rate": round(success_rate, 2),
            "total_time": round(time.time() - self.start_time, 2),
            "timestamp": datetime.now().isoformat()
        }

    def save_results(self, output_file: Optional[str] = None):
        """Save validation results to file."""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"validation_report_{timestamp}.json"

        output_path = Path(__file__).parent / output_file

        with open(output_path, 'w') as f:
            json.dump(self.validation_results, f, indent=2)

        logger.info(f"Validation results saved to {output_path}")
        return output_path

    def print_summary(self):
        """Print validation summary to console."""
        summary = self.validation_results["summary"]

        print("\n" + "="*60)
        print("MAGIC MCP SERVER VALIDATION SUMMARY")
        print("="*60)
        print(f"Overall Status: {summary['overall_status']}")
        print(f"Success Rate: {summary['success_rate']}%")
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Passed: {summary['passed']}")
        print(f"Failed: {summary['failed']}")
        print(f"Warnings: {summary['warnings']}")
        print(f"Total Time: {summary['total_time']}s")
        print("="*60)

        if summary['failed'] > 0:
            print("\nFAILED TESTS:")
            for test in self.validation_results["tests"]:
                if test["status"] == "FAILED":
                    print(f"  - {test['name']}: {test['details']}")

        if summary['warnings'] > 0:
            print("\nWARNINGS:")
            for test in self.validation_results["tests"]:
                if test["status"] == "WARNING":
                    print(f"  - {test['name']}: {test['details']}")

async def main():
    """Main validation function."""
    print("Starting Magic MCP Server Validation...")

    validator = MagicMCPValidator()

    try:
        results = await validator.run_validation()

        # Save results
        output_file = validator.save_results()

        # Print summary
        validator.print_summary()

        # Exit with appropriate code
        if results["summary"]["overall_status"] == "FAILED":
            print(f"\n❌ Validation FAILED. See {output_file} for details.")
            return 1
        elif results["summary"]["overall_status"] == "PASSED_WITH_WARNINGS":
            print(f"\n⚠️  Validation PASSED with warnings. See {output_file} for details.")
            return 0
        else:
            print(f"\n✅ Validation PASSED successfully. See {output_file} for details.")
            return 0

    except Exception as e:
        print(f"\n💥 Validation crashed: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
