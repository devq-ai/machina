#!/usr/bin/env python3
"""
PyTest MCP Server
Testing framework integration using FastMCP framework.
"""

import asyncio
import json
import os
import subprocess
import tempfile
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
    import aiofiles
    PYTEST_DEPS_AVAILABLE = True
except ImportError:
    PYTEST_DEPS_AVAILABLE = False
    BaseModel = object
    def Field(*args, **kwargs):
        return None
    aiofiles = None


class TestResult(BaseModel if PYTEST_DEPS_AVAILABLE else object):
    """Test result model"""
    test_name: str = Field(..., description="Test name")
    status: str = Field(..., description="Test status (passed, failed, skipped)")
    duration: float = Field(..., description="Test duration in seconds")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    file_path: str = Field(..., description="Test file path")
    line_number: Optional[int] = Field(None, description="Line number")


class TestSuite(BaseModel if PYTEST_DEPS_AVAILABLE else object):
    """Test suite model"""
    name: str = Field(..., description="Test suite name")
    path: str = Field(..., description="Test suite path")
    total_tests: int = Field(0, description="Total number of tests")
    passed: int = Field(0, description="Number of passed tests")
    failed: int = Field(0, description="Number of failed tests")
    skipped: int = Field(0, description="Number of skipped tests")
    duration: float = Field(0.0, description="Total duration")
    coverage: Optional[float] = Field(None, description="Code coverage percentage")


class PyTestMCP:
    """
    PyTest MCP Server using FastMCP framework

    Provides comprehensive testing framework operations including:
    - Test discovery and execution
    - Test result analysis and reporting
    - Code coverage measurement
    - Test suite management
    - Continuous testing integration
    - Test data generation
    - Performance testing support
    """

    def __init__(self):
        self.mcp = FastMCP("pytest-mcp", version="1.0.0", description="Testing framework integration with PyTest")
        self.test_results: Dict[str, List[TestResult]] = {}
        self.test_suites: Dict[str, TestSuite] = {}
        self.default_python = os.getenv("PYTEST_PYTHON", "python3")
        self.pytest_args = os.getenv("PYTEST_ARGS", "-v --tb=short")
        self._setup_tools()

    def _parse_pytest_output(self, output: str, error_output: str) -> Dict[str, Any]:
        """Parse pytest output to extract test results"""
        try:
            lines = output.split('\n')
            results = []
            summary = {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "duration": 0.0
            }

            current_test = None
            for line in lines:
                line = line.strip()

                # Parse test results
                if "::" in line and (" PASSED" in line or " FAILED" in line or " SKIPPED" in line):
                    parts = line.split(" ")
                    if len(parts) >= 2:
                        test_path = parts[0]
                        status = parts[1].lower()

                        # Extract file and test name
                        if "::" in test_path:
                            file_part, test_part = test_path.split("::", 1)
                            test_name = test_part
                            file_path = file_part
                        else:
                            test_name = test_path
                            file_path = test_path

                        result = {
                            "test_name": test_name,
                            "status": status,
                            "duration": 0.0,
                            "error_message": None,
                            "file_path": file_path,
                            "line_number": None
                        }

                        results.append(result)
                        summary["total"] += 1
                        summary[status] = summary.get(status, 0) + 1

                # Parse summary line
                if "passed" in line and "failed" in line:
                    # Extract numbers from summary
                    import re
                    numbers = re.findall(r'(\d+)\s+(passed|failed|skipped)', line)
                    for count, status in numbers:
                        summary[status] = int(count)

                # Parse duration
                if "seconds" in line and "=" in line:
                    import re
                    duration_match = re.search(r'([\d.]+)\s*seconds?', line)
                    if duration_match:
                        summary["duration"] = float(duration_match.group(1))

            return {
                "results": results,
                "summary": summary,
                "raw_output": output,
                "error_output": error_output
            }

        except Exception as e:
            return {
                "results": [],
                "summary": {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "duration": 0.0},
                "raw_output": output,
                "error_output": error_output,
                "parse_error": str(e)
            }

    def _generate_test_template(self, test_type: str, module_name: str) -> str:
        """Generate test template based on type"""
        templates = {
            "unit": f'''"""
Unit tests for {module_name}
"""

import pytest
from unittest.mock import Mock, patch
import sys
import os

# Add source directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from {module_name} import *
except ImportError:
    # Mock the module if it doesn't exist yet
    pass


class Test{module_name.title()}:
    """Unit tests for {module_name}"""

    def test_example_function(self):
        """Test example function"""
        # TODO: Implement test
        assert True

    def test_with_mock(self):
        """Test with mock objects"""
        mock_obj = Mock()
        mock_obj.method.return_value = "test"
        assert mock_obj.method() == "test"

    @pytest.mark.parametrize("input_val,expected", [
        (1, 2),
        (2, 3),
        (3, 4),
    ])
    def test_parametrized(self, input_val, expected):
        """Parametrized test example"""
        # TODO: Implement parametrized test
        assert input_val + 1 == expected

    def test_exception_handling(self):
        """Test exception handling"""
        with pytest.raises(ValueError):
            # TODO: Code that should raise ValueError
            raise ValueError("Test exception")
''',
            "integration": f'''"""
Integration tests for {module_name}
"""

import pytest
import asyncio
import tempfile
import os


class Test{module_name.title()}Integration:
    """Integration tests for {module_name}"""

    @pytest.fixture
    def temp_dir(self):
        """Temporary directory fixture"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def sample_data(self):
        """Sample data fixture"""
        return {{"key": "value", "number": 42}}

    def test_integration_example(self, temp_dir, sample_data):
        """Integration test example"""
        # TODO: Implement integration test
        assert os.path.exists(temp_dir)
        assert sample_data["key"] == "value"

    @pytest.mark.asyncio
    async def test_async_integration(self):
        """Async integration test"""
        # TODO: Implement async test
        result = await asyncio.sleep(0.1, result="test")
        assert result == "test"
''',
            "api": f'''"""
API tests for {module_name}
"""

import pytest
import httpx
import json


class Test{module_name.title()}API:
    """API tests for {module_name}"""

    @pytest.fixture
    def client(self):
        """HTTP client fixture"""
        return httpx.AsyncClient()

    @pytest.fixture
    def base_url(self):
        """Base URL fixture"""
        return "http://localhost:8000"

    @pytest.mark.asyncio
    async def test_health_endpoint(self, client, base_url):
        """Test health endpoint"""
        response = await client.get(f"{{base_url}}/health")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_api_endpoint(self, client, base_url):
        """Test API endpoint"""
        # TODO: Implement API test
        response = await client.get(f"{{base_url}}/api/v1/test")
        # assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_post_endpoint(self, client, base_url):
        """Test POST endpoint"""
        data = {{"test": "data"}}
        response = await client.post(
            f"{{base_url}}/api/v1/test",
            json=data
        )
        # TODO: Add assertions
        # assert response.status_code == 201
'''
        }

        return templates.get(test_type, templates["unit"])

    def _setup_tools(self):
        """Setup PyTest MCP tools"""

        @self.mcp.tool(
            name="run_tests",
            description="Run pytest tests",
            input_schema={
                "type": "object",
                "properties": {
                    "test_path": {"type": "string", "description": "Path to test file or directory"},
                    "pattern": {"type": "string", "description": "Test name pattern to match"},
                    "markers": {"type": "string", "description": "Pytest markers to run"},
                    "coverage": {"type": "boolean", "description": "Enable coverage reporting", "default": False},
                    "verbose": {"type": "boolean", "description": "Verbose output", "default": True}
                }
            }
        )
        async def run_tests(test_path: str = ".", pattern: str = None, markers: str = None,
                          coverage: bool = False, verbose: bool = True) -> Dict[str, Any]:
            """Run pytest tests"""
            try:
                # Build pytest command
                cmd = [self.default_python, "-m", "pytest"]

                if verbose:
                    cmd.append("-v")

                if pattern:
                    cmd.extend(["-k", pattern])

                if markers:
                    cmd.extend(["-m", markers])

                if coverage:
                    cmd.extend(["--cov=.", "--cov-report=term", "--cov-report=json"])

                cmd.append(test_path)

                # Run pytest
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    cwd=os.getcwd()
                )

                # Parse results
                parsed = self._parse_pytest_output(result.stdout, result.stderr)

                # Read coverage report if available
                coverage_data = None
                if coverage and os.path.exists("coverage.json"):
                    try:
                        with open("coverage.json", "r") as f:
                            coverage_data = json.load(f)
                    except Exception:
                        pass

                return {
                    "status": "completed",
                    "exit_code": result.returncode,
                    "test_path": test_path,
                    "summary": parsed["summary"],
                    "results": parsed["results"],
                    "coverage": coverage_data,
                    "duration": parsed["summary"]["duration"],
                    "success": result.returncode == 0
                }

            except Exception as e:
                logfire.error(f"Failed to run tests: {str(e)}")
                return {"error": f"Test execution failed: {str(e)}"}

        @self.mcp.tool(
            name="discover_tests",
            description="Discover available tests",
            input_schema={
                "type": "object",
                "properties": {
                    "test_path": {"type": "string", "description": "Path to search for tests", "default": "."},
                    "pattern": {"type": "string", "description": "File pattern for test discovery", "default": "test_*.py"}
                }
            }
        )
        async def discover_tests(test_path: str = ".", pattern: str = "test_*.py") -> Dict[str, Any]:
            """Discover available tests"""
            try:
                # Run pytest in collect-only mode
                cmd = [
                    self.default_python, "-m", "pytest",
                    "--collect-only", "-q",
                    test_path
                ]

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    cwd=os.getcwd()
                )

                discovered_tests = []
                test_files = set()

                for line in result.stdout.split('\n'):
                    line = line.strip()
                    if "::" in line and not line.startswith("="):
                        parts = line.split("::")
                        if len(parts) >= 2:
                            file_path = parts[0]
                            test_name = "::".join(parts[1:])

                            test_files.add(file_path)
                            discovered_tests.append({
                                "file_path": file_path,
                                "test_name": test_name,
                                "full_name": line
                            })

                return {
                    "status": "discovered",
                    "test_path": test_path,
                    "total_tests": len(discovered_tests),
                    "test_files": list(test_files),
                    "tests": discovered_tests
                }

            except Exception as e:
                logfire.error(f"Failed to discover tests: {str(e)}")
                return {"error": f"Test discovery failed: {str(e)}"}

        @self.mcp.tool(
            name="generate_test_file",
            description="Generate a test file template",
            input_schema={
                "type": "object",
                "properties": {
                    "module_name": {"type": "string", "description": "Module name to test"},
                    "test_type": {"type": "string", "description": "Type of test", "enum": ["unit", "integration", "api"], "default": "unit"},
                    "output_path": {"type": "string", "description": "Output file path"}
                },
                "required": ["module_name", "output_path"]
            }
        )
        async def generate_test_file(module_name: str, test_type: str = "unit", output_path: str = None) -> Dict[str, Any]:
            """Generate a test file template"""
            try:
                if not output_path:
                    output_path = f"test_{module_name}.py"

                # Generate test content
                test_content = self._generate_test_template(test_type, module_name)

                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)

                # Write test file
                if aiofiles:
                    async with aiofiles.open(output_path, 'w') as f:
                        await f.write(test_content)
                else:
                    with open(output_path, 'w') as f:
                        f.write(test_content)

                return {
                    "status": "generated",
                    "module_name": module_name,
                    "test_type": test_type,
                    "output_path": output_path,
                    "content_length": len(test_content)
                }

            except Exception as e:
                logfire.error(f"Failed to generate test file: {str(e)}")
                return {"error": f"Test file generation failed: {str(e)}"}

        @self.mcp.tool(
            name="run_coverage",
            description="Run code coverage analysis",
            input_schema={
                "type": "object",
                "properties": {
                    "source_path": {"type": "string", "description": "Source code path", "default": "src"},
                    "test_path": {"type": "string", "description": "Test path", "default": "tests"},
                    "format": {"type": "string", "description": "Coverage report format", "enum": ["term", "html", "xml", "json"], "default": "term"}
                }
            }
        )
        async def run_coverage(source_path: str = "src", test_path: str = "tests", format: str = "term") -> Dict[str, Any]:
            """Run code coverage analysis"""
            try:
                # Build coverage command
                cmd = [
                    self.default_python, "-m", "pytest",
                    f"--cov={source_path}",
                    f"--cov-report={format}",
                    test_path
                ]

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    cwd=os.getcwd()
                )

                # Parse coverage data
                coverage_data = None
                if format == "json" and os.path.exists("coverage.json"):
                    try:
                        with open("coverage.json", "r") as f:
                            coverage_data = json.load(f)
                    except Exception:
                        pass

                return {
                    "status": "completed",
                    "source_path": source_path,
                    "test_path": test_path,
                    "format": format,
                    "exit_code": result.returncode,
                    "output": result.stdout,
                    "coverage_data": coverage_data,
                    "success": result.returncode == 0
                }

            except Exception as e:
                logfire.error(f"Failed to run coverage: {str(e)}")
                return {"error": f"Coverage analysis failed: {str(e)}"}

        @self.mcp.tool(
            name="run_specific_test",
            description="Run a specific test by name",
            input_schema={
                "type": "object",
                "properties": {
                    "test_name": {"type": "string", "description": "Specific test name to run"},
                    "file_path": {"type": "string", "description": "Test file path"},
                    "capture_output": {"type": "boolean", "description": "Capture test output", "default": True}
                },
                "required": ["test_name"]
            }
        )
        async def run_specific_test(test_name: str, file_path: str = None, capture_output: bool = True) -> Dict[str, Any]:
            """Run a specific test by name"""
            try:
                # Build pytest command for specific test
                if file_path:
                    test_target = f"{file_path}::{test_name}"
                else:
                    test_target = f"-k {test_name}"

                cmd = [self.default_python, "-m", "pytest", "-v"]

                if file_path:
                    cmd.append(test_target)
                else:
                    cmd.extend(["-k", test_name])

                if capture_output:
                    cmd.append("-s")

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    cwd=os.getcwd()
                )

                # Parse results
                parsed = self._parse_pytest_output(result.stdout, result.stderr)

                return {
                    "status": "completed",
                    "test_name": test_name,
                    "file_path": file_path,
                    "exit_code": result.returncode,
                    "summary": parsed["summary"],
                    "results": parsed["results"],
                    "output": result.stdout if capture_output else None,
                    "success": result.returncode == 0
                }

            except Exception as e:
                logfire.error(f"Failed to run specific test: {str(e)}")
                return {"error": f"Specific test execution failed: {str(e)}"}

        @self.mcp.tool(
            name="install_pytest_plugins",
            description="Install pytest plugins",
            input_schema={
                "type": "object",
                "properties": {
                    "plugins": {"type": "array", "items": {"type": "string"}, "description": "List of pytest plugins to install"}
                },
                "required": ["plugins"]
            }
        )
        async def install_pytest_plugins(plugins: List[str]) -> Dict[str, Any]:
            """Install pytest plugins"""
            try:
                installed = []
                failed = []

                for plugin in plugins:
                    try:
                        result = subprocess.run(
                            [self.default_python, "-m", "pip", "install", plugin],
                            capture_output=True,
                            text=True
                        )

                        if result.returncode == 0:
                            installed.append(plugin)
                        else:
                            failed.append({"plugin": plugin, "error": result.stderr})
                    except Exception as e:
                        failed.append({"plugin": plugin, "error": str(e)})

                return {
                    "status": "completed",
                    "installed": installed,
                    "failed": failed,
                    "success_count": len(installed),
                    "failure_count": len(failed)
                }

            except Exception as e:
                logfire.error(f"Failed to install plugins: {str(e)}")
                return {"error": f"Plugin installation failed: {str(e)}"}

        @self.mcp.tool(
            name="get_test_stats",
            description="Get testing statistics and configuration",
            input_schema={
                "type": "object",
                "properties": {}
            }
        )
        async def get_test_stats() -> Dict[str, Any]:
            """Get testing statistics"""
            try:
                # Check pytest installation
                pytest_version = None
                try:
                    result = subprocess.run(
                        [self.default_python, "-m", "pytest", "--version"],
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        pytest_version = result.stdout.strip()
                except Exception:
                    pass

                # Count test files
                test_files = []
                for root, dirs, files in os.walk("."):
                    for file in files:
                        if file.startswith("test_") and file.endswith(".py"):
                            test_files.append(os.path.join(root, file))

                return {
                    "pytest_version": pytest_version,
                    "pytest_available": pytest_version is not None,
                    "dependencies_available": PYTEST_DEPS_AVAILABLE,
                    "test_files_found": len(test_files),
                    "test_files": test_files,
                    "default_python": self.default_python,
                    "pytest_args": self.pytest_args,
                    "current_directory": os.getcwd()
                }

            except Exception as e:
                logfire.error(f"Failed to get test stats: {str(e)}")
                return {"error": f"Test stats query failed: {str(e)}"}

    async def run(self):
        """Run the PyTest MCP server"""
        await self.mcp.run_stdio()


async def main():
    """Main entry point"""
    server = PyTestMCP()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
