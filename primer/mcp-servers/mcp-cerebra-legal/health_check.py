#!/usr/bin/env python3
"""
Quick health check for MCP Cerebra Legal server
"""

import asyncio
import sys
from pathlib import Path

# Add the src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from tools import handle_tool_call

async def main():
    """Run a quick health check"""
    print("🔍 Running MCP Cerebra Legal health check...")
    
    try:
        # Test health check
        result = await handle_tool_call("health_check", {})
        
        if result.get("status") == "healthy":
            print("✅ Health check passed!")
            print(f"📊 Server: {result.get('server')}")
            print(f"🔧 Version: {result.get('version')}")
            print(f"🛠️  Available tools: {len(result.get('available_tools', []))}")
            print(f"⚖️  Legal domains: {len(result.get('legal_domains', []))}")
            print(f"🖥️  Node.js server status: {result.get('node_server_status')}")
            
            if result.get('node_server_status') == 'available':
                print("✅ Node.js backend ready")
            else:
                print("⚠️  Node.js backend needs to be built")
                
            return True
        else:
            print(f"❌ Health check failed: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)