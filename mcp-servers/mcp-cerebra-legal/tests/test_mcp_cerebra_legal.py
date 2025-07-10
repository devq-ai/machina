"""
Comprehensive tests for MCP Cerebra Legal Server
Tests both Python wrapper and Node.js backend integration
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from pathlib import Path

# Import the modules to test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from tools import get_tools, handle_tool_call, call_cerebra_node_server
except ImportError as e:
    print(f"Import error: {e}")
    # Create mock implementations for testing
    def get_tools():
        return []
    def handle_tool_call(name, args):
        return {"error": "Module not available"}
    def call_cerebra_node_server(tool, args):
        return {"error": "Module not available"}

class TestCerebraLegalTools:
    """Test suite for Cerebra Legal MCP tools"""

    def test_get_tools_returns_correct_tools(self):
        """Test that get_tools returns the expected legal tools"""
        tools = get_tools()
        
        assert len(tools) == 4
        tool_names = [tool.name for tool in tools]
        
        expected_tools = [
            "legal_think",
            "legal_ask_followup_question", 
            "legal_attempt_completion",
            "health_check"
        ]
        
        for expected_tool in expected_tools:
            assert expected_tool in tool_names

    def test_legal_think_tool_schema(self):
        """Test that legal_think tool has correct schema"""
        tools = get_tools()
        legal_think_tool = next(tool for tool in tools if tool.name == "legal_think")
        
        schema = legal_think_tool.inputSchema
        assert schema["type"] == "object"
        
        required_fields = schema["required"]
        assert "thought" in required_fields
        assert "thoughtNumber" in required_fields
        assert "totalThoughts" in required_fields
        assert "nextThoughtNeeded" in required_fields
        
        properties = schema["properties"]
        assert "category" in properties
        assert "references" in properties
        assert "requestGuidance" in properties
        assert "requestTemplate" in properties

    def test_legal_ask_followup_question_tool_schema(self):
        """Test that legal_ask_followup_question tool has correct schema"""
        tools = get_tools()
        followup_tool = next(tool for tool in tools if tool.name == "legal_ask_followup_question")
        
        schema = followup_tool.inputSchema
        assert schema["type"] == "object"
        
        required_fields = schema["required"]
        assert "question" in required_fields
        
        properties = schema["properties"]
        assert "options" in properties
        assert "context" in properties

    def test_legal_attempt_completion_tool_schema(self):
        """Test that legal_attempt_completion tool has correct schema"""
        tools = get_tools()
        completion_tool = next(tool for tool in tools if tool.name == "legal_attempt_completion")
        
        schema = completion_tool.inputSchema
        assert schema["type"] == "object"
        
        required_fields = schema["required"]
        assert "result" in required_fields
        
        properties = schema["properties"]
        assert "command" in properties
        assert "context" in properties

    @pytest.mark.asyncio
    async def test_health_check_tool(self):
        """Test the health check functionality"""
        result = await handle_tool_call("health_check", {})
        
        assert result["status"] == "healthy"
        assert result["server"] == "mcp-cerebra-legal"
        assert result["version"] == "1.0.0"
        assert "available_tools" in result
        assert "legal_domains" in result
        
        expected_tools = ["legal_think", "legal_ask_followup_question", "legal_attempt_completion"]
        for tool in expected_tools:
            assert tool in result["available_tools"]
            
        expected_domains = ["ansc_contestation", "consumer_protection", "contract_analysis", "legal_reasoning"]
        for domain in expected_domains:
            assert domain in result["legal_domains"]

    @pytest.mark.asyncio
    async def test_unknown_tool_error(self):
        """Test handling of unknown tool calls"""
        result = await handle_tool_call("unknown_tool", {})
        
        assert result["status"] == "error"
        assert "Unknown tool" in result["error"]
        assert "available_tools" in result

    @pytest.mark.asyncio
    @patch('subprocess.run')
    async def test_call_cerebra_node_server_success(self, mock_subprocess):
        """Test successful call to Node.js server"""
        # Mock successful subprocess call
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "content": [{"type": "text", "text": "Legal analysis completed"}]
        })
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result
        
        # Mock the server path exists
        with patch('pathlib.Path.exists', return_value=True):
            result = await call_cerebra_node_server("legal_think", {
                "thought": "Test legal reasoning",
                "thoughtNumber": 1,
                "totalThoughts": 1,
                "nextThoughtNeeded": False
            })
        
        assert "content" in result
        mock_subprocess.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_cerebra_node_server_not_built(self):
        """Test behavior when Node.js server is not built"""
        # Mock that server doesn't exist
        with patch('pathlib.Path.exists', return_value=False):
            result = await call_cerebra_node_server("legal_think", {})
        
        assert result["status"] == "error"
        assert "not found" in result["error"]
        assert "npm run build" in result["suggestion"]

    @pytest.mark.asyncio
    @patch('subprocess.run')
    async def test_call_cerebra_node_server_error(self, mock_subprocess):
        """Test handling of Node.js server errors"""
        # Mock failed subprocess call
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Node.js error occurred"
        mock_subprocess.return_value = mock_result
        
        with patch('pathlib.Path.exists', return_value=True):
            result = await call_cerebra_node_server("legal_think", {})
        
        assert result["status"] == "error"
        assert "Node.js server error" in result["error"]
        assert result["returncode"] == 1

    @pytest.mark.asyncio
    @patch('subprocess.run')
    async def test_call_cerebra_node_server_timeout(self, mock_subprocess):
        """Test handling of Node.js server timeout"""
        # Mock timeout
        from subprocess import TimeoutExpired
        mock_subprocess.side_effect = TimeoutExpired("node", 30)
        
        with patch('pathlib.Path.exists', return_value=True):
            result = await call_cerebra_node_server("legal_think", {})
        
        assert result["status"] == "timeout"
        assert "timed out" in result["error"]

    @pytest.mark.asyncio
    async def test_legal_think_integration(self):
        """Test legal_think tool integration with Node.js backend"""
        # Mock successful Node.js call
        with patch('tools.call_cerebra_node_server') as mock_call:
            mock_call.return_value = {
                "content": [{
                    "type": "text",
                    "text": json.dumps({
                        "thoughtNumber": 1,
                        "totalThoughts": 1,
                        "nextThoughtNeeded": False,
                        "detectedDomain": "legal_reasoning",
                        "guidance": "Test guidance",
                        "template": "Test template"
                    })
                }]
            }
            
            result = await handle_tool_call("legal_think", {
                "thought": "Analyze contract terms",
                "thoughtNumber": 1,
                "totalThoughts": 1,
                "nextThoughtNeeded": False
            })
            
            assert "content" in result
            mock_call.assert_called_once_with("legal_think", {
                "thought": "Analyze contract terms",
                "thoughtNumber": 1,
                "totalThoughts": 1,
                "nextThoughtNeeded": False
            })

    @pytest.mark.asyncio
    async def test_legal_ask_followup_question_integration(self):
        """Test legal_ask_followup_question tool integration"""
        with patch('tools.call_cerebra_node_server') as mock_call:
            mock_call.return_value = {
                "content": [{
                    "type": "text",
                    "text": json.dumps({
                        "question": "What are the key contract terms?",
                        "options": ["Term 1", "Term 2", "Term 3"],
                        "detectedDomain": "contract_analysis"
                    })
                }]
            }
            
            result = await handle_tool_call("legal_ask_followup_question", {
                "question": "What contract terms need clarification?"
            })
            
            assert "content" in result
            mock_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_legal_attempt_completion_integration(self):
        """Test legal_attempt_completion tool integration"""
        with patch('tools.call_cerebra_node_server') as mock_call:
            mock_call.return_value = {
                "content": [{
                    "type": "text", 
                    "text": json.dumps({
                        "result": "Legal analysis complete",
                        "detectedDomain": "contract_analysis",
                        "formattedCitations": []
                    })
                }]
            }
            
            result = await handle_tool_call("legal_attempt_completion", {
                "result": "The contract is enforceable under applicable law"
            })
            
            assert "content" in result
            mock_call.assert_called_once()

class TestCerebraLegalDomains:
    """Test legal domain detection and handling"""

    def test_legal_domain_categories(self):
        """Test that all expected legal domains are supported"""
        tools = get_tools()
        legal_think_tool = next(tool for tool in tools if tool.name == "legal_think")
        
        category_enum = legal_think_tool.inputSchema["properties"]["category"]["enum"]
        
        expected_categories = [
            "analysis",
            "planning", 
            "verification",
            "legal_reasoning",
            "ansc_contestation",
            "consumer_protection",
            "contract_analysis"
        ]
        
        for category in expected_categories:
            assert category in category_enum

    @pytest.mark.asyncio
    async def test_health_check_includes_legal_domains(self):
        """Test that health check returns supported legal domains"""
        result = await handle_tool_call("health_check", {})
        
        legal_domains = result["legal_domains"]
        expected_domains = [
            "ansc_contestation",
            "consumer_protection",
            "contract_analysis", 
            "legal_reasoning"
        ]
        
        assert len(legal_domains) == len(expected_domains)
        for domain in expected_domains:
            assert domain in legal_domains

class TestCerebraLegalErrorHandling:
    """Test error handling and edge cases"""

    @pytest.mark.asyncio
    async def test_malformed_input_handling(self):
        """Test handling of malformed input data"""
        # Test with None arguments
        result = await handle_tool_call("legal_think", None)
        # Should be handled gracefully by the Node.js backend

        # Test with empty arguments for required tool
        result = await handle_tool_call("legal_think", {})
        # Should be handled by Node.js validation

    @pytest.mark.asyncio
    @patch('subprocess.run')
    async def test_json_parse_error_handling(self, mock_subprocess):
        """Test handling of malformed JSON from Node.js server"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Invalid JSON response"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result
        
        with patch('pathlib.Path.exists', return_value=True):
            result = await call_cerebra_node_server("legal_think", {})
        
        assert result["status"] == "success_raw"
        assert "raw_output" in result

if __name__ == "__main__":
    pytest.main([__file__, "-v"])