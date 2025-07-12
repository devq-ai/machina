#!/usr/bin/env python
"""
Pytest MCP Server
FastMCP server for pytest testing automation and validation.
Provides test execution, coverage analysis, and test generation capabilities.
"""
import asyncio
import os
import subprocess
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

# Create FastMCP app instance
app = FastMCP("pytest-mcp")

class PytestHelper:
    """Pytest automation and testing helper."""
    
    def __init__(self):
        self.project_root = os.getenv('PROJECT_ROOT', '/Users/dionedge/devqai/machina')
        self.python_path = os.getenv('PYTHON_PATH', 'python3')
        self.coverage_threshold = float(os.getenv('PYTEST_COVERAGE_THRESHOLD', '90.0'))
    
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
                "success": process.returncode == 0,
                "returncode": process.returncode,
                "stdout": stdout.decode('utf-8'),
                "stderr": stderr.decode('utf-8'),
                "command": ' '.join(cmd)
            }
        except Exception as e:
            return {
                "success": False,
                "returncode": -1,
                "stdout": "",
                "stderr": str(e),
                "command": ' '.join(cmd)
            }

# Initialize helper
pytest_helper = PytestHelper()

@app.tool()
async def pytest_health_check() -> Dict[str, Any]:
    """Check pytest environment health and configuration."""
    try:
        # Check pytest installation
        result = await pytest_helper.run_command([pytest_helper.python_path, '-m', 'pytest', '--version'])
        
        health_status = {
            "pytest_available": result["success"],
            "pytest_version": result["stdout"].strip() if result["success"] else None,
            "python_path": pytest_helper.python_path,
            "project_root": pytest_helper.project_root,
            "coverage_threshold": pytest_helper.coverage_threshold,
            "timestamp": datetime.now().isoformat()
        }
        
        return health_status
        
    except Exception as e:
        raise RuntimeError(f"Pytest health check failed: {str(e)}")

@app.tool()
async def run_tests(
    test_path: Optional[str] = None, 
    verbose: bool = True,
    coverage: bool = True
) -> Dict[str, Any]:
    """Run pytest tests with optional coverage."""
    try:
        # Build pytest command
        cmd = [pytest_helper.python_path, '-m', 'pytest']
        
        if verbose:
            cmd.append('-v')
        
        if coverage:
            cmd.extend(['--cov=src', '--cov-report=term-missing'])
        
        if test_path:
            cmd.append(test_path)
        
        result = await pytest_helper.run_command(cmd)
        
        # Parse results
        output_lines = result["stdout"].split('\n')
        
        test_summary = {
            "success": result["success"],
            "command": result["command"],
            "exit_code": result["returncode"],
            "raw_output": result["stdout"],
            "errors": result["stderr"],
            "timestamp": datetime.now().isoformat()
        }
        
        return test_summary
        
    except Exception as e:
        raise RuntimeError(f"Failed to run tests: {str(e)}")

@app.tool()
async def generate_test(
    module_name: str,
    test_functions: Optional[List[str]] = None,
    include_coverage: bool = True
) -> str:
    """Generate a test file for a given module."""
    try:
        if not test_functions:
            test_functions = ["test_basic_functionality", "test_edge_cases"]
        
        test_code = f'''import pytest
from unittest.mock import patch, MagicMock
from src import {module_name}

class Test{module_name.title()}:
    """Test suite for {module_name} module."""
    
'''
        
        # Add test functions
        for func_name in test_functions:
            test_code += f'''    def {func_name}(self):
        """Test {func_name.replace('test_', '').replace('_', ' ')}."""
        # TODO: Implement {func_name}
        assert True  # Placeholder test
    
'''
        
        return test_code
        
    except Exception as e:
        raise RuntimeError(f"Failed to generate test file: {str(e)}")

@app.tool()
async def get_coverage(coverage_file: str = ".coverage") -> Dict[str, Any]:
    """Analyze test coverage from coverage file."""
    try:
        # Run coverage report
        cmd = [pytest_helper.python_path, '-m', 'coverage', 'report', '--format=json']
        result = await pytest_helper.run_command(cmd)
        
        if not result["success"]:
            return {
                "coverage_available": False,
                "error": result["stderr"],
                "timestamp": datetime.now().isoformat()
            }
        
        # Parse coverage JSON
        try:
            coverage_data = json.loads(result["stdout"])
            
            overall_coverage = coverage_data.get("totals", {}).get("percent_covered", 0)
            
            analysis = {
                "coverage_available": True,
                "overall_coverage": overall_coverage,
                "meets_threshold": overall_coverage >= pytest_helper.coverage_threshold,
                "threshold": pytest_helper.coverage_threshold,
                "file_coverage": coverage_data.get("files", {}),
                "timestamp": datetime.now().isoformat()
            }
            
            return analysis
            
        except json.JSONDecodeError:
            return {
                "coverage_available": False,
                "error": "Failed to parse coverage JSON",
                "raw_output": result["stdout"],
                "timestamp": datetime.now().isoformat()
            }
        
    except Exception as e:
        raise RuntimeError(f"Failed to analyze coverage: {str(e)}")

@app.tool()
async def run_specific_test(
    test_file: str,
    test_function: Optional[str] = None,
    markers: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Run a specific test file or function."""
    try:
        # Build pytest command
        cmd = [pytest_helper.python_path, '-m', 'pytest', '-v']
        
        # Add test file
        test_target = test_file
        if test_function:
            test_target = f"{test_file}::{test_function}"
        cmd.append(test_target)
        
        # Add markers if specified
        if markers:
            for marker in markers:
                cmd.extend(['-m', marker])
        
        result = await pytest_helper.run_command(cmd)
        
        return {
            "success": result["success"],
            "command": result["command"],
            "output": result["stdout"],
            "errors": result["stderr"],
            "exit_code": result["returncode"],
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise RuntimeError(f"Failed to run specific test: {str(e)}")

@app.tool()
async def list_test_files() -> List[str]:
    """List all test files in the project."""
    try:
        project_path = Path(pytest_helper.project_root)
        test_files = []
        
        # Find test files
        for pattern in ["test_*.py", "*_test.py"]:
            test_files.extend([str(f.relative_to(project_path)) for f in project_path.rglob(pattern)])
        
        return sorted(test_files)
        
    except Exception as e:
        raise RuntimeError(f"Failed to list test files: {str(e)}")

@app.tool()
async def validate_test_structure() -> Dict[str, Any]:
    """Validate project test structure and configuration."""
    try:
        project_path = Path(pytest_helper.project_root)
        
        # Check for pytest configuration
        config_files = []
        for config_name in ["pytest.ini", "pyproject.toml", "setup.cfg"]:
            config_path = project_path / config_name
            if config_path.exists():
                config_files.append(config_name)
        
        # Count test files
        test_files = await list_test_files()
        
        # Check test directory structure
        test_dirs = []
        if (project_path / "tests").exists():
            test_dirs.append("tests/")
        if (project_path / "test").exists():
            test_dirs.append("test/")
        
        validation = {
            "config_files": config_files,
            "test_files_count": len(test_files),
            "test_files": test_files,
            "test_directories": test_dirs,
            "project_root": str(project_path),
            "has_pytest_config": len(config_files) > 0,
            "timestamp": datetime.now().isoformat()
        }
        
        return validation
        
    except Exception as e:
        raise RuntimeError(f"Failed to validate test structure: {str(e)}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(app.run_stdio_async())