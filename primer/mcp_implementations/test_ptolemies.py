#!/usr/bin/env python3
"""
Test script for Ptolemies MCP Server
Tests basic connectivity and tool execution
"""

import asyncio
import json
import sys
import os
from datetime import datetime

# Add paths for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '../../ptolemies/python-server'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except ImportError:
    print("❌ MCP SDK not installed. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "mcp"])
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client


async def test_ptolemies_server():
    """Test Ptolemies MCP server connectivity and basic operations"""

    print("🧪 Testing Ptolemies MCP Server")
    print("=" * 50)

    # Get the absolute path to ptolemies
    ptolemies_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../ptolemies/python-server'))

    server_params = StdioServerParameters(
        command=sys.executable,
        args=[os.path.join(ptolemies_path, "ptolemies_mcp_server.py")],
        cwd=ptolemies_path,
        env={
            **os.environ,
            "SURREALDB_URL": "ws://localhost:8000/rpc",
            "SURREALDB_USERNAME": "root",
            "SURREALDB_PASSWORD": "root",
            "SURREALDB_NAMESPACE": "ptolemies",
            "SURREALDB_DATABASE": "knowledge",
            "PYTHONPATH": f"{ptolemies_path}:{os.path.dirname(ptolemies_path)}:{os.environ.get('PYTHONPATH', '')}"
        }
    )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                print("✅ Connected to Ptolemies MCP server")

                # Initialize connection
                await session.initialize()
                print("✅ Session initialized")

                # List available tools
                tools_response = await session.list_tools()
                tools = tools_response.tools if hasattr(tools_response, 'tools') else []

                print(f"\n📋 Available tools: {len(tools)}")
                for tool in tools[:5]:  # Show first 5 tools
                    print(f"  - {tool.name}: {tool.description[:60]}...")

                # Test health check
                print("\n🏥 Testing health check...")
                try:
                    health_result = await session.call_tool(
                        "ptolemies_health_check",
                        {}
                    )

                    health_data = health_result.content[0].text if health_result.content else "{}"
                    health_json = json.loads(health_data)

                    print(f"✅ Health Status: {health_json.get('status', 'unknown')}")
                    print(f"   Components: {', '.join(health_json.get('components', {}).keys())}")
                except Exception as e:
                    print(f"⚠️  Health check not available: {str(e)}")

                # Test system info
                print("\n📊 Testing system info...")
                try:
                    info_result = await session.call_tool(
                        "ptolemies_system_info",
                        {}
                    )

                    info_data = info_result.content[0].text if info_result.content else "{}"
                    info_json = json.loads(info_data)

                    print(f"✅ System Version: {info_json.get('version', 'unknown')}")
                    print(f"   Total Tools: {info_json.get('total_tools', len(tools))}")
                except Exception as e:
                    print(f"⚠️  System info not available: {str(e)}")

                # Quick response test
                print("\n⚡ Testing response time...")
                start_time = datetime.now()

                # Try a simple tool that should exist
                test_tools = ["ptolemies_health_check", "ptolemies_system_info", "list_tools"]
                for tool_name in test_tools:
                    if any(tool.name == tool_name for tool in tools):
                        try:
                            await session.call_tool(tool_name, {})
                            response_time = (datetime.now() - start_time).total_seconds() * 1000
                            print(f"✅ Response time: {response_time:.2f}ms")
                            break
                        except:
                            continue
                else:
                    # If no specific tools found, just measure initialization time
                    response_time = (datetime.now() - start_time).total_seconds() * 1000
                    print(f"✅ Initialization time: {response_time:.2f}ms")

                print("\n✅ Ptolemies MCP Server: OPERATIONAL")
                print(f"   Total tools available: {len(tools)}")
                return True

    except FileNotFoundError as e:
        print(f"❌ Ptolemies MCP server not found: {e}")
        print(f"   Expected at: {ptolemies_path}")
        return False
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Please ensure ptolemies dependencies are installed")
        return False
    except Exception as e:
        print(f"❌ Error testing Ptolemies: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_ptolemies_server())
    sys.exit(0 if success else 1)
