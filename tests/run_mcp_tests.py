#!/usr/bin/env python3
"""
MCP Test Execution Script

Executes comprehensive MCP server tests following DevQ.ai testing criteria
with 100% success rate requirements and real service validation.

Usage:
    python run_mcp_tests.py --mcp logfire
    python run_mcp_tests.py --mcp all
    python run_mcp_tests.py --mcp context7 --performance-only
"""

import asyncio
import argparse
import json
import os
import sys
import time
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class MCPTestExecutor:
    """Execute MCP tests with comprehensive validation and reporting."""

    def __init__(self):
        self.test_results = {}
        self.performance_metrics = {}
        self.start_time = None
        self.validated_mcps = []

        # Define available MCPs and their test requirements
        self.available_mcps = {
            'logfire': {
                'path': 'primer/mcp-servers/logfire-mcp',
                'requires_credentials': ['LOGFIRE_WRITE_TOKEN', 'LOGFIRE_READ_TOKEN'],
                'external_services': ['logfire-api', 'prometheus'],
                'performance_targets': {
                    'status_response': 0.1,  # 100ms
                    'metrics_collection': 1.0,  # 1s
                    'health_check': 2.0  # 2s
                }
            },
            'context7': {
                'path': 'primer/mcp-servers/context7-mcp',
                'requires_credentials': ['OPENAI_API_KEY', 'UPSTASH_REDIS_REST_URL', 'UPSTASH_REDIS_REST_TOKEN'],
                'external_services': ['openai-api', 'redis'],
                'performance_targets': {
                    'embedding_generation': 0.5,  # 500ms
                    'similarity_search': 0.2,  # 200ms
                    'document_storage': 0.1  # 100ms
                }
            },
            'memory': {
                'path': 'primer/mcp-servers/memory-mcp',
                'requires_credentials': [],
                'external_services': [],
                'performance_targets': {
                    'memory_operations': 0.05,  # 50ms
                    'persistence': 0.1  # 100ms
                }
            },
            'pytest': {
                'path': 'primer/mcp-servers/pytest-mcp',
                'requires_credentials': [],
                'external_services': [],
                'performance_targets': {
                    'test_execution': 5.0,  # 5s for test runs
                    'coverage_analysis': 2.0  # 2s for coverage
                }
            }
        }

    def validate_environment(self, mcp_name: str) -> bool:
        """Validate environment setup for MCP testing."""
        logger.info(f"🔍 Validating environment for {mcp_name}...")

        mcp_config = self.available_mcps.get(mcp_name)
        if not mcp_config:
            logger.error(f"❌ Unknown MCP: {mcp_name}")
            return False

        # Check required credentials
        missing_creds = []
        for cred in mcp_config['requires_credentials']:
            if not os.getenv(cred):
                missing_creds.append(cred)

        if missing_creds:
            logger.error(f"❌ Missing required credentials for {mcp_name}: {missing_creds}")
            logger.error("   Please set these environment variables before testing")
            return False

        # Check MCP directory exists
        mcp_path = Path(mcp_config['path'])
        if not mcp_path.exists():
            logger.error(f"❌ MCP directory not found: {mcp_path}")
            return False

        # Check test directory exists
        test_path = mcp_path / 'tests'
        if not test_path.exists():
            logger.warning(f"⚠️  No tests directory found: {test_path}")
            return False

        logger.info(f"✅ Environment validation passed for {mcp_name}")
        return True

    def run_validation_script(self, mcp_name: str) -> Dict[str, Any]:
        """Run the MCP's validation script if available."""
        logger.info(f"🧪 Running validation script for {mcp_name}...")

        mcp_config = self.available_mcps[mcp_name]
        mcp_path = Path(mcp_config['path'])
        validation_script = mcp_path / 'validate_server.py'

        if not validation_script.exists():
            logger.warning(f"⚠️  No validation script found: {validation_script}")
            return {'status': 'skipped', 'reason': 'no_validation_script'}

        try:
            # Set up environment
            env = os.environ.copy()
            env['PYTHONPATH'] = str(mcp_path) + ':' + env.get('PYTHONPATH', '')

            # Run validation script
            start_time = time.time()
            result = subprocess.run(
                [sys.executable, 'validate_server.py'],
                cwd=mcp_path,
                env=env,
                capture_output=True,
                text=True,
                timeout=120  # 2 minute timeout
            )
            duration = time.time() - start_time

            # Check for JSON report
            report_files = list(mcp_path.glob('validation_report_*.json'))
            if report_files:
                latest_report = max(report_files, key=lambda f: f.stat().st_mtime)
                with open(latest_report) as f:
                    validation_data = json.load(f)

                # Move report to standard location
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                standard_name = f"{mcp_name}-{timestamp}.json"
                standard_path = Path('machina') / standard_name
                standard_path.parent.mkdir(exist_ok=True)

                if standard_path != latest_report:
                    latest_report.rename(standard_path)

                validation_data['execution_info'] = {
                    'duration': duration,
                    'return_code': result.returncode,
                    'report_location': str(standard_path)
                }

                return validation_data
            else:
                logger.error(f"❌ No validation report generated for {mcp_name}")
                return {
                    'status': 'failed',
                    'reason': 'no_report_generated',
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'return_code': result.returncode
                }

        except subprocess.TimeoutExpired:
            logger.error(f"❌ Validation script timeout for {mcp_name}")
            return {'status': 'failed', 'reason': 'timeout'}
        except Exception as e:
            logger.error(f"❌ Validation script error for {mcp_name}: {e}")
            return {'status': 'failed', 'reason': str(e)}

    def run_pytest_tests(self, mcp_name: str) -> Dict[str, Any]:
        """Run PyTest suite for the MCP."""
        logger.info(f"🔬 Running PyTest suite for {mcp_name}...")

        mcp_config = self.available_mcps[mcp_name]
        mcp_path = Path(mcp_config['path'])
        test_path = mcp_path / 'tests'

        if not test_path.exists():
            logger.warning(f"⚠️  No tests directory: {test_path}")
            return {'status': 'skipped', 'reason': 'no_tests_directory'}

        try:
            # Set up environment
            env = os.environ.copy()
            env['PYTHONPATH'] = str(mcp_path) + ':' + env.get('PYTHONPATH', '')

            # Run pytest with coverage and detailed output
            start_time = time.time()
            cmd = [
                sys.executable, '-m', 'pytest',
                str(test_path),
                '-v',
                '--tb=short',
                '--json-report',
                '--json-report-file=pytest_report.json',
                '--cov=' + str(mcp_path),
                '--cov-report=json',
                '--cov-report=term-missing',
                '--cov-fail-under=90'
            ]

            result = subprocess.run(
                cmd,
                cwd=mcp_path,
                env=env,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            duration = time.time() - start_time

            # Load pytest JSON report
            pytest_report_path = mcp_path / 'pytest_report.json'
            if pytest_report_path.exists():
                with open(pytest_report_path) as f:
                    pytest_data = json.load(f)

                # Load coverage report
                coverage_path = mcp_path / 'coverage.json'
                coverage_data = {}
                if coverage_path.exists():
                    with open(coverage_path) as f:
                        coverage_data = json.load(f)

                return {
                    'status': 'completed',
                    'duration': duration,
                    'return_code': result.returncode,
                    'summary': pytest_data.get('summary', {}),
                    'tests': pytest_data.get('tests', []),
                    'coverage': coverage_data.get('totals', {}),
                    'stdout': result.stdout,
                    'stderr': result.stderr
                }
            else:
                logger.error(f"❌ No pytest report generated for {mcp_name}")
                return {
                    'status': 'failed',
                    'reason': 'no_pytest_report',
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'return_code': result.returncode
                }

        except subprocess.TimeoutExpired:
            logger.error(f"❌ PyTest timeout for {mcp_name}")
            return {'status': 'failed', 'reason': 'timeout'}
        except Exception as e:
            logger.error(f"❌ PyTest error for {mcp_name}: {e}")
            return {'status': 'failed', 'reason': str(e)}

    def evaluate_success_criteria(self, mcp_name: str, validation_result: Dict, pytest_result: Dict) -> Dict[str, Any]:
        """Evaluate if MCP meets 100% success criteria."""
        logger.info(f"📊 Evaluating success criteria for {mcp_name}...")

        evaluation = {
            'mcp_name': mcp_name,
            'timestamp': datetime.utcnow().isoformat(),
            'overall_status': 'FAILED',
            'success_rate': 0.0,
            'criteria_results': {},
            'performance_metrics': {},
            'compliance_status': {},
            'recommendations': []
        }

        # Evaluate validation script results
        if validation_result.get('summary', {}).get('overall_status') == 'PASSED':
            validation_success_rate = validation_result.get('summary', {}).get('success_rate', 0)
            evaluation['criteria_results']['validation_script'] = {
                'status': 'PASSED' if validation_success_rate == 100.0 else 'FAILED',
                'success_rate': validation_success_rate,
                'details': f"Validation script achieved {validation_success_rate}% success rate"
            }
        else:
            evaluation['criteria_results']['validation_script'] = {
                'status': 'FAILED',
                'success_rate': 0.0,
                'details': "Validation script failed or not executed"
            }

        # Evaluate pytest results
        if pytest_result.get('status') == 'completed' and pytest_result.get('return_code') == 0:
            pytest_summary = pytest_result.get('summary', {})
            total_tests = pytest_summary.get('total', 0)
            passed_tests = pytest_summary.get('passed', 0)
            pytest_success_rate = (passed_tests / max(total_tests, 1)) * 100

            evaluation['criteria_results']['pytest_suite'] = {
                'status': 'PASSED' if pytest_success_rate == 100.0 else 'FAILED',
                'success_rate': pytest_success_rate,
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'details': f"PyTest achieved {pytest_success_rate}% success rate ({passed_tests}/{total_tests})"
            }

            # Coverage evaluation
            coverage = pytest_result.get('coverage', {})
            coverage_percent = coverage.get('percent_covered', 0)
            evaluation['criteria_results']['coverage'] = {
                'status': 'PASSED' if coverage_percent >= 90 else 'FAILED',
                'coverage_percent': coverage_percent,
                'details': f"Code coverage: {coverage_percent}%"
            }
        else:
            evaluation['criteria_results']['pytest_suite'] = {
                'status': 'FAILED',
                'success_rate': 0.0,
                'details': "PyTest suite failed or not executed"
            }

        # Performance evaluation
        if 'performance' in validation_result:
            perf_data = validation_result['performance']
            mcp_config = self.available_mcps[mcp_name]
            targets = mcp_config['performance_targets']

            performance_passed = True
            for metric, target in targets.items():
                actual = perf_data.get(f"{metric}_time", perf_data.get(metric.replace('_', '_'), 0))
                if actual > target:
                    performance_passed = False
                    evaluation['recommendations'].append(
                        f"Performance issue: {metric} took {actual}s, target is {target}s"
                    )

            evaluation['criteria_results']['performance'] = {
                'status': 'PASSED' if performance_passed else 'FAILED',
                'details': f"Performance targets {'met' if performance_passed else 'not met'}",
                'metrics': perf_data
            }

        # Calculate overall success
        all_criteria = evaluation['criteria_results']
        total_criteria = len(all_criteria)
        passed_criteria = sum(1 for c in all_criteria.values() if c['status'] == 'PASSED')
        overall_success_rate = (passed_criteria / max(total_criteria, 1)) * 100

        evaluation['overall_status'] = 'PASSED' if overall_success_rate == 100.0 else 'FAILED'
        evaluation['success_rate'] = overall_success_rate

        # Add recommendations for failures
        if overall_success_rate < 100.0:
            evaluation['recommendations'].append("❌ CRITICAL: 100% success rate required for production deployment")
            evaluation['recommendations'].append("🔧 Review failed criteria and fix all issues before proceeding")

        return evaluation

    def test_single_mcp(self, mcp_name: str, performance_only: bool = False) -> Dict[str, Any]:
        """Test a single MCP comprehensively."""
        logger.info(f"🚀 Starting comprehensive testing for {mcp_name}")

        if not self.validate_environment(mcp_name):
            return {
                'status': 'failed',
                'reason': 'environment_validation_failed',
                'mcp_name': mcp_name
            }

        results = {
            'mcp_name': mcp_name,
            'start_time': datetime.utcnow().isoformat(),
            'validation_result': {},
            'pytest_result': {},
            'evaluation': {}
        }

        # Run validation script
        if not performance_only:
            results['validation_result'] = self.run_validation_script(mcp_name)

        # Run pytest suite
        results['pytest_result'] = self.run_pytest_tests(mcp_name)

        # Evaluate success criteria
        results['evaluation'] = self.evaluate_success_criteria(
            mcp_name,
            results['validation_result'],
            results['pytest_result']
        )

        results['end_time'] = datetime.utcnow().isoformat()

        # Log results
        evaluation = results['evaluation']
        status = evaluation['overall_status']
        success_rate = evaluation['success_rate']

        if status == 'PASSED':
            logger.info(f"✅ {mcp_name} PASSED with {success_rate}% success rate")
            self.validated_mcps.append(mcp_name)
        else:
            logger.error(f"❌ {mcp_name} FAILED with {success_rate}% success rate")
            for rec in evaluation.get('recommendations', []):
                logger.error(f"   {rec}")

        return results

    def test_all_mcps(self, performance_only: bool = False) -> Dict[str, Any]:
        """Test all available MCPs."""
        logger.info("🎯 Starting comprehensive testing for ALL MCPs")

        all_results = {
            'test_session': {
                'start_time': datetime.utcnow().isoformat(),
                'total_mcps': len(self.available_mcps),
                'performance_only': performance_only
            },
            'mcp_results': {},
            'summary': {}
        }

        # Test each MCP
        for mcp_name in self.available_mcps.keys():
            logger.info(f"\n{'='*60}")
            logger.info(f"Testing MCP: {mcp_name.upper()}")
            logger.info(f"{'='*60}")

            mcp_result = self.test_single_mcp(mcp_name, performance_only)
            all_results['mcp_results'][mcp_name] = mcp_result

        # Generate summary
        total_mcps = len(self.available_mcps)
        passed_mcps = len(self.validated_mcps)
        overall_success_rate = (passed_mcps / max(total_mcps, 1)) * 100

        all_results['summary'] = {
            'total_mcps_tested': total_mcps,
            'mcps_passed': passed_mcps,
            'mcps_failed': total_mcps - passed_mcps,
            'overall_success_rate': overall_success_rate,
            'overall_status': 'PASSED' if overall_success_rate == 100.0 else 'FAILED',
            'validated_mcps': self.validated_mcps,
            'end_time': datetime.utcnow().isoformat()
        }

        # Log final summary
        logger.info(f"\n{'='*60}")
        logger.info("📊 FINAL TEST SUMMARY")
        logger.info(f"{'='*60}")
        logger.info(f"Total MCPs Tested: {total_mcps}")
        logger.info(f"MCPs Passed: {passed_mcps}")
        logger.info(f"MCPs Failed: {total_mcps - passed_mcps}")
        logger.info(f"Overall Success Rate: {overall_success_rate}%")
        logger.info(f"Overall Status: {all_results['summary']['overall_status']}")

        if self.validated_mcps:
            logger.info(f"✅ Validated MCPs: {', '.join(self.validated_mcps)}")

        return all_results

    def save_comprehensive_report(self, results: Dict[str, Any], output_file: Optional[str] = None):
        """Save comprehensive test results report."""
        if not output_file:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"mcp_test_comprehensive_{timestamp}.json"

        report_path = Path(output_file)
        report_path.parent.mkdir(exist_ok=True)

        with open(report_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)

        logger.info(f"📋 Comprehensive test report saved: {report_path}")
        return report_path


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Execute comprehensive MCP server testing with 100% success criteria"
    )
    parser.add_argument(
        '--mcp',
        required=True,
        help="MCP to test (logfire, context7, memory, pytest, all)"
    )
    parser.add_argument(
        '--performance-only',
        action='store_true',
        help="Run only performance tests (skip validation scripts)"
    )
    parser.add_argument(
        '--output',
        help="Output file for comprehensive report (default: auto-generated)"
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Initialize test executor
    executor = MCPTestExecutor()

    # Execute tests
    if args.mcp == 'all':
        results = executor.test_all_mcps(args.performance_only)
    else:
        if args.mcp not in executor.available_mcps:
            logger.error(f"❌ Unknown MCP: {args.mcp}")
            logger.error(f"Available MCPs: {', '.join(executor.available_mcps.keys())}")
            return 1

        single_result = executor.test_single_mcp(args.mcp, args.performance_only)
        results = {
            'test_session': {
                'start_time': single_result.get('start_time'),
                'total_mcps': 1,
                'performance_only': args.performance_only
            },
            'mcp_results': {args.mcp: single_result},
            'summary': {
                'total_mcps_tested': 1,
                'mcps_passed': 1 if single_result['evaluation']['overall_status'] == 'PASSED' else 0,
                'mcps_failed': 0 if single_result['evaluation']['overall_status'] == 'PASSED' else 1,
                'overall_success_rate': single_result['evaluation']['success_rate'],
                'overall_status': single_result['evaluation']['overall_status'],
                'end_time': single_result.get('end_time')
            }
        }

    # Save comprehensive report
    executor.save_comprehensive_report(results, args.output)

    # Return appropriate exit code
    overall_status = results['summary']['overall_status']
    if overall_status == 'PASSED':
        logger.info("🎉 ALL TESTS PASSED - MCPs ready for production!")
        return 0
    else:
        logger.error("💥 TESTS FAILED - Review failures before proceeding")
        return 1


if __name__ == "__main__":
    exit(main())
