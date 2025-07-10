#!/usr/bin/env python3
"""
Basic test suite for Instagram MCP Server
Tests the server startup and basic health check functionality
"""

import subprocess
import json
import time
import sys
from pathlib import Path

class InstagramMCPTester:
    def __init__(self):
        self.server_path = Path(__file__).parent.parent / "dist" / "index.js"
        self.server_process = None
        
    def test_server_startup(self):
        """Test that the server starts without errors"""
        try:
            # Start the server
            cmd = ["node", str(self.server_path)]
            self.server_process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait a moment for startup
            time.sleep(2)
            
            # Check if process is still running
            if self.server_process.poll() is not None:
                stderr_output = self.server_process.stderr.read()
                raise Exception(f"Server failed to start: {stderr_output}")
                
            print("✅ Server startup test passed")
            return True
            
        except Exception as e:
            print(f"❌ Server startup test failed: {e}")
            return False
            
    def test_health_check_tool(self):
        """Test the health check tool"""
        try:
            if not self.server_process:
                raise Exception("Server not running")
                
            # Send health check request
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "instagram_health_check",
                    "arguments": {
                        "test_connection": False  # Don't test browser connection in tests
                    }
                }
            }
            
            # Send request to server
            request_json = json.dumps(request) + "\n"
            self.server_process.stdin.write(request_json)
            self.server_process.stdin.flush()
            
            # Read response (with timeout)
            response_line = self.server_process.stdout.readline()
            if not response_line:
                raise Exception("No response from server")
                
            response = json.loads(response_line.strip())
            
            # Check response structure
            if "result" not in response:
                raise Exception(f"Invalid response structure: {response}")
                
            result = response["result"]
            if "content" not in result:
                raise Exception(f"Missing content in response: {result}")
                
            # Parse the health check result
            content = json.loads(result["content"][0]["text"])
            
            if content["server_status"] != "healthy":
                raise Exception(f"Server not healthy: {content}")
                
            print("✅ Health check tool test passed")
            return True
            
        except Exception as e:
            print(f"❌ Health check tool test failed: {e}")
            return False
            
    def test_tool_listing(self):
        """Test that the server lists available tools"""
        try:
            if not self.server_process:
                raise Exception("Server not running")
                
            # Send tools list request
            request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list"
            }
            
            request_json = json.dumps(request) + "\n"
            self.server_process.stdin.write(request_json)
            self.server_process.stdin.flush()
            
            # Read response
            response_line = self.server_process.stdout.readline()
            if not response_line:
                raise Exception("No response from server")
                
            response = json.loads(response_line.strip())
            
            if "result" not in response:
                raise Exception(f"Invalid response structure: {response}")
                
            tools = response["result"]["tools"]
            tool_names = [tool["name"] for tool in tools]
            
            expected_tools = [
                "get_instagram_posts",
                "get_instagram_profile", 
                "get_instagram_media",
                "instagram_health_check"
            ]
            
            for expected_tool in expected_tools:
                if expected_tool not in tool_names:
                    raise Exception(f"Missing tool: {expected_tool}")
                    
            print(f"✅ Tool listing test passed - Found {len(tools)} tools")
            return True
            
        except Exception as e:
            print(f"❌ Tool listing test failed: {e}")
            return False
    
    def cleanup(self):
        """Clean up the server process"""
        if self.server_process:
            self.server_process.terminate()
            self.server_process.wait(timeout=5)
            
    def run_all_tests(self):
        """Run all tests"""
        print("🧪 Starting Instagram MCP Server Tests")
        print("=" * 50)
        
        # Check if server binary exists
        if not self.server_path.exists():
            print(f"❌ Server binary not found at {self.server_path}")
            print("Run 'npm run build' first")
            return False
            
        tests = [
            self.test_server_startup,
            self.test_tool_listing,
            self.test_health_check_tool
        ]
        
        passed = 0
        total = len(tests)
        
        try:
            for test in tests:
                if test():
                    passed += 1
                time.sleep(1)  # Brief pause between tests
                
        finally:
            self.cleanup()
            
        print("=" * 50)
        print(f"📊 Test Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed!")
            return True
        else:
            print("💥 Some tests failed")
            return False

if __name__ == "__main__":
    tester = InstagramMCPTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)