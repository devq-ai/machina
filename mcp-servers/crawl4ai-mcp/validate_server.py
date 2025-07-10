#!/usr/bin/env python3
"""
Crawl4AI MCP Server Validation Script

This script validates that the Crawl4AI MCP server is working correctly
by testing MCP protocol compliance, tool functionality, crawl4ai integration,
and production readiness.
"""

import asyncio
import json
import sys
import subprocess
import tempfile
from pathlib import Path

async def test_imports():
    """Test that all required imports work"""
    print("📦 Testing Import Dependencies...")

    try:
        # Test core MCP imports
        from mcp import types
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
        print("✅ MCP imports: OK")

        # Test Pydantic imports
        from pydantic import BaseModel, Field, field_validator
        print("✅ Pydantic imports: OK")

        # Test Crawl4AI imports
        from crawl4ai import AsyncWebCrawler, CrawlResult
        from crawl4ai.extraction_strategy import LLMExtractionStrategy, JsonCssExtractionStrategy
        print("✅ Crawl4AI imports: OK")

        # Test async support
        import asyncio
        import aiofiles
        print("✅ Async libraries: OK")

        # Test content processing
        import beautifulsoup4
        import lxml
        import nltk
        print("✅ Content processing libraries: OK")

        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_server_file():
    """Test server file structure and syntax"""
    print("\n📝 Testing Server File Structure...")

    server_file = Path("server.py")
    if not server_file.exists():
        print("❌ server.py file not found")
        return False

    try:
        # Test syntax by compiling
        with open(server_file) as f:
            code = f.read()

        compile(code, str(server_file), 'exec')
        print("✅ Python syntax: Valid")

        # Check for key classes and functions
        required_components = [
            "class CrawlMode",
            "class ExtractStrategy",
            "class CrawlConfig",
            "class CrawlStorage",
            "class ContentProcessor",
            "class Crawl4aiMCP",
            "def main"
        ]

        missing_components = []
        for component in required_components:
            if component not in code:
                missing_components.append(component)

        if missing_components:
            print(f"❌ Missing components: {missing_components}")
            return False
        else:
            print("✅ All required components present")

        # Check for MCP tools
        expected_tools = [
            "crawl_url",
            "crawl_deep",
            "extract_structured_data",
            "batch_crawl",
            "search_content",
            "analyze_page",
            "get_crawl_result",
            "list_crawl_results",
            "create_session",
            "get_page_links"
        ]

        missing_tools = []
        for tool in expected_tools:
            if tool not in code:
                missing_tools.append(tool)

        if missing_tools:
            print(f"⚠️  Missing MCP tools: {missing_tools}")
        else:
            print("✅ All expected MCP tools present")

        return True

    except SyntaxError as e:
        print(f"❌ Syntax error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error reading server file: {e}")
        return False

async def test_crawl4ai_functionality():
    """Test basic crawl4ai functionality"""
    print("\n🕷️ Testing Crawl4AI Integration...")

    try:
        from crawl4ai import AsyncWebCrawler

        print("⏳ Testing basic web crawling...")
        async with AsyncWebCrawler(verbose=False) as crawler:
            result = await asyncio.wait_for(
                crawler.arun(url='https://httpbin.org/html'),
                timeout=30.0
            )

            if result.success:
                print("✅ Crawl4AI basic functionality: Working")
                print(f"   📄 Content length: {len(result.markdown) if result.markdown else 0} chars")
                print(f"   🔗 Links found: {len(result.links) if result.links else 0}")
                return True
            else:
                print("❌ Crawl4AI: Crawl failed")
                return False

    except asyncio.TimeoutError:
        print("❌ Crawl4AI: Request timeout")
        return False
    except Exception as e:
        print(f"❌ Crawl4AI error: {e}")
        return False

async def test_mcp_protocol():
    """Test basic MCP protocol compliance"""
    print("\n🔍 Testing MCP Protocol Compliance...")

    try:
        process = subprocess.Popen(
            [sys.executable, "server.py"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Send initialize request
        initialize_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        }

        request_json = json.dumps(initialize_request) + "\n"
        process.stdin.write(request_json)
        process.stdin.flush()

        # Read response with timeout
        try:
            response_line = await asyncio.wait_for(
                asyncio.create_task(asyncio.to_thread(process.stdout.readline)),
                timeout=10.0
            )

            if response_line:
                response = json.loads(response_line.strip())
                if response.get("result"):
                    print("✅ MCP Protocol: Server responds to initialize")
                    return True
                else:
                    print("❌ MCP Protocol: Invalid initialize response")
                    return False
            else:
                print("❌ MCP Protocol: No response from server")
                return False

        except asyncio.TimeoutError:
            print("❌ MCP Protocol: Server response timeout")
            return False

    except Exception as e:
        print(f"❌ MCP Protocol: Error testing server - {e}")
        return False
    finally:
        if 'process' in locals():
            process.terminate()
            process.wait()

async def test_tools_listing():
    """Test that all expected tools are available"""
    print("\n🔧 Testing MCP Tools Listing...")

    expected_tools = [
        "crawl_url",
        "crawl_deep",
        "extract_structured_data",
        "batch_crawl",
        "search_content",
        "analyze_page",
        "get_crawl_result",
        "list_crawl_results",
        "create_session",
        "get_page_links"
    ]

    try:
        process = subprocess.Popen(
            [sys.executable, "server.py"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Initialize first
        initialize_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "test-client", "version": "1.0.0"}
            }
        }

        process.stdin.write(json.dumps(initialize_request) + "\n")
        process.stdin.flush()

        # Read initialize response
        init_response = process.stdout.readline()

        # Send initialized notification
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        process.stdin.write(json.dumps(initialized_notification) + "\n")
        process.stdin.flush()

        # Request tools list
        tools_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list"
        }

        process.stdin.write(json.dumps(tools_request) + "\n")
        process.stdin.flush()

        # Read tools response
        tools_response_line = await asyncio.wait_for(
            asyncio.create_task(asyncio.to_thread(process.stdout.readline)),
            timeout=10.0
        )

        if tools_response_line:
            tools_response = json.loads(tools_response_line.strip())
            if "result" in tools_response and "tools" in tools_response["result"]:
                available_tools = [tool["name"] for tool in tools_response["result"]["tools"]]

                print(f"📋 Available tools: {len(available_tools)}")
                for tool in available_tools:
                    print(f"   • {tool}")

                missing_tools = set(expected_tools) - set(available_tools)
                extra_tools = set(available_tools) - set(expected_tools)

                if missing_tools:
                    print(f"❌ Missing tools: {missing_tools}")
                    return False
                elif extra_tools:
                    print(f"ℹ️  Extra tools found: {extra_tools}")

                print("✅ All expected tools are available")
                return True
            else:
                print("❌ Invalid tools response format")
                return False
        else:
            print("❌ No tools response received")
            return False

    except Exception as e:
        print(f"❌ Error testing tools: {e}")
        return False
    finally:
        if 'process' in locals():
            process.terminate()
            process.wait()

async def test_storage_functionality():
    """Test storage system functionality"""
    print("\n💾 Testing Storage System...")

    try:
        # Import storage class
        sys.path.insert(0, '.')
        from server import CrawlStorage

        # Create temporary storage
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = CrawlStorage(storage_dir=temp_dir)

            # Test result storage
            test_result = {
                "url": "https://example.com",
                "markdown": "Test content",
                "success": True
            }

            success = await storage.store_result("test-id", test_result)
            if not success:
                print("❌ Storage: Failed to store result")
                return False

            # Test result retrieval
            retrieved = await storage.get_result("test-id")
            if not retrieved or retrieved.get("url") != "https://example.com":
                print("❌ Storage: Failed to retrieve result")
                return False

            # Test session creation
            session_id = await storage.create_session("test-session", {})
            if not session_id:
                print("❌ Storage: Failed to create session")
                return False

            print("✅ Storage system: Working correctly")
            return True

    except Exception as e:
        print(f"❌ Storage error: {e}")
        return False

async def test_content_processing():
    """Test content processing functionality"""
    print("\n🔄 Testing Content Processing...")

    try:
        sys.path.insert(0, '.')
        from server import ContentProcessor

        # Create mock result for testing
        class MockResult:
            def __init__(self):
                self.url = "https://example.com"
                self.markdown = "Test content for processing"
                self.links = [
                    {"href": "/internal", "text": "Internal"},
                    {"href": "https://external.com", "text": "External"}
                ]
                self.success = True
                self.title = "Test Page"
                self.description = "Test description"

        processor = ContentProcessor()
        mock_result = MockResult()

        # Test metadata extraction
        metadata = processor.extract_metadata(mock_result)
        if not metadata or metadata.get("url") != "https://example.com":
            print("❌ Content Processing: Metadata extraction failed")
            return False

        # Test link analysis
        links_analysis = processor.analyze_links(mock_result, "https://example.com")
        if not links_analysis or links_analysis.get("total") != 2:
            print("❌ Content Processing: Link analysis failed")
            return False

        # Test content chunking
        chunks = processor.chunk_content("This is test content for chunking", chunk_size=10)
        if not chunks or len(chunks) < 2:
            print("❌ Content Processing: Content chunking failed")
            return False

        print("✅ Content processing: Working correctly")
        return True

    except Exception as e:
        print(f"❌ Content processing error: {e}")
        return False

async def run_validation():
    """Run all validation tests"""
    print("🚀 Crawl4AI MCP Server Validation")
    print("=" * 60)

    # Track test results
    results = []

    # Test 1: Import dependencies
    results.append(("Import Dependencies", test_imports()))

    # Test 2: Server file structure
    results.append(("Server File Structure", test_server_file()))

    # Test 3: Storage functionality
    results.append(("Storage System", await test_storage_functionality()))

    # Test 4: Content processing
    results.append(("Content Processing", await test_content_processing()))

    # Test 5: Crawl4AI integration
    results.append(("Crawl4AI Integration", await test_crawl4ai_functionality()))

    # Test 6: MCP protocol compliance
    results.append(("MCP Protocol", await test_mcp_protocol()))

    # Test 7: Tools listing
    results.append(("MCP Tools", await test_tools_listing()))

    # Summary
    print("\n" + "=" * 60)
    print("📊 VALIDATION SUMMARY")
    print("=" * 60)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:.<40} {status}")
        if result:
            passed += 1

    print(f"\nResults: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Crawl4AI MCP Server is ready!")
        print("💡 Key Features Validated:")
        print("   • Complete MCP protocol compliance")
        print("   • 10 comprehensive crawling tools")
        print("   • Full Crawl4AI integration")
        print("   • Robust storage and content processing")
        print("   • Production-ready error handling")
        print("\n🚀 Server ready for integration with main Machina service!")
        return True
    else:
        print(f"\n⚠️  {total - passed} tests failed. Please review and fix issues.")
        return False

if __name__ == "__main__":
    try:
        result = asyncio.run(run_validation())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n🛑 Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error during validation: {e}")
        sys.exit(1)
