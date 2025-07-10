#!/usr/bin/env python3
"""
Comprehensive MCP Test Execution Script for SurrealDB MCP Server

This script provides comprehensive testing capabilities for the SurrealDB MCP server,
including environment validation, performance analysis, and detailed reporting.

Usage:
    python run_mcp_tests.py --mcp surrealdb
    python run_mcp_tests.py --mcp surrealdb --performance-only
    python run_mcp_tests.py --mcp surrealdb --output results.json
    python run_mcp_tests.py --mcp all --comprehensive
"""

import asyncio
import json
import logging
import os
import sys
import time
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import subprocess
import signal

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test configuration
TEST_CONFIG = {
    "surrealdb": {
        "name": "SurrealDB MCP Server",
        "module": "surrealdb_mcp.server",
        "test_file": "tests/test_surrealdb_mcp.py",
        "required_env": [
            "SURREALDB_URL",
            "SURREALDB_USERNAME",
            "SURREALDB_PASSWORD"
        ],
        "optional_env": [
            "SURREALDB_NAMESPACE",
            "SURREALDB_DATABASE",
            "SURREALDB_TIMEOUT"
        ],
        "performance_targets": {
            "status_response": 0.1,
            "document_create": 0.2,
            "graph_traverse": 0.5,
            "query_execute": 1.0,
            "connection_setup": 0.1
        },
        "required_tools": [
            "surrealdb_status",
            "connect_database",
            "execute_query",
            "create_document",
            "get_document",
            "update_document",
            "delete_document",
            "list_tables",
            "query_table",
            "create_relation",
            "get_relations",
            "graph_traverse",
            "set_key_value",
            "get_key_value",
            "delete_key_value",
            "get_database_info"
        ]
    }
}

class MCPTestRunner:
    """Comprehensive MCP test runner."""

    def __init__(self, mcp_name: str, output_file: Optional[str] = None):
        self.mcp_name = mcp_name
        self.output_file = output_file
        self.config = TEST_CONFIG.get(mcp_name, {})
        self.results = {
            "summary": {
                "mcp_name": mcp_name,
                "total_tests": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "success_rate": 0.0,
                "total_duration": 0.0,
                "timestamp": datetime.now().isoformat()
            },
            "environment": {},
            "performance": {},
            "test_results": [],
            "errors": [],
            "recommendations": []
        }
        self.start_time = None
        self.surrealdb_process = None

    def validate_environment(self) -> bool:
        """Validate required environment variables and dependencies."""
        logger.info("🔍 Validating environment...")

        env_status = {}
        all_valid = True

        # Check required environment variables
        for env_var in self.config.get("required_env", []):
            value = os.getenv(env_var)
            env_status[env_var] = value is not None
            if not value:
                logger.error(f"❌ Required environment variable {env_var} not set")
                all_valid = False
            else:
                logger.info(f"✅ {env_var} configured")

        # Check optional environment variables
        for env_var in self.config.get("optional_env", []):
            value = os.getenv(env_var)
            env_status[env_var] = value is not None
            if value:
                logger.info(f"✅ {env_var} configured")
            else:
                logger.info(f"ℹ️  {env_var} using default value")

        # Check Python dependencies
        try:
            import pytest
            import mcp
            env_status["pytest"] = True
            env_status["mcp"] = True
            logger.info("✅ Python dependencies available")
        except ImportError as e:
            logger.error(f"❌ Missing Python dependencies: {e}")
            env_status["python_deps"] = False
            all_valid = False

        # Check SurrealDB availability
        surrealdb_available = self.check_surrealdb_availability()
        env_status["surrealdb_server"] = surrealdb_available
        if not surrealdb_available:
            logger.warning("⚠️  SurrealDB server not running, attempting to start...")
            if self.start_surrealdb():
                env_status["surrealdb_server"] = True
                logger.info("✅ SurrealDB server started")
            else:
                logger.error("❌ Could not start SurrealDB server")
                all_valid = False

        self.results["environment"] = env_status
        return all_valid

    def check_surrealdb_availability(self) -> bool:
        """Check if SurrealDB server is running."""
        try:
            import subprocess
            result = subprocess.run(
                ["curl", "-s", "http://localhost:8000/status"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception as e:
            logger.debug(f"SurrealDB availability check failed: {e}")
            return False

    def start_surrealdb(self) -> bool:
        """Start SurrealDB server for testing."""
        try:
            # Start SurrealDB server in memory mode
            self.surrealdb_process = subprocess.Popen([
                "surreal", "start",
                "--log", "info",
                "--user", "root",
                "--pass", "root",
                "memory"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # Wait for server to start
            time.sleep(3)

            # Verify server is running
            if self.check_surrealdb_availability():
                logger.info("SurrealDB server started successfully")
                return True
            else:
                logger.error("SurrealDB server failed to start properly")
                return False

        except Exception as e:
            logger.error(f"Failed to start SurrealDB server: {e}")
            return False

    def stop_surrealdb(self):
        """Stop SurrealDB server."""
        if self.surrealdb_process:
            try:
                self.surrealdb_process.terminate()
                self.surrealdb_process.wait(timeout=5)
                logger.info("SurrealDB server stopped")
            except subprocess.TimeoutExpired:
                self.surrealdb_process.kill()
                logger.warning("SurrealDB server forcefully terminated")
            except Exception as e:
                logger.error(f"Error stopping SurrealDB server: {e}")

    def run_pytest_tests(self, test_categories: List[str] = None) -> Dict[str, Any]:
        """Run PyTest tests with specified categories."""
        logger.info("🧪 Running PyTest tests...")

        test_file = self.config.get("test_file", "tests/test_surrealdb_mcp.py")
        test_path = Path(test_file)

        if not test_path.exists():
            logger.error(f"❌ Test file {test_file} not found")
            return {"success": False, "error": f"Test file {test_file} not found"}

        # Build pytest command
        pytest_cmd = [
            "python", "-m", "pytest",
            str(test_path),
            "-v",
            "--tb=short",
            "--cov=surrealdb_mcp",
            "--cov-report=term-missing",
            "--cov-report=json:coverage.json",
            "--json-report",
            "--json-report-file=pytest_report.json"
        ]

        # Add category filters if specified
        if test_categories:
            category_filter = " or ".join(test_categories)
            pytest_cmd.extend(["-k", category_filter])

        # Add performance markers
        if "performance" in (test_categories or []):
            pytest_cmd.extend(["-m", "performance"])

        try:
            # Run tests
            result = subprocess.run(
                pytest_cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            # Parse results
            test_results = {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }

            # Try to parse JSON report
            json_report_path = Path("pytest_report.json")
            if json_report_path.exists():
                try:
                    with open(json_report_path, 'r') as f:
                        json_report = json.load(f)
                        test_results["json_report"] = json_report

                        # Extract summary
                        summary = json_report.get("summary", {})
                        self.results["summary"]["total_tests"] = summary.get("total", 0)
                        self.results["summary"]["passed"] = summary.get("passed", 0)
                        self.results["summary"]["failed"] = summary.get("failed", 0)
                        self.results["summary"]["skipped"] = summary.get("skipped", 0)

                        # Calculate success rate
                        total = self.results["summary"]["total_tests"]
                        passed = self.results["summary"]["passed"]
                        if total > 0:
                            self.results["summary"]["success_rate"] = (passed / total) * 100

                except Exception as e:
                    logger.warning(f"Could not parse JSON report: {e}")

            return test_results

        except subprocess.TimeoutExpired:
            logger.error("❌ Test execution timed out")
            return {"success": False, "error": "Test execution timed out"}
        except Exception as e:
            logger.error(f"❌ Error running tests: {e}")
            return {"success": False, "error": str(e)}

    def run_performance_tests(self) -> Dict[str, Any]:
        """Run performance-specific tests."""
        logger.info("🏃 Running performance tests...")

        performance_results = {
            "targets": self.config.get("performance_targets", {}),
            "actual": {},
            "analysis": {}
        }

        # Run performance tests
        test_results = self.run_pytest_tests(["performance"])

        if test_results.get("success"):
            # Extract performance metrics from test output
            stdout = test_results.get("stdout", "")

            # Parse performance metrics from logs
            for line in stdout.split('\n'):
                if "Benchmark" in line and ":" in line:
                    try:
                        parts = line.split(":")
                        if len(parts) >= 2:
                            metric_name = parts[0].split()[-1]
                            metric_value = float(parts[1].strip().rstrip('s'))
                            performance_results["actual"][metric_name] = metric_value
                    except (ValueError, IndexError):
                        continue

            # Compare with targets
            targets = performance_results["targets"]
            actual = performance_results["actual"]

            for metric, target in targets.items():
                if metric in actual:
                    actual_value = actual[metric]
                    performance_results["analysis"][metric] = {
                        "target": target,
                        "actual": actual_value,
                        "status": "PASS" if actual_value <= target else "FAIL",
                        "margin": target - actual_value
                    }

        self.results["performance"] = performance_results
        return performance_results

    def run_integration_tests(self) -> Dict[str, Any]:
        """Run integration tests with real services."""
        logger.info("🔌 Running integration tests...")
        return self.run_pytest_tests(["integration"])

    def run_all_tests(self) -> Dict[str, Any]:
        """Run comprehensive test suite."""
        logger.info("🎯 Running comprehensive test suite...")
        self.start_time = time.time()

        # Run different test categories
        test_categories = [
            ("core_functionality", "Core Functionality"),
            ("integration", "Integration"),
            ("performance", "Performance"),
            ("error_handling", "Error Handling"),
            ("compliance", "Compliance")
        ]

        category_results = {}

        for category, description in test_categories:
            logger.info(f"Running {description} tests...")
            result = self.run_pytest_tests([category])
            category_results[category] = result

            if not result.get("success", False):
                logger.warning(f"⚠️  {description} tests had failures")

        # Calculate overall duration
        if self.start_time:
            self.results["summary"]["total_duration"] = time.time() - self.start_time

        return category_results

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report."""
        logger.info("📊 Generating test report...")

        # Add recommendations based on results
        recommendations = []

        # Check success rate
        success_rate = self.results["summary"]["success_rate"]
        if success_rate < 100:
            recommendations.append({
                "type": "quality",
                "priority": "high",
                "message": f"Success rate {success_rate:.1f}% is below 100% target. Review failed tests."
            })

        # Check performance
        performance = self.results.get("performance", {})
        failed_performance = []
        for metric, analysis in performance.get("analysis", {}).items():
            if analysis.get("status") == "FAIL":
                failed_performance.append(metric)

        if failed_performance:
            recommendations.append({
                "type": "performance",
                "priority": "medium",
                "message": f"Performance targets not met for: {', '.join(failed_performance)}"
            })

        # Check environment
        env_issues = []
        for env_var, status in self.results.get("environment", {}).items():
            if not status:
                env_issues.append(env_var)

        if env_issues:
            recommendations.append({
                "type": "environment",
                "priority": "medium",
                "message": f"Environment issues detected: {', '.join(env_issues)}"
            })

        self.results["recommendations"] = recommendations

        # Save report if output file specified
        if self.output_file:
            try:
                # Ensure test_results directory exists
                test_results_dir = Path("test_results")
                test_results_dir.mkdir(exist_ok=True)

                # If output_file is just a filename, put it in test_results
                if "/" not in self.output_file:
                    output_path = test_results_dir / self.output_file
                else:
                    output_path = Path(self.output_file)

                with open(output_path, 'w') as f:
                    json.dump(self.results, f, indent=2)
                logger.info(f"📄 Report saved to {output_path}")
            except Exception as e:
                logger.error(f"❌ Could not save report: {e}")

        return self.results

    def print_summary(self):
        """Print test summary to console."""
        summary = self.results["summary"]

        print("\n" + "="*60)
        print(f"🎯 MCP TEST SUMMARY - {summary['mcp_name'].upper()}")
        print("="*60)

        print(f"📊 Test Results:")
        print(f"   Total Tests: {summary['total_tests']}")
        print(f"   Passed: {summary['passed']}")
        print(f"   Failed: {summary['failed']}")
        print(f"   Skipped: {summary['skipped']}")
        print(f"   Success Rate: {summary['success_rate']:.1f}%")
        print(f"   Duration: {summary['total_duration']:.2f}s")

        # Performance summary
        performance = self.results.get("performance", {})
        if performance.get("analysis"):
            print(f"\n🏃 Performance Results:")
            for metric, analysis in performance["analysis"].items():
                status_icon = "✅" if analysis["status"] == "PASS" else "❌"
                print(f"   {status_icon} {metric}: {analysis['actual']:.3f}s (target: {analysis['target']}s)")

        # Environment summary
        env = self.results.get("environment", {})
        if env:
            print(f"\n🔧 Environment Status:")
            for var, status in env.items():
                status_icon = "✅" if status else "❌"
                print(f"   {status_icon} {var}")

        # Recommendations
        recommendations = self.results.get("recommendations", [])
        if recommendations:
            print(f"\n💡 Recommendations:")
            for rec in recommendations:
                priority_icon = "🔴" if rec["priority"] == "high" else "🟡"
                print(f"   {priority_icon} {rec['message']}")

        # Overall status
        overall_status = "PASSED" if summary["success_rate"] == 100 else "FAILED"
        status_icon = "✅" if overall_status == "PASSED" else "❌"
        print(f"\n{status_icon} OVERALL STATUS: {overall_status}")
        print("="*60)

    def cleanup(self):
        """Clean up resources."""
        self.stop_surrealdb()

        # Clean up temporary files
        temp_files = ["pytest_report.json", "coverage.json", ".coverage"]
        for temp_file in temp_files:
            try:
                if Path(temp_file).exists():
                    Path(temp_file).unlink()
            except Exception as e:
                logger.debug(f"Could not remove {temp_file}: {e}")

def signal_handler(signum, frame):
    """Handle interrupt signals."""
    logger.info("Received interrupt signal, cleaning up...")
    sys.exit(0)

def main():
    """Main test execution function."""
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="MCP Test Runner")
    parser.add_argument("--mcp", required=True, choices=["surrealdb", "all"],
                       help="MCP server to test")
    parser.add_argument("--performance-only", action="store_true",
                       help="Run only performance tests")
    parser.add_argument("--integration-only", action="store_true",
                       help="Run only integration tests")
    parser.add_argument("--output", type=str,
                       help="Output file for results (JSON)")
    parser.add_argument("--comprehensive", action="store_true",
                       help="Run comprehensive test suite")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")

    args = parser.parse_args()

    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Handle "all" MCP option
    mcp_servers = ["surrealdb"] if args.mcp == "surrealdb" else ["surrealdb"]

    overall_success = True

    for mcp_name in mcp_servers:
        logger.info(f"🚀 Starting tests for {mcp_name.upper()} MCP Server")

        # Initialize test runner
        runner = MCPTestRunner(mcp_name, args.output)

        try:
            # Validate environment
            if not runner.validate_environment():
                logger.error(f"❌ Environment validation failed for {mcp_name}")
                overall_success = False
                continue

            # Run tests based on arguments
            if args.performance_only:
                runner.run_performance_tests()
            elif args.integration_only:
                runner.run_integration_tests()
            elif args.comprehensive:
                runner.run_all_tests()
            else:
                runner.run_all_tests()

            # Generate report
            runner.generate_report()
            runner.print_summary()

            # Check if tests passed
            if runner.results["summary"]["success_rate"] < 100:
                overall_success = False

        except Exception as e:
            logger.error(f"❌ Error running tests for {mcp_name}: {e}")
            overall_success = False
        finally:
            runner.cleanup()

    # Exit with appropriate code
    sys.exit(0 if overall_success else 1)

if __name__ == "__main__":
    main()
