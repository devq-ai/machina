#!/usr/bin/env python3
"""
Quick Validation Script for SurrealDB MCP Testing Framework

This script provides a quick validation of the comprehensive testing framework
to ensure all components are working correctly before running the full test suite.

Usage:
    python validate_testing_framework.py
"""

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TestingFrameworkValidator:
    """Validate the comprehensive testing framework."""

    def __init__(self):
        self.results = {
            "summary": {
                "validation_time": None,
                "total_checks": 0,
                "passed_checks": 0,
                "failed_checks": 0,
                "success_rate": 0.0,
                "status": "UNKNOWN"
            },
            "checks": [],
            "environment": {},
            "recommendations": []
        }
        self.start_time = time.time()

    def check_environment_variables(self) -> bool:
        """Check required environment variables."""
        logger.info("🔍 Checking environment variables...")

        required_vars = [
            "SURREALDB_URL",
            "SURREALDB_USERNAME",
            "SURREALDB_PASSWORD"
        ]

        optional_vars = [
            "SURREALDB_NAMESPACE",
            "SURREALDB_DATABASE",
            "SURREALDB_TIMEOUT"
        ]

        all_good = True
        env_status = {}

        for var in required_vars:
            value = os.getenv(var)
            env_status[var] = value is not None
            if not value:
                logger.error(f"❌ Missing required environment variable: {var}")
                all_good = False
            else:
                logger.info(f"✅ {var} is set")

        for var in optional_vars:
            value = os.getenv(var)
            env_status[var] = value is not None
            if value:
                logger.info(f"✅ {var} is set")
            else:
                logger.info(f"ℹ️  {var} not set (using default)")

        self.results["environment"] = env_status
        return all_good

    def check_python_dependencies(self) -> bool:
        """Check Python dependencies."""
        logger.info("🐍 Checking Python dependencies...")

        required_modules = [
            "pytest",
            "pytest_asyncio",
            "pytest_cov",
            "mcp",
            "asyncio",
            "json",
            "pathlib"
        ]

        all_good = True

        for module in required_modules:
            try:
                __import__(module)
                logger.info(f"✅ {module} available")
            except ImportError:
                logger.error(f"❌ {module} not available")
                all_good = False

        return all_good

    def check_file_structure(self) -> bool:
        """Check required file structure."""
        logger.info("📁 Checking file structure...")

        required_files = [
            "surrealdb_mcp/server.py",
            "tests/test_surrealdb_mcp.py",
            "tests/conftest.py",
            "pytest.ini",
            "MCP_TESTING_CRITERIA.md",
            "MCP_TESTING_USAGE.md",
            "run_mcp_tests.py"
        ]

        all_good = True

        for file_path in required_files:
            path = Path(file_path)
            if path.exists():
                logger.info(f"✅ {file_path} exists")
            else:
                logger.error(f"❌ {file_path} missing")
                all_good = False

        return all_good

    def check_surrealdb_availability(self) -> bool:
        """Check SurrealDB server availability."""
        logger.info("🗄️  Checking SurrealDB availability...")

        try:
            import subprocess
            result = subprocess.run(
                ["curl", "-s", "http://localhost:8000/status"],
                capture_output=True,
                timeout=5
            )

            if result.returncode == 0:
                logger.info("✅ SurrealDB server is running")
                return True
            else:
                logger.warning("⚠️  SurrealDB server not running")
                return False

        except Exception as e:
            logger.warning(f"⚠️  Could not check SurrealDB: {e}")
            return False

    def check_test_configuration(self) -> bool:
        """Check test configuration files."""
        logger.info("⚙️  Checking test configuration...")

        # Check pytest.ini
        pytest_ini = Path("pytest.ini")
        if not pytest_ini.exists():
            logger.error("❌ pytest.ini not found")
            return False

        # Check conftest.py
        conftest = Path("tests/conftest.py")
        if not conftest.exists():
            logger.error("❌ tests/conftest.py not found")
            return False

        # Check test file
        test_file = Path("tests/test_surrealdb_mcp.py")
        if not test_file.exists():
            logger.error("❌ tests/test_surrealdb_mcp.py not found")
            return False

        logger.info("✅ Test configuration files present")
        return True

    def check_documentation(self) -> bool:
        """Check documentation files."""
        logger.info("📚 Checking documentation...")

        doc_files = [
            "MCP_TESTING_CRITERIA.md",
            "MCP_TESTING_USAGE.md"
        ]

        all_good = True

        for doc_file in doc_files:
            path = Path(doc_file)
            if path.exists():
                # Check if file has content
                if path.stat().st_size > 0:
                    logger.info(f"✅ {doc_file} exists and has content")
                else:
                    logger.warning(f"⚠️  {doc_file} exists but is empty")
                    all_good = False
            else:
                logger.error(f"❌ {doc_file} missing")
                all_good = False

        return all_good

    def check_server_module(self) -> bool:
        """Check SurrealDB MCP server module."""
        logger.info("🖥️  Checking server module...")

        try:
            # Try to import the server module
            sys.path.insert(0, str(Path.cwd()))
            from surrealdb_mcp.server import SurrealDBServer

            # Check if server can be instantiated
            server = SurrealDBServer()

            # Check if server has required attributes
            required_attrs = ['server', 'namespace', 'database', 'connected']
            for attr in required_attrs:
                if hasattr(server, attr):
                    logger.info(f"✅ Server has {attr} attribute")
                else:
                    logger.error(f"❌ Server missing {attr} attribute")
                    return False

            logger.info("✅ Server module is valid")
            return True

        except Exception as e:
            logger.error(f"❌ Server module error: {e}")
            return False

    def check_test_execution_script(self) -> bool:
        """Check test execution script."""
        logger.info("🚀 Checking test execution script...")

        script_path = Path("run_mcp_tests.py")
        if not script_path.exists():
            logger.error("❌ run_mcp_tests.py not found")
            return False

        # Check if script is executable
        if not os.access(script_path, os.X_OK):
            logger.warning("⚠️  run_mcp_tests.py is not executable")

        # Check script content
        try:
            with open(script_path, 'r') as f:
                content = f.read()
                if "MCPTestRunner" in content:
                    logger.info("✅ Test execution script is valid")
                    return True
                else:
                    logger.error("❌ Test execution script appears invalid")
                    return False
        except Exception as e:
            logger.error(f"❌ Could not read test execution script: {e}")
            return False

    def perform_validation(self) -> Dict[str, Any]:
        """Perform comprehensive validation."""
        logger.info("🎯 Starting comprehensive testing framework validation...")

        checks = [
            ("Environment Variables", self.check_environment_variables),
            ("Python Dependencies", self.check_python_dependencies),
            ("File Structure", self.check_file_structure),
            ("SurrealDB Availability", self.check_surrealdb_availability),
            ("Test Configuration", self.check_test_configuration),
            ("Documentation", self.check_documentation),
            ("Server Module", self.check_server_module),
            ("Test Execution Script", self.check_test_execution_script)
        ]

        total_checks = len(checks)
        passed_checks = 0

        for check_name, check_func in checks:
            logger.info(f"\n--- {check_name} ---")

            try:
                result = check_func()
                status = "PASSED" if result else "FAILED"

                if result:
                    passed_checks += 1
                    logger.info(f"✅ {check_name}: {status}")
                else:
                    logger.error(f"❌ {check_name}: {status}")

                self.results["checks"].append({
                    "name": check_name,
                    "status": status,
                    "passed": result
                })

            except Exception as e:
                logger.error(f"❌ {check_name}: ERROR - {e}")
                self.results["checks"].append({
                    "name": check_name,
                    "status": "ERROR",
                    "passed": False,
                    "error": str(e)
                })

        # Calculate results
        success_rate = (passed_checks / total_checks) * 100 if total_checks > 0 else 0

        self.results["summary"].update({
            "validation_time": time.time() - self.start_time,
            "total_checks": total_checks,
            "passed_checks": passed_checks,
            "failed_checks": total_checks - passed_checks,
            "success_rate": success_rate,
            "status": "PASSED" if success_rate == 100 else "FAILED"
        })

        # Generate recommendations
        self.generate_recommendations()

        return self.results

    def generate_recommendations(self):
        """Generate recommendations based on validation results."""
        recommendations = []

        # Environment recommendations
        env = self.results["environment"]
        missing_required = [var for var, status in env.items()
                          if not status and var in ["SURREALDB_URL", "SURREALDB_USERNAME", "SURREALDB_PASSWORD"]]

        if missing_required:
            recommendations.append({
                "type": "environment",
                "priority": "high",
                "message": f"Set required environment variables: {', '.join(missing_required)}"
            })

        # SurrealDB recommendations
        if not self.check_surrealdb_availability():
            recommendations.append({
                "type": "service",
                "priority": "medium",
                "message": "Start SurrealDB server: surreal start --log info --user root --pass root memory"
            })

        # Success rate recommendations
        if self.results["summary"]["success_rate"] < 100:
            recommendations.append({
                "type": "quality",
                "priority": "high",
                "message": "Fix all validation issues before running tests"
            })

        self.results["recommendations"] = recommendations

    def print_summary(self):
        """Print validation summary."""
        summary = self.results["summary"]

        print("\n" + "="*60)
        print("🎯 TESTING FRAMEWORK VALIDATION SUMMARY")
        print("="*60)

        print(f"📊 Validation Results:")
        print(f"   Total Checks: {summary['total_checks']}")
        print(f"   Passed: {summary['passed_checks']}")
        print(f"   Failed: {summary['failed_checks']}")
        print(f"   Success Rate: {summary['success_rate']:.1f}%")
        print(f"   Duration: {summary['validation_time']:.2f}s")

        # Show failed checks
        failed_checks = [check for check in self.results["checks"] if not check["passed"]]
        if failed_checks:
            print(f"\n❌ Failed Checks:")
            for check in failed_checks:
                print(f"   - {check['name']}: {check['status']}")

        # Show recommendations
        recommendations = self.results["recommendations"]
        if recommendations:
            print(f"\n💡 Recommendations:")
            for rec in recommendations:
                priority_icon = "🔴" if rec["priority"] == "high" else "🟡"
                print(f"   {priority_icon} {rec['message']}")

        # Overall status
        status_icon = "✅" if summary["status"] == "PASSED" else "❌"
        print(f"\n{status_icon} OVERALL STATUS: {summary['status']}")

        if summary["status"] == "PASSED":
            print("\n🚀 Testing framework is ready!")
            print("   Run tests with: python run_mcp_tests.py --mcp surrealdb")
            print("   Or use pytest: pytest tests/test_surrealdb_mcp.py -v")
        else:
            print("\n🔧 Please fix the issues above before running tests")

        print("="*60)

def main():
    """Main validation function."""
    validator = TestingFrameworkValidator()

    try:
        results = validator.perform_validation()
        validator.print_summary()

        # Save results to file
        with open("validation_results.json", "w") as f:
            json.dump(results, f, indent=2)

        # Exit with appropriate code
        sys.exit(0 if results["summary"]["status"] == "PASSED" else 1)

    except Exception as e:
        logger.error(f"❌ Validation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
