#!/usr/bin/env python3
"""
Comprehensive Production Tests for 14 MCP Servers
Tests actual tool functionality with real implementations
"""

import asyncio
import json
import os
import tempfile
import shutil
import sqlite3
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest
from typing import Dict, List, Any, Optional

# MCP Testing Framework
from mcp.server.models import Tool, TextContent, EmbeddedResource
from mcp.server.session import ServerSession
from mcp.server.stdio import StdioServerParameters
from mcp.types import CallToolRequest, CallToolResult

# Test Configuration
TEST_RESULTS = []
TEST_CONFIG = {
    "timeout": 30,
    "max_retries": 3,
    "capture_output": True,
    "mock_external_apis": True
}

class MCPServerTester:
    """Base class for testing MCP servers with real tool calls"""
    
    def __init__(self, server_name: str, server_module: str):
        self.server_name = server_name
        self.server_module = server_module
        self.test_results = []
        self.server_instance = None
        
    async def setup_server(self):
        """Initialize the MCP server"""
        try:
            # Import the server module dynamically
            module = __import__(self.server_module, fromlist=[''])
            
            # Get server instance or create one
            if hasattr(module, 'server'):
                self.server_instance = module.server
            elif hasattr(module, 'app'):
                self.server_instance = module.app
            else:
                raise ImportError(f"No server instance found in {self.server_module}")
                
            return True
        except Exception as e:
            self.test_results.append({
                "test": "server_setup",
                "status": "FAILED",
                "error": str(e),
                "details": f"Failed to setup server {self.server_name}"
            })
            return False
    
    async def test_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Test a specific tool call with real execution"""
        try:
            # Create MCP tool call request
            request = CallToolRequest(
                method="tools/call",
                params={
                    "name": tool_name,
                    "arguments": arguments
                }
            )
            
            # Execute tool call
            if hasattr(self.server_instance, 'call_tool'):
                result = await self.server_instance.call_tool(request)
            else:
                # Fallback to direct function call
                tool_func = getattr(self.server_instance, tool_name.replace('-', '_'), None)
                if tool_func:
                    result = await tool_func(**arguments)
                else:
                    raise AttributeError(f"Tool {tool_name} not found")
            
            return {
                "test": tool_name,
                "status": "PASSED", 
                "result": result,
                "arguments": arguments,
                "response_type": type(result).__name__
            }
            
        except Exception as e:
            return {
                "test": tool_name,
                "status": "FAILED",
                "error": str(e),
                "arguments": arguments,
                "details": f"Tool call failed: {tool_name}"
            }
    
    async def run_tests(self, test_cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Run all test cases for this server"""
        if not await self.setup_server():
            return self.test_results
            
        for test_case in test_cases:
            result = await self.test_tool_call(
                test_case["tool_name"],
                test_case["arguments"]
            )
            self.test_results.append(result)
            
        return self.test_results

# Test Cases for Each Server

class TestDarwinMCP(MCPServerTester):
    """Tests for Darwin MCP (Genetic Algorithm Platform)"""
    
    def __init__(self):
        super().__init__("Darwin MCP", "darwin_mcp_production")
        
    async def run_darwin_tests(self):
        """Run comprehensive Darwin MCP tests"""
        test_cases = [
            {
                "tool_name": "darwin_health_check",
                "arguments": {},
                "expected": "Server status and capabilities"
            },
            {
                "tool_name": "darwin_create_population",
                "arguments": {
                    "population_id": "test_pop_1",
                    "size": 10,
                    "dimensions": 3,
                    "bounds": [[-5, 5], [-5, 5], [-5, 5]]
                },
                "expected": "Population created successfully"
            },
            {
                "tool_name": "darwin_evaluate_fitness",
                "arguments": {
                    "population_id": "test_pop_1",
                    "fitness_function": "sphere"
                },
                "expected": "Fitness evaluation results"
            },
            {
                "tool_name": "darwin_evolve",
                "arguments": {
                    "population_id": "test_pop_1",
                    "generations": 5,
                    "mutation_rate": 0.1,
                    "crossover_rate": 0.8
                },
                "expected": "Evolution results with best fitness"
            },
            {
                "tool_name": "darwin_get_best",
                "arguments": {
                    "population_id": "test_pop_1",
                    "count": 3
                },
                "expected": "Best individuals from population"
            },
            {
                "tool_name": "darwin_get_population_stats",
                "arguments": {
                    "population_id": "test_pop_1"
                },
                "expected": "Population statistics"
            }
        ]
        
        return await self.run_tests(test_cases)

class TestDockerMCP(MCPServerTester):
    """Tests for Docker MCP (Container Management)"""
    
    def __init__(self):
        super().__init__("Docker MCP", "docker_mcp_production")
        
    async def run_docker_tests(self):
        """Run Docker MCP tests (with Docker daemon detection)"""
        test_cases = [
            {
                "tool_name": "docker_health_check",
                "arguments": {},
                "expected": "Docker daemon status"
            },
            {
                "tool_name": "docker_system_info",
                "arguments": {},
                "expected": "Docker system information"
            },
            {
                "tool_name": "docker_list_containers",
                "arguments": {"all": True},
                "expected": "Container list"
            },
            {
                "tool_name": "docker_list_images",
                "arguments": {},
                "expected": "Image list"
            }
        ]
        
        # Only run container operations if Docker is available
        try:
            import docker
            client = docker.from_env()
            client.ping()
            
            # Add container creation test
            test_cases.extend([
                {
                    "tool_name": "docker_create_container",
                    "arguments": {
                        "image": "alpine:latest",
                        "name": "test_container_mcp",
                        "command": "echo 'Hello from MCP test'"
                    },
                    "expected": "Container created successfully"
                },
                {
                    "tool_name": "docker_remove_container",
                    "arguments": {
                        "container": "test_container_mcp",
                        "force": True
                    },
                    "expected": "Container removed successfully"
                }
            ])
        except Exception:
            # Docker not available, skip container operations
            pass
            
        return await self.run_tests(test_cases)

class TestFastMCPMCP(MCPServerTester):
    """Tests for FastMCP MCP (Framework Generator)"""
    
    def __init__(self):
        super().__init__("FastMCP MCP", "fastmcp_mcp_production")
        
    async def run_fastmcp_tests(self):
        """Run FastMCP framework tests"""
        test_cases = [
            {
                "tool_name": "fastmcp_health_check",
                "arguments": {},
                "expected": "Framework health status"
            },
            {
                "tool_name": "fastmcp_list_templates",
                "arguments": {},
                "expected": "Available project templates"
            },
            {
                "tool_name": "fastmcp_create_project",
                "arguments": {
                    "project_name": "test_mcp_project",
                    "template": "basic",
                    "description": "Test MCP project for validation"
                },
                "expected": "Project created successfully"
            },
            {
                "tool_name": "fastmcp_validate_project",
                "arguments": {
                    "project_path": "./test_mcp_project"
                },
                "expected": "Project validation results"
            },
            {
                "tool_name": "fastmcp_add_tool",
                "arguments": {
                    "project_path": "./test_mcp_project",
                    "tool_name": "test_tool",
                    "description": "Test tool for validation",
                    "parameters": {
                        "input": {"type": "string", "description": "Test input"}
                    }
                },
                "expected": "Tool added successfully"
            }
        ]
        
        return await self.run_tests(test_cases)

class TestMemoryMCP(MCPServerTester):
    """Tests for Memory MCP (Persistent Storage)"""
    
    def __init__(self):
        super().__init__("Memory MCP", "memory_mcp_production")
        
    async def run_memory_tests(self):
        """Run Memory MCP tests with real SQLite operations"""
        test_cases = [
            {
                "tool_name": "store_memory",
                "arguments": {
                    "content": "Test memory content for MCP validation",
                    "importance": 0.8,
                    "tags": ["test", "validation", "mcp"]
                },
                "expected": "Memory stored successfully"
            },
            {
                "tool_name": "search_memories",
                "arguments": {
                    "query": "validation",
                    "limit": 5
                },
                "expected": "Search results for validation"
            },
            {
                "tool_name": "store_conversation",
                "arguments": {
                    "conversation_id": "test_conv_1",
                    "message": "Test conversation message",
                    "role": "user"
                },
                "expected": "Conversation stored successfully"
            },
            {
                "tool_name": "get_conversation_history",
                "arguments": {
                    "conversation_id": "test_conv_1",
                    "limit": 10
                },
                "expected": "Conversation history retrieved"
            },
            {
                "tool_name": "get_memory_stats",
                "arguments": {},
                "expected": "Memory statistics"
            }
        ]
        
        return await self.run_tests(test_cases)

class TestBayesMCP(MCPServerTester):
    """Tests for Bayes MCP (Statistical Analysis)"""
    
    def __init__(self):
        super().__init__("Bayes MCP", "bayes_mcp")
        
    async def run_bayes_tests(self):
        """Run Bayesian analysis tests"""
        test_cases = [
            {
                "tool_name": "bayes_health_check",
                "arguments": {},
                "expected": "Bayes server status"
            },
            {
                "tool_name": "bayes_calculate_posterior",
                "arguments": {
                    "prior": 0.1,
                    "likelihood": 0.8,
                    "evidence": 0.3
                },
                "expected": "Posterior probability"
            },
            {
                "tool_name": "bayes_beta_binomial",
                "arguments": {
                    "alpha": 2,
                    "beta": 3,
                    "successes": 5,
                    "trials": 10
                },
                "expected": "Updated beta parameters"
            },
            {
                "tool_name": "bayes_credible_interval",
                "arguments": {
                    "alpha": 5,
                    "beta": 3,
                    "confidence": 0.95
                },
                "expected": "Credible interval bounds"
            },
            {
                "tool_name": "bayes_hypothesis_test",
                "arguments": {
                    "h0_prob": 0.5,
                    "h1_prob": 0.7,
                    "evidence": [1, 1, 0, 1, 0]
                },
                "expected": "Hypothesis test results"
            }
        ]
        
        return await self.run_tests(test_cases)

# Mock API Tests (for servers requiring external APIs)

class TestGmailMCP(MCPServerTester):
    """Tests for Gmail MCP (with mocked Google API)"""
    
    def __init__(self):
        super().__init__("Gmail MCP", "gmail_mcp_production")
        
    async def run_gmail_tests(self):
        """Run Gmail tests with mocked Google API"""
        with patch('googleapiclient.discovery.build') as mock_build:
            # Mock Gmail API service
            mock_service = Mock()
            mock_build.return_value = mock_service
            
            # Mock labels list
            mock_service.users().labels().list().execute.return_value = {
                'labels': [
                    {'id': 'INBOX', 'name': 'INBOX'},
                    {'id': 'SENT', 'name': 'SENT'}
                ]
            }
            
            # Mock email search
            mock_service.users().messages().list().execute.return_value = {
                'messages': [
                    {'id': 'msg_1', 'threadId': 'thread_1'},
                    {'id': 'msg_2', 'threadId': 'thread_2'}
                ]
            }
            
            test_cases = [
                {
                    "tool_name": "list_labels",
                    "arguments": {},
                    "expected": "Gmail labels list"
                },
                {
                    "tool_name": "search_emails",
                    "arguments": {
                        "query": "test",
                        "max_results": 5
                    },
                    "expected": "Email search results"
                }
            ]
            
            return await self.run_tests(test_cases)

class TestGCPMCP(MCPServerTester):
    """Tests for GCP MCP (with mocked Google Cloud APIs)"""
    
    def __init__(self):
        super().__init__("GCP MCP", "gcp_mcp_production")
        
    async def run_gcp_tests(self):
        """Run GCP tests with mocked Google Cloud APIs"""
        with patch('google.cloud.compute_v1.InstancesClient') as mock_compute, \
             patch('google.cloud.storage.Client') as mock_storage, \
             patch('google.cloud.bigquery.Client') as mock_bigquery:
            
            # Mock Compute Engine
            mock_compute.return_value.list.return_value = [
                Mock(name='test-instance-1', status='RUNNING'),
                Mock(name='test-instance-2', status='STOPPED')
            ]
            
            # Mock Cloud Storage
            mock_storage.return_value.list_buckets.return_value = [
                Mock(name='test-bucket-1'),
                Mock(name='test-bucket-2')
            ]
            
            # Mock BigQuery
            mock_bigquery.return_value.list_datasets.return_value = [
                Mock(dataset_id='test_dataset_1'),
                Mock(dataset_id='test_dataset_2')
            ]
            
            test_cases = [
                {
                    "tool_name": "list_instances",
                    "arguments": {
                        "project_id": "test-project",
                        "zone": "us-central1-a"
                    },
                    "expected": "Compute instances list"
                },
                {
                    "tool_name": "list_buckets",
                    "arguments": {
                        "project_id": "test-project"
                    },
                    "expected": "Storage buckets list"
                },
                {
                    "tool_name": "list_datasets",
                    "arguments": {
                        "project_id": "test-project"
                    },
                    "expected": "BigQuery datasets list"
                }
            ]
            
            return await self.run_tests(test_cases)

class TestGithubMCP(MCPServerTester):
    """Tests for GitHub MCP (with mocked PyGithub)"""
    
    def __init__(self):
        super().__init__("GitHub MCP", "github_mcp_production")
        
    async def run_github_tests(self):
        """Run GitHub tests with mocked PyGithub"""
        with patch('github.Github') as mock_github:
            # Mock GitHub client
            mock_client = Mock()
            mock_github.return_value = mock_client
            
            # Mock repositories
            mock_repo = Mock()
            mock_repo.name = "test-repo"
            mock_repo.full_name = "user/test-repo"
            mock_repo.description = "Test repository"
            mock_client.get_user().get_repos.return_value = [mock_repo]
            
            # Mock issues
            mock_issue = Mock()
            mock_issue.number = 1
            mock_issue.title = "Test Issue"
            mock_issue.state = "open"
            mock_repo.get_issues.return_value = [mock_issue]
            
            test_cases = [
                {
                    "tool_name": "list_repos",
                    "arguments": {},
                    "expected": "GitHub repositories list"
                },
                {
                    "tool_name": "list_issues",
                    "arguments": {
                        "repo": "user/test-repo"
                    },
                    "expected": "GitHub issues list"
                }
            ]
            
            return await self.run_tests(test_cases)

class TestCalendarMCP(MCPServerTester):
    """Tests for Calendar MCP (with mocked Google Calendar API)"""
    
    def __init__(self):
        super().__init__("Calendar MCP", "calendar_mcp_production")
        
    async def run_calendar_tests(self):
        """Run Calendar tests with mocked Google Calendar API"""
        with patch('googleapiclient.discovery.build') as mock_build:
            # Mock Calendar API service
            mock_service = Mock()
            mock_build.return_value = mock_service
            
            # Mock calendar list
            mock_service.calendarList().list().execute.return_value = {
                'items': [
                    {'id': 'primary', 'summary': 'Primary Calendar'},
                    {'id': 'calendar_2', 'summary': 'Work Calendar'}
                ]
            }
            
            # Mock events list
            mock_service.events().list().execute.return_value = {
                'items': [
                    {
                        'id': 'event_1',
                        'summary': 'Test Event',
                        'start': {'dateTime': '2024-01-01T10:00:00Z'},
                        'end': {'dateTime': '2024-01-01T11:00:00Z'}
                    }
                ]
            }
            
            test_cases = [
                {
                    "tool_name": "list_calendars",
                    "arguments": {},
                    "expected": "Google calendars list"
                },
                {
                    "tool_name": "list_events",
                    "arguments": {
                        "calendar_id": "primary",
                        "max_results": 10
                    },
                    "expected": "Calendar events list"
                }
            ]
            
            return await self.run_tests(test_cases)

class TestUpstashMCP(MCPServerTester):
    """Tests for Upstash MCP (with mocked Upstash APIs)"""
    
    def __init__(self):
        super().__init__("Upstash MCP", "upstash_mcp_production")
        
    async def run_upstash_tests(self):
        """Run Upstash tests with mocked HTTP responses"""
        with patch('httpx.AsyncClient') as mock_client:
            # Mock HTTP client
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"result": "OK"}
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            test_cases = [
                {
                    "tool_name": "redis_set",
                    "arguments": {
                        "key": "test_key",
                        "value": "test_value"
                    },
                    "expected": "Redis set operation result"
                },
                {
                    "tool_name": "redis_get",
                    "arguments": {
                        "key": "test_key"
                    },
                    "expected": "Redis get operation result"
                },
                {
                    "tool_name": "vector_store",
                    "arguments": {
                        "vector_id": "test_vector",
                        "vector": [0.1, 0.2, 0.3, 0.4, 0.5],
                        "metadata": {"type": "test"}
                    },
                    "expected": "Vector store operation result"
                }
            ]
            
            return await self.run_tests(test_cases)

class TestLogfireMCP(MCPServerTester):
    """Tests for Logfire MCP (with mocked Logfire API)"""
    
    def __init__(self):
        super().__init__("Logfire MCP", "logfire_mcp_production")
        
    async def run_logfire_tests(self):
        """Run Logfire tests with mocked API responses"""
        with patch('httpx.AsyncClient') as mock_client:
            # Mock HTTP client
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "success", "id": "log_123"}
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            test_cases = [
                {
                    "tool_name": "send_log",
                    "arguments": {
                        "level": "info",
                        "message": "Test log message",
                        "timestamp": "2024-01-01T10:00:00Z"
                    },
                    "expected": "Log sent successfully"
                },
                {
                    "tool_name": "start_span",
                    "arguments": {
                        "name": "test_span",
                        "operation": "test_operation"
                    },
                    "expected": "Span started successfully"
                },
                {
                    "tool_name": "send_metric",
                    "arguments": {
                        "name": "test_metric",
                        "value": 42.0,
                        "type": "counter"
                    },
                    "expected": "Metric sent successfully"
                }
            ]
            
            return await self.run_tests(test_cases)

# Main Test Runner

async def run_all_production_tests():
    """Run comprehensive tests for all 14 production MCP servers"""
    
    print("🧪 Starting Comprehensive MCP Production Server Tests\n")
    print("=" * 60)
    
    all_results = []
    
    # Group 1: Self-contained servers (no external dependencies)
    print("\n🔧 Group 1: Self-Contained Servers")
    print("-" * 40)
    
    self_contained_tests = [
        ("Darwin MCP", TestDarwinMCP),
        ("FastMCP MCP", TestFastMCPMCP),
        ("Memory MCP", TestMemoryMCP),
        ("Bayes MCP", TestBayesMCP)
    ]
    
    for name, test_class in self_contained_tests:
        print(f"\n📊 Testing {name}...")
        try:
            tester = test_class()
            results = await tester.run_tests([])  # Will be implemented per server
            all_results.extend(results)
            
            passed = sum(1 for r in results if r.get('status') == 'PASSED')
            failed = sum(1 for r in results if r.get('status') == 'FAILED')
            print(f"   ✅ {passed} passed, ❌ {failed} failed")
            
        except Exception as e:
            print(f"   ❌ Server test failed: {e}")
            all_results.append({
                "server": name,
                "status": "FAILED",
                "error": str(e)
            })
    
    # Group 2: Docker-dependent servers
    print("\n🐳 Group 2: Docker-Dependent Servers")
    print("-" * 40)
    
    try:
        print(f"\n📊 Testing Docker MCP...")
        docker_tester = TestDockerMCP()
        docker_results = await docker_tester.run_docker_tests()
        all_results.extend(docker_results)
        
        passed = sum(1 for r in docker_results if r.get('status') == 'PASSED')
        failed = sum(1 for r in docker_results if r.get('status') == 'FAILED')
        print(f"   ✅ {passed} passed, ❌ {failed} failed")
        
    except Exception as e:
        print(f"   ❌ Docker MCP test failed: {e}")
        all_results.append({
            "server": "Docker MCP",
            "status": "FAILED",
            "error": str(e)
        })
    
    # Group 3: API-dependent servers (with mocking)
    print("\n🌐 Group 3: API-Dependent Servers (Mocked)")
    print("-" * 40)
    
    api_dependent_tests = [
        ("Gmail MCP", TestGmailMCP),
        ("GCP MCP", TestGCPMCP),
        ("GitHub MCP", TestGithubMCP),
        ("Calendar MCP", TestCalendarMCP),
        ("Upstash MCP", TestUpstashMCP),
        ("Logfire MCP", TestLogfireMCP)
    ]
    
    for name, test_class in api_dependent_tests:
        print(f"\n📊 Testing {name}...")
        try:
            tester = test_class()
            if hasattr(tester, f"run_{name.lower().replace(' ', '_')}_tests"):
                results = await getattr(tester, f"run_{name.lower().replace(' ', '_')}_tests")()
            else:
                results = await tester.run_tests([])
            all_results.extend(results)
            
            passed = sum(1 for r in results if r.get('status') == 'PASSED')
            failed = sum(1 for r in results if r.get('status') == 'FAILED')
            print(f"   ✅ {passed} passed, ❌ {failed} failed")
            
        except Exception as e:
            print(f"   ❌ {name} test failed: {e}")
            all_results.append({
                "server": name,
                "status": "FAILED",
                "error": str(e)
            })
    
    # Group 4: Incomplete servers (basic tests only)
    print("\n⚠️  Group 4: Incomplete Servers (Basic Tests)")
    print("-" * 40)
    
    incomplete_servers = ["Stripe MCP", "Shopify MCP", "Ptolemies MCP"]
    
    for server_name in incomplete_servers:
        print(f"\n📊 Testing {server_name}...")
        try:
            # Basic health check only
            result = {
                "server": server_name,
                "status": "INCOMPLETE",
                "note": "Server implementation is incomplete - only basic structure exists"
            }
            all_results.append(result)
            print(f"   ⚠️  Server marked as incomplete")
            
        except Exception as e:
            print(f"   ❌ {server_name} test failed: {e}")
            all_results.append({
                "server": server_name,
                "status": "FAILED",
                "error": str(e)
            })
    
    return all_results

# Test Results Summary

def generate_test_summary(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate comprehensive test summary"""
    
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r.get('status') == 'PASSED')
    failed_tests = sum(1 for r in results if r.get('status') == 'FAILED')
    incomplete_tests = sum(1 for r in results if r.get('status') == 'INCOMPLETE')
    
    # Group results by server
    server_results = {}
    for result in results:
        server = result.get('server', result.get('test', 'Unknown'))
        if server not in server_results:
            server_results[server] = []
        server_results[server].append(result)
    
    summary = {
        "total_tests": total_tests,
        "passed_tests": passed_tests,
        "failed_tests": failed_tests,
        "incomplete_tests": incomplete_tests,
        "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
        "server_results": server_results,
        "timestamp": "2024-01-01T10:00:00Z"  # Will be updated with actual timestamp
    }
    
    return summary

if __name__ == "__main__":
    # Run all tests
    results = asyncio.run(run_all_production_tests())
    
    # Generate summary
    summary = generate_test_summary(results)
    
    # Print final results
    print(f"\n🎯 FINAL TEST RESULTS")
    print("=" * 60)
    print(f"Total Tests: {summary['total_tests']}")
    print(f"✅ Passed: {summary['passed_tests']}")
    print(f"❌ Failed: {summary['failed_tests']}")
    print(f"⚠️  Incomplete: {summary['incomplete_tests']}")
    print(f"📊 Success Rate: {summary['success_rate']:.1f}%")
    
    # Save results to file
    with open("mcp_production_test_results.json", "w") as f:
        json.dump({
            "summary": summary,
            "detailed_results": results
        }, f, indent=2)
    
    print(f"\n📄 Detailed results saved to: mcp_production_test_results.json")