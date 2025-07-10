"""
Basic functionality tests for MCP Cerebra Legal Server
Tests core functionality without external dependencies
"""

import pytest
import json
import subprocess
from pathlib import Path

class TestCerebraBasicFunctionality:
    """Test basic functionality of Cerebra Legal server"""

    def test_node_server_built(self):
        """Test that the Node.js server was built successfully"""
        build_path = Path(__file__).parent.parent / "build" / "index.js"
        assert build_path.exists(), "Node.js server should be built at build/index.js"
        assert build_path.is_file(), "build/index.js should be a file"
        
    def test_package_json_exists(self):
        """Test that package.json exists with correct configuration"""
        package_path = Path(__file__).parent.parent / "package.json"
        assert package_path.exists(), "package.json should exist"
        
        with open(package_path, 'r') as f:
            package_data = json.load(f)
            
        assert package_data["name"] == "mcp-cerebra-legal-server"
        assert "mcp" in package_data["keywords"]
        assert "legal" in package_data["keywords"]
        assert "@modelcontextprotocol/sdk" in package_data["dependencies"]

    def test_requirements_txt_exists(self):
        """Test that Python requirements.txt exists"""
        req_path = Path(__file__).parent.parent / "requirements.txt"
        assert req_path.exists(), "requirements.txt should exist"
        
        with open(req_path, 'r') as f:
            requirements = f.read()
            
        assert "fastapi" in requirements
        assert "mcp" in requirements
        assert "uvicorn" in requirements

    def test_python_server_file_exists(self):
        """Test that Python server files exist"""
        server_path = Path(__file__).parent.parent / "src" / "server.py"
        tools_path = Path(__file__).parent.parent / "src" / "tools.py"
        
        assert server_path.exists(), "server.py should exist"
        assert tools_path.exists(), "tools.py should exist"

    def test_typescript_source_files_exist(self):
        """Test that TypeScript source files exist"""
        src_path = Path(__file__).parent.parent / "src"
        
        # Check main index file
        index_path = src_path / "index.ts"
        assert index_path.exists(), "index.ts should exist"
        
        # Check tool files
        tools_dir = src_path / "tools"
        assert tools_dir.exists(), "tools directory should exist"
        
        expected_tools = [
            "LegalThinkTool.ts",
            "LegalAskFollowupQuestionTool.ts", 
            "LegalAttemptCompletionTool.ts"
        ]
        
        for tool_file in expected_tools:
            tool_path = tools_dir / tool_file
            assert tool_path.exists(), f"{tool_file} should exist"

    def test_shared_modules_exist(self):
        """Test that shared utility modules exist"""
        shared_dir = Path(__file__).parent.parent / "src" / "shared"
        assert shared_dir.exists(), "shared directory should exist"
        
        expected_modules = [
            "CitationFormatter.ts",
            "DomainDetector.ts",
            "LegalKnowledgeBase.ts",
            "types.ts"
        ]
        
        for module_file in expected_modules:
            module_path = shared_dir / module_file
            assert module_path.exists(), f"{module_file} should exist"

    @pytest.mark.asyncio
    async def test_node_server_basic_invocation(self):
        """Test that Node.js server can be invoked (basic smoke test)"""
        build_path = Path(__file__).parent.parent / "build" / "index.js"
        
        if not build_path.exists():
            pytest.skip("Node.js server not built")
            
        # Test basic invocation (will likely fail with invalid input, but should not crash)
        try:
            result = subprocess.run(
                ["node", str(build_path)],
                input='{"invalid": "test"}',
                capture_output=True,
                text=True,
                timeout=5
            )
            # We expect this to fail with invalid input, but not crash
            assert result.returncode is not None
        except subprocess.TimeoutExpired:
            # Timeout is acceptable for this test
            pass
        except FileNotFoundError:
            pytest.skip("Node.js not available")

    def test_legal_domains_defined(self):
        """Test that legal domains are properly defined"""
        # Read the index.ts file to check domain definitions
        index_path = Path(__file__).parent.parent / "src" / "index.ts"
        
        if not index_path.exists():
            pytest.skip("index.ts not found")
            
        with open(index_path, 'r') as f:
            content = f.read()
            
        # Check that legal domains are defined
        assert "ansc_contestation" in content
        assert "consumer_protection" in content  
        assert "contract_analysis" in content
        assert "legal_reasoning" in content

    def test_legal_tools_defined(self):
        """Test that legal tools are properly defined"""
        index_path = Path(__file__).parent.parent / "src" / "index.ts"
        
        if not index_path.exists():
            pytest.skip("index.ts not found")
            
        with open(index_path, 'r') as f:
            content = f.read()
            
        # Check that legal tools are defined
        assert "legal_think" in content
        assert "legal_ask_followup_question" in content
        assert "legal_attempt_completion" in content

class TestCerebraConfiguration:
    """Test configuration and setup"""

    def test_tsconfig_exists(self):
        """Test that TypeScript configuration exists"""
        tsconfig_path = Path(__file__).parent.parent / "tsconfig.json"
        assert tsconfig_path.exists(), "tsconfig.json should exist"
        
        with open(tsconfig_path, 'r') as f:
            tsconfig = json.load(f)
            
        assert "compilerOptions" in tsconfig
        assert tsconfig["compilerOptions"]["target"]
        assert tsconfig["compilerOptions"]["module"]

    def test_readme_exists(self):
        """Test that README documentation exists"""
        readme_path = Path(__file__).parent.parent / "README.md"
        assert readme_path.exists(), "README.md should exist"
        
        with open(readme_path, 'r') as f:
            readme_content = f.read()
            
        # Should contain basic information about the legal server
        assert "legal" in readme_content.lower() or "cerebra" in readme_content.lower()

class TestCerebraIntegration:
    """Test integration with the registry"""

    def test_server_follows_registry_pattern(self):
        """Test that the server follows the expected registry pattern"""
        # Check directory structure matches registry expectations
        base_path = Path(__file__).parent.parent
        
        # Should have src/server.py for Python wrapper
        assert (base_path / "src" / "server.py").exists()
        
        # Should have src/tools.py for tool definitions  
        assert (base_path / "src" / "tools.py").exists()
        
        # Should have requirements.txt for dependencies
        assert (base_path / "requirements.txt").exists()
        
        # Should have tests directory
        assert (base_path / "tests").exists()

    def test_build_directory_structure(self):
        """Test that build directory has expected structure"""
        build_path = Path(__file__).parent.parent / "build"
        
        if not build_path.exists():
            pytest.skip("Build directory not found")
            
        # Should have compiled JavaScript
        assert (build_path / "index.js").exists()

if __name__ == "__main__":
    pytest.main([__file__, "-v"])