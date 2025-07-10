#!/usr/bin/env python3
"""
Actual MCP Tool Testing Script
Makes REAL MCP tool calls using FastMCP framework - NO FAKE/MOCK/STUB RESPONSES

This script demonstrates actual tool functionality by:
1. Importing and instantiating real MCP servers
2. Making actual tool calls through the FastMCP framework
3. Capturing authentic responses from tools performing their business logic
4. Providing real verification of tool functionality

ZERO TOLERANCE FOR FAKE DATA - All responses are from actual tool execution.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, Any, List
import traceback
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Import actual MCP servers
from mcp_servers.logfire_mcp import LogfireMCP
from mcp_servers.fastapi_mcp import FastAPIMCP
from mcp_servers.pytest_mcp import PyTestMCP
from mcp_servers.github_mcp import GitHubMCP
from mcp_servers.memory_mcp import MemoryMCP
from mcp_servers.docker_mcp import DockerMCP
from mcp_servers.registry_mcp import RegistryMCP

import logfire

# Configure logging
logfire.configure()

class ActualMCPTester:
    """
    Actual MCP Tool Tester

    Makes REAL tool calls to verify functionality.
    NO FAKE/MOCK/STUB RESPONSES PERMITTED.
    """

    def __init__(self):
        self.servers = {}
        self.results = {}
        self.start_time = datetime.now()

    async def initialize_servers(self):
        """Initialize actual MCP servers"""
        server_classes = {
            'logfire': LogfireMCP,
            'fastapi': FastAPIMCP,
            'pytest': PyTestMCP,
            'github': GitHubMCP,
            'memory': MemoryMCP,
            'docker': DockerMCP,
            'registry': RegistryMCP
        }

        for name, server_class in server_classes.items():
            try:
                with logfire.span(f"Initialize {name} server"):
                    self.servers[name] = server_class()
                    logfire.info(f"Successfully initialized {name} MCP server")
            except Exception as e:
                logfire.error(f"Failed to initialize {name} server: {str(e)}")
                self.servers[name] = None

    async def test_tool_call(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make an ACTUAL tool call to a real MCP server

        Returns:
            Dict with actual response data or error information
        """
        server = self.servers.get(server_name)
        if not server:
            return {
                "error": f"Server {server_name} not available",
                "server_available": False,
                "timestamp": datetime.now().isoformat()
            }

        try:
            with logfire.span(f"Tool call: {server_name}.{tool_name}", arguments=arguments):
                # Make actual tool call through FastMCP framework
                if hasattr(server, 'mcp') and hasattr(server.mcp, '_tools'):
                    tool_func = server.mcp._tools.get(tool_name)
                    if tool_func:
                        # Execute the actual tool function
                        if asyncio.iscoroutinefunction(tool_func):
                            result = await tool_func(**arguments)
                        else:
                            result = await asyncio.get_event_loop().run_in_executor(None, lambda: tool_func(**arguments))

                        logfire.info(f"Tool call successful: {server_name}.{tool_name}")
                        return {
                            "success": True,
                            "result": result,
                            "server_name": server_name,
                            "tool_name": tool_name,
                            "arguments": arguments,
                            "timestamp": datetime.now().isoformat(),
                            "response_type": type(result).__name__
                        }
                    else:
                        return {
                            "error": f"Tool {tool_name} not found in server {server_name}",
                            "available_tools": list(server.mcp._tools.keys()) if hasattr(server, 'mcp') else [],
                            "timestamp": datetime.now().isoformat()
                        }
                else:
                    return {
                        "error": f"Server {server_name} does not use FastMCP framework",
                        "server_type": type(server).__name__,
                        "timestamp": datetime.now().isoformat()
                    }

        except Exception as e:
            logfire.error(f"Tool call failed: {server_name}.{tool_name}", error=str(e))
            return {
                "error": f"Tool call failed: {str(e)}",
                "server_name": server_name,
                "tool_name": tool_name,
                "arguments": arguments,
                "timestamp": datetime.now().isoformat(),
                "traceback": traceback.format_exc()
            }

    async def get_server_info(self, server_name: str) -> Dict[str, Any]:
        """Get actual server information"""
        server = self.servers.get(server_name)
        if not server:
            return {"error": f"Server {server_name} not available"}

        try:
            if hasattr(server, 'mcp') and hasattr(server.mcp, 'get_tool_info'):
                return await asyncio.get_event_loop().run_in_executor(None, server.mcp.get_tool_info)
            else:
                return {
                    "server_name": server_name,
                    "server_type": type(server).__name__,
                    "tools": getattr(server, '_tools', {}).keys() if hasattr(server, '_tools') else [],
                    "framework": "Unknown"
                }
        except Exception as e:
            return {
                "error": f"Failed to get server info: {str(e)}",
                "server_name": server_name
            }

    async def run_comprehensive_tests(self):
        """Run comprehensive tests with actual tool calls"""

        # Initialize servers
        await self.initialize_servers()

        # Test configurations for actual tool calls using correct tool names
        test_configs = {
            'logfire': [
                {
                    'tool': 'get_project_info',
                    'args': {}
                },
                {
                    'tool': 'query_logs',
                    'args': {'limit': 5}
                }
            ],
            'fastapi': [
                {
                    'tool': 'create_project',
                    'args': {'name': 'test_project', 'description': 'Test FastAPI project'}
                },
                {
                    'tool': 'add_endpoint',
                    'args': {'project_name': 'test_project', 'endpoint_name': 'test_endpoint', 'method': 'GET'}
                }
            ],
            'pytest': [
                {
                    'tool': 'run_tests',
                    'args': {'test_path': 'tests/', 'verbose': True}
                },
                {
                    'tool': 'generate_test_file',
                    'args': {'file_path': 'test_example.py', 'function_name': 'test_example'}
                }
            ],
            'github': [
                {
                    'tool': 'get_user_info',
                    'args': {'username': 'testuser'}
                }
            ],
            'memory': [
                {
                    'tool': 'store_memory',
                    'args': {'content': 'test_content', 'context': 'test_context', 'tags': ['test']}
                },
                {
                    'tool': 'get_memory_stats',
                    'args': {}
                }
            ],
            'docker': [
                {
                    'tool': 'list_containers',
                    'args': {}
                },
                {
                    'tool': 'get_system_info',
                    'args': {}
                }
            ],
            'registry': [
                {
                    'tool': 'search_servers',
                    'args': {'query': 'test'}
                },
                {
                    'tool': 'get_registry_stats',
                    'args': {}
                }
            ]
        }

        # Execute actual tool calls
        for server_name, tests in test_configs.items():
            logfire.info(f"Testing server: {server_name}")

            # Get server info
            server_info = await self.get_server_info(server_name)

            # Initialize results for this server
            self.results[server_name] = {
                'server_info': server_info,
                'tool_calls': [],
                'server_available': server_name in self.servers and self.servers[server_name] is not None
            }

            # Execute tool calls
            for test_config in tests:
                tool_name = test_config['tool']
                args = test_config['args']

                logfire.info(f"Testing {server_name}.{tool_name}")
                result = await self.test_tool_call(server_name, tool_name, args)
                self.results[server_name]['tool_calls'].append(result)

    def generate_report(self) -> str:
        """Generate comprehensive report of actual tool testing"""

        report = []
        report.append("# ACTUAL MCP TOOL TESTING REPORT")
        report.append("## REAL TOOL CALLS WITH AUTHENTIC RESPONSES")
        report.append("")
        report.append("This report contains ONLY actual tool call results.")
        report.append("NO FAKE/MOCK/STUB RESPONSES - All data is from real tool execution.")
        report.append("")
        report.append(f"Test execution time: {datetime.now() - self.start_time}")
        report.append(f"Total servers tested: {len(self.results)}")
        report.append("")

        # Summary statistics
        total_tools = 0
        successful_calls = 0
        failed_calls = 0

        for server_name, server_results in self.results.items():
            total_tools += len(server_results['tool_calls'])
            for call in server_results['tool_calls']:
                if call.get('success', False):
                    successful_calls += 1
                else:
                    failed_calls += 1

        report.append("## SUMMARY")
        report.append(f"- Total tool calls: {total_tools}")
        report.append(f"- Successful calls: {successful_calls}")
        report.append(f"- Failed calls: {failed_calls}")
        report.append(f"- Success rate: {(successful_calls/total_tools*100):.1f}%" if total_tools > 0 else "- Success rate: 0%")
        report.append("")

        # Detailed results per server
        for server_name, server_results in self.results.items():
            report.append(f"## {server_name.upper()} MCP SERVER")
            report.append(f"**Server Available:** {'✅' if server_results['server_available'] else '❌'}")
            report.append("")

            # Server info
            server_info = server_results['server_info']
            if 'error' not in server_info:
                report.append("### Server Information")
                report.append(f"- **Name:** {server_info.get('server_name', 'Unknown')}")
                report.append(f"- **Version:** {server_info.get('server_version', 'Unknown')}")
                report.append(f"- **Tools:** {server_info.get('tool_count', 0)}")
                report.append(f"- **Framework:** {server_info.get('framework', 'FastMCP')}")

                if 'tools' in server_info:
                    report.append("- **Available Tools:**")
                    for tool in server_info['tools']:
                        if isinstance(tool, dict):
                            report.append(f"  - {tool.get('name', 'Unknown')}: {tool.get('description', 'No description')}")
                        else:
                            report.append(f"  - {tool}")
            else:
                report.append(f"### Server Error: {server_info['error']}")

            report.append("")

            # Tool call results
            report.append("### Tool Call Results")
            for i, call_result in enumerate(server_results['tool_calls'], 1):
                if call_result.get('success', False):
                    report.append(f"**{i}. ✅ {call_result['tool_name']}**")
                    report.append(f"   - **Arguments:** {json.dumps(call_result['arguments'], indent=2)}")
                    report.append(f"   - **Response Type:** {call_result.get('response_type', 'Unknown')}")
                    report.append(f"   - **Timestamp:** {call_result['timestamp']}")

                    # Show actual result (truncated if too long)
                    result_str = str(call_result['result'])
                    if len(result_str) > 500:
                        result_str = result_str[:500] + "... (truncated)"
                    report.append(f"   - **Actual Result:** {result_str}")
                else:
                    report.append(f"**{i}. ❌ {call_result.get('tool_name', 'Unknown')}**")
                    report.append(f"   - **Error:** {call_result.get('error', 'Unknown error')}")
                    report.append(f"   - **Arguments:** {json.dumps(call_result.get('arguments', {}), indent=2)}")
                    report.append(f"   - **Timestamp:** {call_result.get('timestamp', 'Unknown')}")

                    if 'available_tools' in call_result:
                        report.append(f"   - **Available Tools:** {call_result['available_tools']}")

                report.append("")

        report.append("## VERIFICATION STATEMENT")
        report.append("")
        report.append("This report contains ONLY actual tool execution results.")
        report.append("Every tool call was made through the FastMCP framework.")
        report.append("NO SIMULATED, FAKE, MOCK, OR STUB RESPONSES.")
        report.append("All data represents real tool functionality and authentic responses.")
        report.append("")
        report.append("Generated: " + datetime.now().isoformat())

        return "\n".join(report)

    async def save_results(self, filename: str = "actual_mcp_tool_results.json"):
        """Save raw results to JSON file"""
        with open(filename, 'w') as f:
            json.dump({
                'test_metadata': {
                    'execution_time': datetime.now().isoformat(),
                    'duration': str(datetime.now() - self.start_time),
                    'total_servers': len(self.results)
                },
                'results': self.results
            }, f, indent=2, default=str)

        logfire.info(f"Results saved to {filename}")

async def main():
    """Main execution function"""
    logfire.info("Starting ACTUAL MCP tool testing")

    tester = ActualMCPTester()

    try:
        # Run comprehensive tests with actual tool calls
        await tester.run_comprehensive_tests()

        # Generate and save report
        report = tester.generate_report()

        # Save to file
        with open("ACTUAL_MCP_TOOL_REPORT.md", "w") as f:
            f.write(report)

        # Save raw results
        await tester.save_results("actual_mcp_tool_results.json")

        print("✅ ACTUAL MCP TOOL TESTING COMPLETED")
        print("📄 Report saved to: ACTUAL_MCP_TOOL_REPORT.md")
        print("📊 Raw data saved to: actual_mcp_tool_results.json")

        logfire.info("ACTUAL MCP tool testing completed successfully")

    except Exception as e:
        logfire.error(f"Testing failed: {str(e)}")
        print(f"❌ Testing failed: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
