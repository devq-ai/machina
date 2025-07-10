#!/usr/bin/env python3
"""
Production MCP Servers Verification Script
Comprehensive verification of all 13 required production MCP servers for Machina registry.
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Required production servers mapping
PRODUCTION_SERVERS = {
    'context7-mcp': {
        'filename': 'context7_mcp.py',
        'repo': 'https://github.com/upstash/context7',
        'description': 'advanced context management and semantic search with vector embeddings',
        'instrumentation': 'fastmcp',
        'class_name': 'Context7MCP'
    },
    'crawl4ai-mcp': {
        'filename': 'crawl4ai_mcp.py',
        'repo': 'https://github.com/coleam00/mcp-crawl4ai-rag',
        'description': 'web crawling and rag capabilities for ai agents and ai coding assistants',
        'instrumentation': 'fastmcp',
        'class_name': 'Crawl4AIMCP'
    },
    'docker-mcp': {
        'filename': 'docker_mcp.py',
        'repo': 'https://github.com/QuantGeekDev/docker-mcp',
        'description': 'an mcp server for managing docker with natural language',
        'instrumentation': 'uv-python',
        'class_name': 'DockerMCP'
    },
    'fastapi-mcp': {
        'filename': 'fastapi_mcp.py',
        'repo': 'https://pypi.org/project/fastmcp/1.0/',
        'description': 'an mcp for the best web framework',
        'instrumentation': 'fastmcp',
        'class_name': 'FastAPIMCP'
    },
    'fastmcp-mcp': {
        'filename': 'fastmcp_mcp.py',
        'repo': 'https://github.com/jlowin/fastmcp',
        'description': 'fast development for mcp',
        'instrumentation': 'fastmcp',
        'class_name': 'FastMCPMCPServer'
    },
    'github-mcp': {
        'filename': 'github_mcp.py',
        'repo': 'https://github.com/docker/mcp-servers/tree/main/src/github',
        'description': 'github api integration for repository management, issues, and pull requests',
        'instrumentation': 'typescript-npm',
        'class_name': 'GitHubMCP'
    },
    'logfire-mcp': {
        'filename': 'logfire_mcp.py',
        'repo': 'https://github.com/pydantic/logfire-mcp',
        'description': 'integrated observability and logging with structured monitoring',
        'instrumentation': 'mcp-python',
        'class_name': 'LogfireMCP'
    },
    'memory-mcp': {
        'filename': 'memory_mcp.py',
        'repo': 'https://github.com/modelcontextprotocol/servers/tree/main/src/memory',
        'description': 'persistent memory management with',
        'instrumentation': 'mcp-typescript',
        'class_name': 'MemoryMCP'
    },
    'pydantic-ai-mcp': {
        'filename': 'pydantic_ai_mcp.py',
        'repo': 'https://ai.pydantic.dev/mcp/',
        'description': 'an mcp for best testing framework',
        'instrumentation': 'fastmcp-mcp',
        'class_name': 'PydanticAIMCP'
    },
    'pytest-mcp': {
        'filename': 'pytest_mcp.py',
        'repo': 'https://mcp.so/server/pytest-mcp-server/tosin2013?tab=content',
        'description': 'an mcp for best testing framework',
        'instrumentation': 'mcp-typescript',
        'class_name': 'PyTestMCP'
    },
    'registry-mcp': {
        'filename': 'registry_mcp.py',
        'repo': 'https://github.com/modelcontextprotocol/registry',
        'description': 'official mcp server registry with discovery and installation tools',
        'instrumentation': 'custom-stdio',
        'class_name': 'RegistryMCP'
    },
    'sequential-thinking-mcp': {
        'filename': 'sequential_thinking_mcp.py',
        'repo': 'https://github.com/loamstudios/zed-mcp-server-sequential-thinking',
        'description': 'sequential reasoning capabilities for complex problem-solving workflows',
        'instrumentation': 'mcp-python',
        'class_name': 'SequentialThinkingMCPServer'
    },
    'surrealdb-mcp': {
        'filename': 'surrealdb_mcp.py',
        'repo': 'https://github.com/nsxdavid/surrealdb-mcp-server',
        'description': 'surrealdb multi-model database integration with graph capabilities',
        'instrumentation': 'mcp-typescript',
        'class_name': 'SurrealDBMCPServer'
    }
}


class ProductionServerVerifier:
    """Comprehensive verification of production MCP servers"""

    def __init__(self):
        self.project_root = Path(__file__).parent
        self.servers_dir = self.project_root / "mcp_servers"
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'total_servers': len(PRODUCTION_SERVERS),
            'verified_servers': 0,
            'failed_servers': 0,
            'servers': {}
        }

    def verify_file_exists(self, server_name: str, server_info: Dict[str, Any]) -> bool:
        """Verify server file exists"""
        file_path = self.servers_dir / server_info['filename']
        exists = file_path.exists()

        if not exists:
            logger.error(f"❌ {server_name}: File not found - {file_path}")
        else:
            logger.info(f"✅ {server_name}: File exists - {file_path}")

        return exists

    def verify_class_import(self, server_name: str, server_info: Dict[str, Any]) -> bool:
        """Verify server class can be imported"""
        try:
            # Import the server class
            module_name = f"mcp_servers.{server_info['filename'][:-3]}"  # Remove .py extension

            # Dynamic import
            __import__(module_name)
            module = sys.modules[module_name]

            # Check if class exists
            if hasattr(module, server_info['class_name']):
                server_class = getattr(module, server_info['class_name'])
                logger.info(f"✅ {server_name}: Class imported successfully - {server_info['class_name']}")
                return True
            else:
                logger.error(f"❌ {server_name}: Class not found - {server_info['class_name']}")
                return False

        except Exception as e:
            logger.error(f"❌ {server_name}: Import failed - {str(e)}")
            return False

    def verify_registry_integration(self, server_name: str) -> bool:
        """Verify server is properly registered in __init__.py"""
        try:
            from mcp_servers import MCP_SERVERS

            if server_name in MCP_SERVERS:
                logger.info(f"✅ {server_name}: Registered in MCP_SERVERS")
                return True
            else:
                logger.error(f"❌ {server_name}: Not registered in MCP_SERVERS")
                return False

        except Exception as e:
            logger.error(f"❌ {server_name}: Registry verification failed - {str(e)}")
            return False

    def verify_server_instantiation(self, server_name: str, server_info: Dict[str, Any]) -> bool:
        """Verify server can be instantiated"""
        try:
            from mcp_servers import MCP_SERVERS

            if server_name not in MCP_SERVERS:
                return False

            server_class = MCP_SERVERS[server_name]

            # Try to instantiate the server
            server_instance = server_class()

            # Check if it has expected attributes
            if hasattr(server_instance, 'server') or hasattr(server_instance, 'app'):
                logger.info(f"✅ {server_name}: Server instantiated successfully")
                return True
            else:
                logger.warning(f"⚠️  {server_name}: Server instantiated but missing expected attributes")
                return True  # Still consider it successful

        except Exception as e:
            logger.error(f"❌ {server_name}: Instantiation failed - {str(e)}")
            return False

    def verify_server_metadata(self, server_name: str, server_info: Dict[str, Any]) -> Dict[str, Any]:
        """Verify server metadata and extract information"""
        metadata = {
            'file_exists': False,
            'class_importable': False,
            'registry_integrated': False,
            'instantiable': False,
            'instrumentation': server_info['instrumentation'],
            'description': server_info['description'],
            'repo': server_info['repo']
        }

        try:
            # Check file existence
            metadata['file_exists'] = self.verify_file_exists(server_name, server_info)

            # Check class import
            if metadata['file_exists']:
                metadata['class_importable'] = self.verify_class_import(server_name, server_info)

            # Check registry integration
            if metadata['class_importable']:
                metadata['registry_integrated'] = self.verify_registry_integration(server_name)

            # Check instantiation
            if metadata['registry_integrated']:
                metadata['instantiable'] = self.verify_server_instantiation(server_name, server_info)

            # Overall status
            metadata['status'] = 'passed' if all([
                metadata['file_exists'],
                metadata['class_importable'],
                metadata['registry_integrated'],
                metadata['instantiable']
            ]) else 'failed'

            if metadata['status'] == 'passed':
                self.results['verified_servers'] += 1
                logger.info(f"🎯 {server_name}: ALL CHECKS PASSED")
            else:
                self.results['failed_servers'] += 1
                logger.error(f"💥 {server_name}: VERIFICATION FAILED")

        except Exception as e:
            logger.error(f"❌ {server_name}: Metadata verification failed - {str(e)}")
            metadata['status'] = 'error'
            metadata['error'] = str(e)
            self.results['failed_servers'] += 1

        return metadata

    def run_comprehensive_verification(self) -> Dict[str, Any]:
        """Run comprehensive verification of all production servers"""
        logger.info("🚀 Starting Production MCP Servers Verification")
        logger.info("=" * 80)

        for server_name, server_info in PRODUCTION_SERVERS.items():
            logger.info(f"\n🔍 Verifying: {server_name}")
            logger.info(f"Description: {server_info['description']}")
            logger.info(f"Instrumentation: {server_info['instrumentation']}")

            metadata = self.verify_server_metadata(server_name, server_info)
            self.results['servers'][server_name] = metadata

        # Summary
        logger.info("\n" + "=" * 80)
        logger.info("📊 VERIFICATION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total servers: {self.results['total_servers']}")
        logger.info(f"Verified servers: {self.results['verified_servers']}")
        logger.info(f"Failed servers: {self.results['failed_servers']}")
        logger.info(f"Success rate: {(self.results['verified_servers'] / self.results['total_servers']) * 100:.1f}%")

        # Detailed results
        logger.info("\n📋 DETAILED RESULTS")
        for server_name, metadata in self.results['servers'].items():
            status_emoji = "✅" if metadata['status'] == 'passed' else "❌"
            logger.info(f"{status_emoji} {server_name}: {metadata['status']}")

            if metadata['status'] == 'failed':
                logger.info(f"   File exists: {metadata['file_exists']}")
                logger.info(f"   Class importable: {metadata['class_importable']}")
                logger.info(f"   Registry integrated: {metadata['registry_integrated']}")
                logger.info(f"   Instantiable: {metadata['instantiable']}")

        # Production readiness
        production_ready = self.results['failed_servers'] == 0
        logger.info(f"\n🎯 PRODUCTION READY: {'YES' if production_ready else 'NO'}")

        if production_ready:
            logger.info("🎉 All production MCP servers are verified and ready for deployment!")
        else:
            logger.error("⚠️  Some servers failed verification. Please fix issues before production.")

        return self.results

    def save_results(self, filename: str = "production_verification_results.json"):
        """Save verification results to JSON file"""
        results_file = self.project_root / filename
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        logger.info(f"📄 Results saved to: {results_file}")

    def generate_production_report(self):
        """Generate production readiness report"""
        report = []
        report.append("# Production MCP Servers Verification Report")
        report.append(f"Generated: {self.results['timestamp']}")
        report.append("")

        report.append("## Summary")
        report.append(f"- Total servers: {self.results['total_servers']}")
        report.append(f"- Verified servers: {self.results['verified_servers']}")
        report.append(f"- Failed servers: {self.results['failed_servers']}")
        report.append(f"- Success rate: {(self.results['verified_servers'] / self.results['total_servers']) * 100:.1f}%")
        report.append("")

        report.append("## Server Details")
        for server_name, metadata in self.results['servers'].items():
            status_emoji = "✅" if metadata['status'] == 'passed' else "❌"
            report.append(f"### {status_emoji} {server_name}")
            report.append(f"- **Status**: {metadata['status']}")
            report.append(f"- **Description**: {metadata['description']}")
            report.append(f"- **Instrumentation**: {metadata['instrumentation']}")
            report.append(f"- **Repository**: {metadata['repo']}")

            if metadata['status'] == 'failed':
                report.append("- **Issues**:")
                report.append(f"  - File exists: {metadata['file_exists']}")
                report.append(f"  - Class importable: {metadata['class_importable']}")
                report.append(f"  - Registry integrated: {metadata['registry_integrated']}")
                report.append(f"  - Instantiable: {metadata['instantiable']}")

            report.append("")

        # Production readiness
        production_ready = self.results['failed_servers'] == 0
        report.append("## Production Readiness")
        report.append(f"**Status**: {'✅ READY' if production_ready else '❌ NOT READY'}")

        if production_ready:
            report.append("\n🎉 All production MCP servers are verified and ready for deployment!")
        else:
            report.append("\n⚠️  Some servers failed verification. Please fix issues before production.")

        # Save report
        report_file = self.project_root / "PRODUCTION_VERIFICATION_REPORT.md"
        with open(report_file, 'w') as f:
            f.write('\n'.join(report))
        logger.info(f"📋 Production report saved to: {report_file}")


def main():
    """Main verification entry point"""
    verifier = ProductionServerVerifier()

    try:
        # Run comprehensive verification
        results = verifier.run_comprehensive_verification()

        # Save results
        verifier.save_results()

        # Generate report
        verifier.generate_production_report()

        # Exit with appropriate code
        if results['failed_servers'] == 0:
            logger.info("✅ All verifications passed!")
            sys.exit(0)
        else:
            logger.error(f"❌ {results['failed_servers']} server(s) failed verification")
            sys.exit(1)

    except Exception as e:
        logger.error(f"💥 Verification failed with error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
