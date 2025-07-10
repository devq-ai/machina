#!/usr/bin/env python3
"""
Machina Registry Test Script
Simple test to verify registry availability and basic functionality.
"""

import asyncio
import sys
import os
import json
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, List

# Add the parent directory to the path so we can import fastmcp
sys.path.insert(0, str(Path(__file__).parent))

import logfire
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Logfire
logfire.configure()
logger = logfire


class RegistryTester:
    """Test suite for Machina MCP Registry"""

    def __init__(self):
        self.registry_path = Path(__file__).parent / "registry" / "main.py"
        self.test_results = []

    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all registry tests"""

        logger.info("🧪 Starting Machina Registry Test Suite")

        tests = [
            ("Environment Validation", self.test_environment),
            ("Registry File Check", self.test_registry_files),
            ("Python Import Test", self.test_python_imports),
            ("Registry Startup Test", self.test_registry_startup),
            ("Health Check Test", self.test_health_check),
            ("Server Registration Test", self.test_server_registration),
        ]

        results = {
            "total_tests": len(tests),
            "passed": 0,
            "failed": 0,
            "tests": []
        }

        for test_name, test_func in tests:
            try:
                logger.info(f"🔍 Running: {test_name}")
                result = await test_func()

                if result["passed"]:
                    logger.info(f"✅ {test_name}: PASSED")
                    results["passed"] += 1
                else:
                    logger.error(f"❌ {test_name}: FAILED - {result['error']}")
                    results["failed"] += 1

                results["tests"].append({
                    "name": test_name,
                    "passed": result["passed"],
                    "message": result.get("message", ""),
                    "error": result.get("error", "")
                })

            except Exception as e:
                logger.error(f"❌ {test_name}: EXCEPTION - {str(e)}")
                results["failed"] += 1
                results["tests"].append({
                    "name": test_name,
                    "passed": False,
                    "error": str(e)
                })

        # Calculate success rate
        success_rate = (results["passed"] / results["total_tests"]) * 100
        results["success_rate"] = success_rate

        logger.info(f"📊 Test Results: {results['passed']}/{results['total_tests']} passed ({success_rate:.1f}%)")

        return results

    async def test_environment(self) -> Dict[str, Any]:
        """Test environment variables and dependencies"""

        try:
            # Check required environment variables
            required_vars = [
                "OPENAI_API_KEY",
                "ANTHROPIC_API_KEY",
                "GITHUB_TOKEN",
                "SURREALDB_URL",
                "SURREALDB_USERNAME",
                "SURREALDB_PASSWORD"
            ]

            missing_vars = []
            for var in required_vars:
                if not os.getenv(var):
                    missing_vars.append(var)

            if missing_vars:
                return {
                    "passed": False,
                    "error": f"Missing environment variables: {missing_vars}"
                }

            # Check Python version
            if sys.version_info < (3, 8):
                return {
                    "passed": False,
                    "error": f"Python {sys.version_info.major}.{sys.version_info.minor} too old, need 3.8+"
                }

            return {
                "passed": True,
                "message": f"Environment OK - Python {sys.version_info.major}.{sys.version_info.minor}"
            }

        except Exception as e:
            return {"passed": False, "error": str(e)}

    async def test_registry_files(self) -> Dict[str, Any]:
        """Test registry files exist and are accessible"""

        try:
            # Check main registry file
            if not self.registry_path.exists():
                return {
                    "passed": False,
                    "error": f"Registry file not found: {self.registry_path}"
                }

            # Check if file is readable
            with open(self.registry_path, 'r') as f:
                content = f.read()
                if len(content) < 100:
                    return {
                        "passed": False,
                        "error": "Registry file appears empty or corrupted"
                    }

            # Check for required imports
            required_imports = ["fastmcp", "logfire", "MCPRegistry"]
            for import_name in required_imports:
                if import_name not in content:
                    return {
                        "passed": False,
                        "error": f"Missing required import: {import_name}"
                    }

            return {
                "passed": True,
                "message": f"Registry files OK - {len(content)} bytes"
            }

        except Exception as e:
            return {"passed": False, "error": str(e)}

    async def test_python_imports(self) -> Dict[str, Any]:
        """Test Python imports work correctly"""

        try:
            # Test basic imports
            import fastmcp
            import logfire
            from dotenv import load_dotenv

            # Test registry-specific imports
            from fastmcp import MCPRegistry

            return {
                "passed": True,
                "message": "All imports successful"
            }

        except ImportError as e:
            return {
                "passed": False,
                "error": f"Import failed: {str(e)}"
            }
        except Exception as e:
            return {"passed": False, "error": str(e)}

    async def test_registry_startup(self) -> Dict[str, Any]:
        """Test registry startup (quick validation)"""

        try:
            # Create a test process to validate startup
            cmd = [
                sys.executable,
                str(self.registry_path),
                "--validate-only"  # We'll add this flag
            ]

            # Run with timeout
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.registry_path.parent)
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=10.0
                )

                if process.returncode == 0:
                    return {
                        "passed": True,
                        "message": "Registry startup validation passed"
                    }
                else:
                    return {
                        "passed": False,
                        "error": f"Startup failed: {stderr.decode()}"
                    }

            except asyncio.TimeoutError:
                process.kill()
                return {
                    "passed": False,
                    "error": "Registry startup timed out"
                }

        except Exception as e:
            return {"passed": False, "error": str(e)}

    async def test_health_check(self) -> Dict[str, Any]:
        """Test registry health check functionality"""

        try:
            # For now, we'll test the health check logic exists
            # In a real scenario, this would ping the running registry

            with open(self.registry_path, 'r') as f:
                content = f.read()

            # Check for health monitoring code
            health_indicators = [
                "health_monitor",
                "add_default_health_checks",
                "production-ready"
            ]

            missing_indicators = []
            for indicator in health_indicators:
                if indicator not in content:
                    missing_indicators.append(indicator)

            if missing_indicators:
                return {
                    "passed": False,
                    "error": f"Missing health check components: {missing_indicators}"
                }

            return {
                "passed": True,
                "message": "Health check components found"
            }

        except Exception as e:
            return {"passed": False, "error": str(e)}

    async def test_server_registration(self) -> Dict[str, Any]:
        """Test server registration configuration"""

        try:
            with open(self.registry_path, 'r') as f:
                content = f.read()

            # Check for server registration logic
            if "register_production_servers" not in content:
                return {
                    "passed": False,
                    "error": "Server registration function not found"
                }

            # Count expected servers
            expected_servers = [
                "context7-mcp", "memory-mcp", "sequential-thinking-mcp",
                "crawl4ai-mcp", "github-mcp", "fastapi-mcp", "pytest-mcp",
                "pydantic-ai-mcp", "docker-mcp", "logfire-mcp",
                "fastmcp-mcp", "registry-mcp", "surrealdb-mcp"
            ]

            missing_servers = []
            for server in expected_servers:
                if server not in content:
                    missing_servers.append(server)

            if missing_servers:
                return {
                    "passed": False,
                    "error": f"Missing server configurations: {missing_servers}"
                }

            return {
                "passed": True,
                "message": f"All {len(expected_servers)} servers configured"
            }

        except Exception as e:
            return {"passed": False, "error": str(e)}

    def print_detailed_results(self, results: Dict[str, Any]):
        """Print detailed test results"""

        print("\n" + "="*60)
        print("🧪 MACHINA REGISTRY TEST RESULTS")
        print("="*60)

        print(f"📊 Overall: {results['passed']}/{results['total_tests']} tests passed ({results['success_rate']:.1f}%)")

        if results['success_rate'] == 100:
            print("✅ All tests passed! Registry is ready for use.")
        elif results['success_rate'] >= 80:
            print("⚠️  Most tests passed. Some issues need attention.")
        else:
            print("❌ Multiple test failures. Registry needs fixes.")

        print("\n📋 Test Details:")
        for test in results['tests']:
            status = "✅ PASS" if test['passed'] else "❌ FAIL"
            print(f"  {status}: {test['name']}")

            if test.get('message'):
                print(f"    💡 {test['message']}")
            if test.get('error'):
                print(f"    ❌ {test['error']}")

        print("\n🔧 Quick Start Commands:")
        print("  # Start the registry")
        print(f"  python {self.registry_path}")
        print()
        print("  # Check if running")
        print("  ps aux | grep 'machina.*registry'")
        print()
        print("  # View logs")
        print("  tail -f machina/logs/registry.log")

        print("\n📚 Documentation:")
        print("  - Registry Config: machina/tests/master_mcp-server.yaml")
        print("  - Test Results: machina/testing-table.md")
        print("  - Environment: machina/.env")

        print("="*60)


async def main():
    """Main test runner"""

    try:
        tester = RegistryTester()
        results = await tester.run_all_tests()
        tester.print_detailed_results(results)

        # Exit with appropriate code
        if results['success_rate'] == 100:
            sys.exit(0)
        else:
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("🛑 Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Test runner failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
