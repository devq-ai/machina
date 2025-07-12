#!/usr/bin/env python3
"""
Test the MCP Registry with our Machina servers using the proper client.
"""

from fastmcp_http.client import FastMCPHttpClient
import json

def main():
    print("🔌 Connecting to MCP Registry at http://127.0.0.1:31337")
    client = FastMCPHttpClient("http://127.0.0.1:31337")

    print("\n📋 Listing all registered servers:")
    servers = client.list_servers()
    for server in servers:
        print(f"  • {server.name}: {server.description}")
    
    print(f"\n🛠️  Listing all available tools:")
    tools = client.list_tools()
    print(f"Total tools available: {len(tools)}")
    
    for tool in tools:
        if tool.name.startswith('MachinaTestServer'):
            print(f"  • {tool.name}: {tool.description}")
    
    print(f"\n🔧 Testing MachinaTestServer.list_machina_servers tool:")
    try:
        result = client.call_tool("MachinaTestServer.list_machina_servers", {})
        print("✅ Tool call successful!")
        print(f"📊 Result: {result}")
    except Exception as e:
        print(f"❌ Tool call failed: {e}")
    
    print(f"\n🔧 Testing MachinaTestServer.health_check tool:")
    try:
        result = client.call_tool("MachinaTestServer.health_check", {})
        print("✅ Health check successful!")
        print(f"📊 Result: {result}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")

    print(f"\n🔧 Testing MachinaTestServer.echo_message tool:")
    try:
        result = client.call_tool("MachinaTestServer.echo_message", {
            "message": "All 13 Machina MCP servers are working!",
            "repeat_count": 2
        })
        print("✅ Echo test successful!")
        print(f"📊 Result: {result}")
    except Exception as e:
        print(f"❌ Echo test failed: {e}")

if __name__ == "__main__":
    main()