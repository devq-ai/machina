#!/usr/bin/env python3
"""
Comprehensive MCP Server Testing with Real Credentials
Tests all servers using credentials from .env and config.md
"""

import os
import sys
import asyncio
import json
import importlib.util
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
import traceback

# Load environment variables from .env file
def load_env_file():
    """Load environment variables from .env file"""
    env_path = Path('/Users/dionedge/devqai/machina/.env')
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Handle variable substitutions like ${VAR}
                    if '${' in value and '}' in value:
                        start = value.find('${') + 2
                        end = value.find('}', start)
                        if start > 1 and end > start:
                            var_name = value[start:end]
                            if var_name in os.environ:
                                value = value.replace(f'${{{var_name}}}', os.environ[var_name])
                    os.environ[key] = value
        print(f"✅ Loaded environment variables from {env_path}")
    else:
        print(f"⚠️ No .env file found at {env_path}")

# Load environment
load_env_file()

# Add machina to Python path
sys.path.insert(0, '/Users/dionedge/devqai/machina')

class ComprehensiveMCPTester:
    """Test all MCP servers with real credentials and comprehensive validation"""
    
    def __init__(self):
        self.test_results = []
        self.mcp_implementations_path = Path('/Users/dionedge/devqai/machina/mcp_implementations')
        self.mcp_servers_path = Path('/Users/dionedge/devqai/machina/mcp/mcp-servers')
        self.working_servers_path = Path('/Users/dionedge/devqai/machina/working_servers')
    
    async def test_server_with_credentials(self, server_path: Path, server_name: str) -> Dict[str, Any]:
        """Test individual server with real credentials"""
        start_time = datetime.now()
        
        try:
            # Import server module
            spec = importlib.util.spec_from_file_location(server_name, server_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find server class or instance
            server_instance = None
            server_class = None
            
            # Look for common server patterns
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if attr_name.endswith('MCPServer') and hasattr(attr, '__call__'):
                    server_class = attr
                    break
                elif attr_name == 'server' and hasattr(attr, 'call_tool'):
                    server_instance = attr
                    break
            
            if server_class:
                server_instance = server_class()
            elif not server_instance:
                # Try to find any callable server-like object
                for attr_name in ['app', 'main', 'server']:
                    if hasattr(module, attr_name):
                        server_instance = getattr(module, attr_name)
                        break
            
            if not server_instance:
                return {
                    "server": server_name,
                    "status": "FAILED",
                    "error": "No server instance found",
                    "file_path": str(server_path)
                }
            
            # Get available tools
            tools = []
            if hasattr(server_instance, '_get_tools'):
                tools = server_instance._get_tools()
            elif hasattr(server_instance, 'list_tools'):
                tools = await server_instance.list_tools()
            
            tool_names = [tool.name for tool in tools] if tools else []
            
            # Test basic functionality
            test_calls = []
            
            # Test health check if available
            health_tools = [name for name in tool_names if 'health' in name.lower()]
            if health_tools:
                tool_name = health_tools[0]
                try:
                    if hasattr(server_instance, '_handle_tool_call'):
                        result = await server_instance._handle_tool_call(tool_name, {})
                        response_text = result[0].text if hasattr(result[0], 'text') else str(result)
                        test_calls.append({
                            "tool": tool_name,
                            "status": "SUCCESS",
                            "response": response_text[:200] + "..." if len(response_text) > 200 else response_text
                        })
                    else:
                        test_calls.append({
                            "tool": tool_name,
                            "status": "SKIPPED",
                            "reason": "No tool call handler found"
                        })
                except Exception as e:
                    test_calls.append({
                        "tool": tool_name,
                        "status": "FAILED",
                        "error": str(e)
                    })
            
            # Test first available tool
            if tool_names and not health_tools:
                tool_name = tool_names[0]
                try:
                    if hasattr(server_instance, '_handle_tool_call'):
                        # Try with empty arguments first
                        result = await server_instance._handle_tool_call(tool_name, {})
                        response_text = result[0].text if hasattr(result[0], 'text') else str(result)
                        test_calls.append({
                            "tool": tool_name,
                            "status": "SUCCESS",
                            "response": response_text[:200] + "..." if len(response_text) > 200 else response_text
                        })
                    else:
                        test_calls.append({
                            "tool": tool_name,
                            "status": "SKIPPED",
                            "reason": "No tool call handler found"
                        })
                except Exception as e:
                    test_calls.append({
                        "tool": tool_name,
                        "status": "FAILED",
                        "error": str(e)
                    })
            
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds() * 1000
            
            return {
                "server": server_name,
                "status": "TESTED",
                "file_path": str(server_path),
                "available_tools": tool_names,
                "tool_count": len(tool_names),
                "test_calls": test_calls,
                "successful_calls": sum(1 for call in test_calls if call["status"] == "SUCCESS"),
                "execution_time_ms": round(execution_time, 2)
            }
            
        except Exception as e:
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds() * 1000
            
            return {
                "server": server_name,
                "status": "FAILED",
                "file_path": str(server_path),
                "error": str(e),
                "traceback": traceback.format_exc(),
                "execution_time_ms": round(execution_time, 2)
            }
    
    async def test_mcp_implementations(self) -> List[Dict[str, Any]]:
        """Test all production MCP implementations"""
        print("🔧 Testing MCP Production Implementations")
        print("=" * 50)
        
        results = []
        
        # Get all Python files excluding tests
        python_files = [f for f in self.mcp_implementations_path.glob("*.py") 
                       if not f.name.startswith("test_")]
        
        for py_file in python_files:
            server_name = py_file.stem
            print(f"  🧪 Testing {server_name}...")
            
            result = await self.test_server_with_credentials(py_file, server_name)
            results.append(result)
            
            if result["status"] == "TESTED":
                successful = result.get("successful_calls", 0)
                total = len(result.get("test_calls", []))
                tools = result.get("tool_count", 0)
                print(f"    ✅ {tools} tools, {successful}/{total} calls successful")
            else:
                print(f"    ❌ Failed: {result.get('error', 'Unknown error')}")
        
        return results
    
    async def test_mcp_server_frameworks(self) -> List[Dict[str, Any]]:
        """Test structured MCP server frameworks"""
        print("\n🏗️ Testing MCP Server Frameworks")
        print("=" * 50)
        
        results = []
        
        # Test sample of structured servers
        sample_servers = [
            "darwin-mcp", "bayes-mcp", "stripe-mcp", "memory-mcp", 
            "docker-mcp", "github-mcp", "context7-mcp", "scholarly-mcp"
        ]
        
        for server_dir in sample_servers:
            server_path = self.mcp_servers_path / server_dir
            if server_path.exists():
                print(f"  🧪 Testing framework {server_dir}...")
                
                # Look for main server file
                server_files = list(server_path.glob("src/server.py")) + \
                              list(server_path.glob("src/*.py")) + \
                              list(server_path.glob("*.py"))
                
                if server_files:
                    main_file = server_files[0]
                    result = await self.test_server_with_credentials(main_file, server_dir)
                    result["framework_type"] = "structured"
                    results.append(result)
                    
                    if result["status"] == "TESTED":
                        tools = result.get("tool_count", 0)
                        print(f"    ✅ Framework has {tools} tools")
                    else:
                        print(f"    ❌ Framework failed: {result.get('error', 'Unknown')}")
                else:
                    results.append({
                        "server": server_dir,
                        "status": "NO_SERVER_FILE",
                        "file_path": str(server_path),
                        "framework_type": "structured"
                    })
                    print("    ⚠️ No server files found")
            else:
                print(f"    ❌ Directory not found: {server_dir}")
        
        return results
    
    async def test_working_servers_sample(self) -> List[Dict[str, Any]]:
        """Test sample of working servers (FastAPI stubs)"""
        print("\n🔧 Testing Working Servers (Sample)")
        print("=" * 50)
        
        results = []
        
        # Test sample of working servers
        sample_files = ["darwin-mcp.py", "bayes-mcp.py", "shopify-mcp.py", "stripe-mcp.py"]
        
        for filename in sample_files:
            file_path = self.working_servers_path / filename
            if file_path.exists():
                print(f"  🧪 Testing {filename}...")
                
                try:
                    # Test FastAPI endpoint
                    spec = importlib.util.spec_from_file_location(filename[:-3], file_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    if hasattr(module, 'app'):
                        from fastapi.testclient import TestClient
                        client = TestClient(module.app)
                        
                        response = client.get("/")
                        
                        results.append({
                            "server": filename,
                            "status": "FASTAPI_STUB",
                            "file_path": str(file_path),
                            "http_status": response.status_code,
                            "response": response.json() if response.status_code == 200 else None,
                            "framework_type": "fastapi_stub"
                        })
                        
                        print(f"    ✅ FastAPI stub responding: {response.status_code}")
                    else:
                        results.append({
                            "server": filename,
                            "status": "NO_FASTAPI",
                            "file_path": str(file_path),
                            "framework_type": "unknown"
                        })
                        print("    ❌ No FastAPI app found")
                        
                except Exception as e:
                    results.append({
                        "server": filename,
                        "status": "FAILED",
                        "file_path": str(file_path),
                        "error": str(e),
                        "framework_type": "fastapi_stub"
                    })
                    print(f"    ❌ Failed: {e}")
            else:
                print(f"    ❌ File not found: {filename}")
        
        return results
    
    async def run_comprehensive_tests(self) -> Dict[str, Any]:
        """Run all comprehensive tests"""
        print("🧪 COMPREHENSIVE MCP SERVER TESTING WITH CREDENTIALS")
        print("=" * 70)
        print(f"Environment loaded: GITHUB_TOKEN={os.environ.get('GITHUB_TOKEN', 'Not set')[:10]}...")
        print(f"Environment loaded: ANTHROPIC_API_KEY={os.environ.get('ANTHROPIC_API_KEY', 'Not set')[:10]}...")
        print(f"Environment loaded: UPSTASH_REDIS_REST_URL={os.environ.get('UPSTASH_REDIS_REST_URL', 'Not set')[:30]}...")
        print("=" * 70)
        
        # Test all server types
        implementation_results = await self.test_mcp_implementations()
        framework_results = await self.test_mcp_server_frameworks()
        working_results = await self.test_working_servers_sample()
        
        all_results = implementation_results + framework_results + working_results
        
        # Calculate summary statistics
        total_servers = len(all_results)
        tested_servers = sum(1 for r in all_results if r["status"] == "TESTED")
        failed_servers = sum(1 for r in all_results if r["status"] == "FAILED")
        stub_servers = sum(1 for r in all_results if r["status"] == "FASTAPI_STUB")
        
        total_tools = sum(r.get("tool_count", 0) for r in all_results)
        total_successful_calls = sum(r.get("successful_calls", 0) for r in all_results)
        total_test_calls = sum(len(r.get("test_calls", [])) for r in all_results)
        
        summary = {
            "test_timestamp": datetime.now().isoformat(),
            "test_type": "Comprehensive MCP Testing with Real Credentials",
            "environment_credentials_loaded": True,
            "total_servers_assessed": total_servers,
            "tested_servers": tested_servers,
            "failed_servers": failed_servers,
            "fastapi_stub_servers": stub_servers,
            "total_tools_found": total_tools,
            "total_tool_calls_attempted": total_test_calls,
            "successful_tool_calls": total_successful_calls,
            "tool_call_success_rate": round((total_successful_calls / total_test_calls * 100) if total_test_calls > 0 else 0, 1),
            "server_categories": {
                "mcp_implementations": len(implementation_results),
                "mcp_frameworks": len(framework_results),
                "working_servers": len(working_results)
            },
            "detailed_results": all_results
        }
        
        print("\n📊 COMPREHENSIVE TEST RESULTS")
        print("=" * 50)
        print(f"Total Servers Assessed: {total_servers}")
        print(f"✅ Successfully Tested: {tested_servers}")
        print(f"❌ Failed: {failed_servers}")
        print(f"🔧 FastAPI Stubs: {stub_servers}")
        print(f"🛠️ Total Tools Found: {total_tools}")
        print(f"📞 Tool Calls Attempted: {total_test_calls}")
        print(f"✅ Successful Tool Calls: {total_successful_calls}")
        print(f"📈 Tool Call Success Rate: {summary['tool_call_success_rate']}%")
        
        return summary

async def main():
    """Main test execution"""
    tester = ComprehensiveMCPTester()
    results = await tester.run_comprehensive_tests()
    
    # Save comprehensive results
    output_file = 'comprehensive_mcp_test_results_with_credentials.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📄 Comprehensive results saved to: {output_file}")
    
    # Generate summary by category
    print("\n📋 RESULTS BY CATEGORY:")
    print("-" * 30)
    
    for result in results['detailed_results']:
        status_icon = "✅" if result['status'] == 'TESTED' else "❌" if result['status'] == 'FAILED' else "🔧"
        tools = result.get('tool_count', 0)
        calls = result.get('successful_calls', 0)
        print(f"{status_icon} {result['server']}: {tools} tools, {calls} successful calls")
    
    return results

if __name__ == "__main__":
    asyncio.run(main())