# MCP Production Testing Requirements & Business Rules

**Document Version:** 1.0  
**Created:** July 7, 2025  
**Purpose:** Define mandatory testing standards for MCP server production certification

---

## Business Rules for Production Certification

### Rule 1: FUNDAMENTAL REQUIREMENT - Valid Tool Call Testing
**THE MOST IMPORTANT CRITERIA: MCP tools must be tested with valid deliberate tool calls and the MCP must return valid answers to those tool calls.**

**PRIMARY SUCCESS CRITERIA:**
- ✅ **DELIBERATE TOOL CALLS** - Each tool called with intentional, valid parameters
- ✅ **VALID ANSWERS RETURNED** - MCP responds with meaningful, real business results
- ✅ **FUNCTIONAL TOOL EXECUTION** - Tools perform their intended business logic
- ✅ **REAL MCP PROTOCOL** - Actual request/response cycles, not simulated

**PRIMARY FAILURE CRITERIA:**
- ❌ **NO DELIBERATE TOOL CALLS** - Tools not actually invoked with valid parameters
- ❌ **INVALID ANSWERS** - Fake, stub, or hardcoded responses
- ❌ **NON-FUNCTIONAL TOOLS** - Tools don't perform intended business logic
- ❌ **SIMULATED RESPONSES** - Mock or placeholder answers instead of real execution

**SECONDARY SUCCESS CRITERIA:**
- ✅ **100% of tools tested** with valid deliberate calls
- ✅ **All tools return valid business answers** or proper dependency errors
- ✅ **Zero hardcoded/mock responses** across all tools
- ✅ **All tools handle invalid parameters gracefully**

**SECONDARY FAILURE CRITERIA:**
- ❌ **<100% tool coverage** (e.g., Darwin MCP: 2/9 tools = 22% = FAIL)
- ❌ **Any tool returns fake/stub/hardcoded data**
- ❌ **Any tool crashes on invalid input**
- ❌ **Missing tools not discoverable via list_tools()**

### Rule 2: Zero Tolerance for Fake Data
**Any server returning hardcoded, mock, or stub responses is automatically disqualified.**

**SUCCESS CRITERIA:**
- ✅ **Real business logic execution** in all tool responses
- ✅ **Actual computations/API calls** or clear dependency errors
- ✅ **Dynamic responses** based on input parameters
- ✅ **Proper error messages** for missing dependencies

**FAILURE CRITERIA (AUTOMATIC DISQUALIFICATION):**
- ❌ **Hardcoded JSON responses** (same output regardless of input)
- ❌ **Mock API data** or simulated responses
- ❌ **Stub implementations** with placeholder text
- ❌ **"Not implemented" or "Coming soon" messages**
- ❌ **Template responses** not customized for business logic

### Rule 3: Dependency Transparency
**All external dependencies must be documented and properly handled.**

**SUCCESS CRITERIA:**
- ✅ **Clear documentation** of all required dependencies
- ✅ **Graceful error handling** when dependencies unavailable
- ✅ **Actionable error messages** with setup instructions
- ✅ **Health check endpoint** reporting dependency status

**FAILURE CRITERIA:**
- ❌ **Undocumented dependencies** causing silent failures
- ❌ **Server crashes** due to missing credentials/services
- ❌ **Vague error messages** without resolution guidance
- ❌ **No way to verify** dependency status

---

## Mandatory PyTest Framework

### Testing Philosophy
**"If it's not tested with PyTest, it's not production ready."**

All MCP servers must pass comprehensive automated test suites before deployment. Manual testing is insufficient for production certification.

### Core Testing Requirements

#### 1. **Server Initialization Testing**

**SUCCESS CRITERIA:**
- ✅ Server instance created without exceptions
- ✅ All expected tools discoverable via list_tools()
- ✅ Each tool has name, description, and input_schema
- ✅ Tool count matches expected implementation

**FAILURE CRITERIA:**
- ❌ Server initialization throws exceptions
- ❌ list_tools() returns empty list or fewer tools than expected
- ❌ Any tool missing required metadata

```python
@pytest.mark.asyncio
async def test_server_initializes_without_errors(self):
    """SUCCESS: Server starts without exceptions"""
    server = YourMCPServer()
    assert server is not None, "FAIL: Server initialization returned None"
    
@pytest.mark.asyncio  
async def test_all_tools_discoverable(self):
    """SUCCESS: All expected tools discoverable with proper metadata"""
    tools = await server.list_tools()
    assert len(tools) >= EXPECTED_TOOL_COUNT, f"FAIL: Expected {EXPECTED_TOOL_COUNT} tools, got {len(tools)}"
    
    # SUCCESS: Each tool has proper metadata
    for tool in tools:
        assert tool.name is not None, f"FAIL: Tool missing name: {tool}"
        assert tool.description is not None, f"FAIL: Tool missing description: {tool.name}"
        assert hasattr(tool, 'input_schema'), f"FAIL: Tool missing input_schema: {tool.name}"
```

#### 2. **CRITICAL: Valid Tool Call Testing**

**FUNDAMENTAL SUCCESS CRITERIA:**
- ✅ **DELIBERATE TOOL CALLS** - Every tool invoked with intentional, valid parameters
- ✅ **VALID ANSWERS RETURNED** - MCP provides meaningful business results for each call
- ✅ **REAL EXECUTION** - Tools actually perform their intended business logic
- ✅ **AUTHENTIC MCP PROTOCOL** - Genuine request/response cycles, not simulations

**FUNDAMENTAL FAILURE CRITERIA:**
- ❌ **NO ACTUAL TOOL CALLS** - Tools not invoked with real parameters
- ❌ **INVALID/FAKE ANSWERS** - Stub, mock, or hardcoded responses
- ❌ **NON-EXECUTION** - Tools don't perform intended business logic
- ❌ **SIMULATED PROTOCOL** - Mock responses instead of real MCP execution

**ADDITIONAL SUCCESS CRITERIA:**
- ✅ **100% of tools tested** with deliberate valid calls
- ✅ **Dynamic responses** that vary based on input parameters
- ✅ **Proper error handling** for invalid parameters

**ADDITIONAL FAILURE CRITERIA:**
- ❌ **Any tool untested** (partial testing = automatic fail)
- ❌ **Tools crash** on invalid input
- ❌ **"Not implemented"** or placeholder responses

```python
@pytest.mark.asyncio
async def test_all_tools_deliberate_calls_valid_answers(self):
    """FUNDAMENTAL: MCP tools tested with deliberate calls must return valid answers"""
    tools = await server.list_tools()
    
    for tool in tools:
        # FUNDAMENTAL: Make deliberate tool call with valid parameters
        valid_params = self._get_valid_params_for_tool(tool)
        result = await server.call_tool(tool.name, valid_params)
        
        # FUNDAMENTAL: Must return valid answer (not fake/stub)
        assert result is not None, f"FUNDAMENTAL FAIL: Tool {tool.name} returned None"
        assert not self._is_fake_response(result), f"FUNDAMENTAL FAIL: Tool {tool.name} returned invalid answer (fake/stub)"
        
        # FUNDAMENTAL: Must provide real business execution
        assert self._validates_real_execution(result), f"FUNDAMENTAL FAIL: Tool {tool.name} did not execute real business logic"
        
        # FUNDAMENTAL: Must be authentic MCP protocol response
        assert self._validates_authentic_mcp_response(result), f"FUNDAMENTAL FAIL: Tool {tool.name} provided simulated response"

def _is_fake_response(self, result):
    """Detect fake/stub responses - AUTOMATIC FAIL"""
    fake_patterns = [
        "mock", "stub", "fake", "placeholder", "test_data",
        "example", "dummy", "sample", "hardcoded", "not_implemented",
        "coming soon", "todo", "template"
    ]
    
    result_str = str(result).lower()
    if any(pattern in result_str for pattern in fake_patterns):
        return True
        
    # FAIL: Same response for different inputs (hardcoded)
    return self._detects_hardcoded_response(result)

def _validates_business_logic(self, result):
    """SUCCESS: Real business value provided"""
    if isinstance(result, TextContent):
        content = result.text
        
        # SUCCESS: Proper error messages acceptable
        if "error" in content.lower():
            return self._is_proper_dependency_error(content)
            
        # SUCCESS: Real computation/data patterns
        return len(content) > 50 and self._shows_real_computation(content)
        
    return False
```

#### 3. **Error Handling Validation**

**SUCCESS CRITERIA:**
- ✅ **Graceful handling** of invalid parameters
- ✅ **Clear error messages** with actionable guidance
- ✅ **No server crashes** on bad input
- ✅ **Proper error format** in responses

**FAILURE CRITERIA:**
- ❌ **Server crashes** on invalid input
- ❌ **Vague error messages** without guidance
- ❌ **Silent failures** (no error indication)
- ❌ **Exception leakage** in responses

```python
@pytest.mark.asyncio
async def test_error_handling_comprehensive(self):
    """SUCCESS: Graceful error handling for all failure modes"""
    tools = await server.list_tools()
    
    for tool in tools:
        # SUCCESS: Handle invalid parameters gracefully
        result = await server.call_tool(tool.name, {"invalid": "params"})
        assert result is not None, f"FAIL: Tool {tool.name} returned None on invalid input"
        assert "error" in str(result).lower(), f"FAIL: Tool {tool.name} didn't indicate error for invalid params"
        
        # SUCCESS: Handle missing parameters appropriately
        result = await server.call_tool(tool.name, {})
        assert result is not None, f"FAIL: Tool {tool.name} returned None on empty params"
        
        # FAIL: Exception traces leaked to user
        assert not self._contains_stack_trace(result), f"FAIL: Tool {tool.name} leaked exception details"

def _contains_stack_trace(self, result):
    """FAIL: Stack traces should not leak to users"""
    trace_indicators = ["traceback", "file \"/", "line ", "in <module>", "exception occurred"]
    result_str = str(result).lower()
    return any(indicator in result_str for indicator in trace_indicators)
```

---

## PyTest Templates by Server Type

### Template 1: Self-Contained Python MCP Server
```python
"""
Template for servers with no external dependencies
Requirements: All tools functional, no API calls needed
"""
import pytest
import asyncio
from mcp.types import TextContent

class TestSelfContainedMCPServer:
    @pytest.fixture
    async def server(self):
        from your_server import YourMCPServer
        return YourMCPServer()
        
    @pytest.mark.asyncio
    async def test_all_tools_functional_no_deps(self, server):
        """All tools must work without external dependencies"""
        tools = await server.list_tools()
        
        for tool in tools:
            result = await server.call_tool(tool.name, {})
            
            # Must provide real business value
            assert not self._is_stub_response(result)
            assert self._provides_computation_or_logic(result)
            
    def _provides_computation_or_logic(self, result):
        """Verify actual computation occurred"""
        if isinstance(result, TextContent):
            content = result.text
            
            # Look for signs of real computation
            computation_indicators = [
                "calculated", "computed", "generated", "processed",
                "algorithm", "result", "output", "analysis"
            ]
            
            content_lower = content.lower()
            return any(indicator in content_lower for indicator in computation_indicators)
            
        return False
```

### Template 2: API-Dependent MCP Server
```python
"""
Template for servers requiring external API access
Requirements: Proper credential handling, real API calls or clear errors
"""
import pytest
import os

class TestAPIMCPServer:
    @pytest.fixture
    async def server(self):
        # Check for credentials
        if not os.getenv('API_KEY'):
            pytest.skip("API credentials not configured")
            
        from your_api_server import APIServer
        return APIServer()
        
    @pytest.mark.asyncio
    async def test_api_tools_real_calls_or_clear_errors(self, server):
        """API tools must make real calls or provide clear setup errors"""
        tools = await server.list_tools()
        
        for tool in tools:
            result = await server.call_tool(tool.name, {})
            
            if "error" in str(result).lower():
                # Error must be about configuration, not fake
                assert self._is_configuration_error(result)
            else:
                # Must be real API response
                assert not self._is_mock_api_response(result)
                
    def _is_configuration_error(self, result):
        """Verify error is about missing configuration"""
        config_terms = [
            "credential", "api_key", "token", "authentication",
            "configuration", "setup", "permission", "access"
        ]
        
        result_str = str(result).lower()
        return any(term in result_str for term in config_terms)
        
    def _is_mock_api_response(self, result):
        """Detect mock API responses - AUTOMATIC FAIL"""
        mock_patterns = [
            "mock_api", "fake_api", "test_api", "dummy_api",
            "simulated", "mock_response", "fake_data"
        ]
        
        result_str = str(result).lower()
        return any(pattern in result_str for pattern in mock_patterns)
```

### Template 3: FastMCP Framework Server
```python
"""
Template for FastMCP-based implementations
Requirements: Proper FastMCP integration, real tool implementations
"""
import pytest
from fastmcp import FastMCP

class TestFastMCPServer:
    @pytest.fixture
    async def app(self):
        from your_fastmcp_app import app
        return app
        
    @pytest.mark.asyncio
    async def test_fastmcp_tools_real_implementations(self, app):
        """FastMCP tools must have real implementations"""
        tools = app.list_tools()
        
        for tool_name in tools:
            result = await app.call_tool(tool_name, {})
            
            # Must not be FastMCP template responses
            assert not self._is_fastmcp_template(result)
            assert self._is_custom_implementation(result)
            
    def _is_fastmcp_template(self, result):
        """Detect unmodified FastMCP templates"""
        template_patterns = [
            "fastmcp template", "not implemented", "todo",
            "replace this", "template response", "placeholder"
        ]
        
        result_str = str(result).lower()
        return any(pattern in result_str for pattern in template_patterns)
        
    def _is_custom_implementation(self, result):
        """Verify custom business logic implementation"""
        # Must have substantial content indicating real implementation
        result_str = str(result)
        return len(result_str) > 20 and not self._is_fastmcp_template(result)
```

---

## Production Certification Process

### Phase 1: Automated PyTest Validation (Required)

**SUCCESS CRITERIA:**
- ✅ **All PyTests pass** without exceptions
- ✅ **100% tool coverage** verified and tested
- ✅ **Zero fake/stub responses** detected
- ✅ **All error scenarios** handled gracefully
- ✅ **No stack traces** leaked to users

**FAILURE CRITERIA:**
- ❌ **Any PyTest failure** = automatic disqualification
- ❌ **<100% tool coverage** = not production ready
- ❌ **Fake responses detected** = automatic disqualification
- ❌ **Server crashes** on invalid input = automatic disqualification

**Actions:**
1. **Install test dependencies**: `pip install pytest pytest-asyncio`
2. **Run comprehensive test suite**: `pytest test_mcp_production.py -v`
3. **Verify 100% tool coverage**: All tools must be tested and functional
4. **Check zero fake responses**: Automated detection of stub implementations
5. **Validate error handling**: Proper dependency error messages

### Phase 2: Manual Integration Testing (Required)

**SUCCESS CRITERIA:**
- ✅ **External services connect** or provide clear setup errors
- ✅ **Response times <5 seconds** for all operations
- ✅ **Memory usage <500MB** during normal operations
- ✅ **Credentials handled securely** (no logging/exposure)
- ✅ **Input validation** prevents injection attacks

**FAILURE CRITERIA:**
- ❌ **Silent failures** with external services
- ❌ **Response times >10 seconds** for basic operations
- ❌ **Memory leaks** or excessive resource usage
- ❌ **Credentials exposed** in logs or responses
- ❌ **Security vulnerabilities** in input handling

**Actions:**
1. **External service integration**: Test with real APIs, databases
2. **Performance under load**: Response times within acceptable limits
3. **Resource usage validation**: Memory, CPU consumption reasonable
4. **Security testing**: Credential handling, input validation

### Phase 3: Production Deployment Readiness (Required)

**SUCCESS CRITERIA:**
- ✅ **Complete documentation** with setup examples
- ✅ **Health check endpoint** reporting all dependencies
- ✅ **Logging integration** for monitoring and debugging
- ✅ **Deployment works** in clean environment
- ✅ **Rollback procedures** tested and documented

**FAILURE CRITERIA:**
- ❌ **Missing/incomplete documentation**
- ❌ **No health check** or dependency validation
- ❌ **No logging** for production debugging
- ❌ **Deployment fails** in clean environment
- ❌ **No rollback plan** for failures

**Actions:**
1. **Documentation complete**: README, setup instructions, examples
2. **Monitoring integration**: Health checks, logging, error reporting
3. **Deployment testing**: Works in production environment
4. **Rollback procedures**: Clear steps for deployment issues

---

## Automatic Disqualification Criteria

### Immediate Production Failure (Zero Tolerance)
- **Hardcoded responses** in any tool output
- **Mock/fake data** in business logic implementations  
- **Stub functions** masquerading as real functionality
- **Template responses** not customized for business logic
- **Missing error handling** for dependency failures
- **Incomplete tool testing** (less than 100% tool verification)

### Configuration Failures (Must Fix Before Production)
- **Missing dependency documentation** 
- **Unclear setup instructions**
- **No health check endpoint**
- **Poor error messages** for missing dependencies
- **No recovery procedures** for common failures

---

## Implementation Checklist

### Required Files for Production Certification

**SUCCESS CRITERIA: All files present and properly implemented**

- [ ] ✅ `test_mcp_production.py` - Comprehensive PyTest suite with 100% tool coverage
- [ ] ✅ `requirements.txt` - All dependencies listed with specific versions
- [ ] ✅ `README.md` - Complete setup instructions with examples
- [ ] ✅ `health_check()` method - Reports status of all dependencies
- [ ] ✅ `error_documentation.md` - Troubleshooting guide for common issues

**FAILURE CRITERIA: Missing any required file = not production ready**

### Required Test Coverage

**SUCCESS CRITERIA: All tests pass with real functionality validation**

- [ ] ✅ Server initialization without errors or exceptions
- [ ] ✅ All tools discoverable via list_tools() with proper metadata
- [ ] ✅ **100% of tools** functional with valid parameters (no partial testing)
- [ ] ✅ All tools handle invalid parameters gracefully without crashes
- [ ] ✅ Dependency errors provide clear, actionable setup guidance
- [ ] ✅ **Zero hardcoded/mock/stub responses** in any tool (automatic disqualification)
- [ ] ✅ Performance acceptable under basic load (<5 second response times)

**FAILURE CRITERIA: Any test failure = automatic production disqualification**

### Required Documentation

**SUCCESS CRITERIA: Complete, accurate documentation enabling independent deployment**

- [ ] ✅ Clear dependency requirements with installation commands
- [ ] ✅ Step-by-step setup instructions that work in clean environment
- [ ] ✅ Working example usage for each tool with expected outputs
- [ ] ✅ Troubleshooting guide addressing common setup errors
- [ ] ✅ Production deployment procedures with rollback steps

**FAILURE CRITERIA: Incomplete documentation preventing successful deployment**

### Production Readiness Verification

**FINAL SUCCESS CRITERIA - ALL MUST BE TRUE:**
- ✅ **PyTest suite passes 100%** - No test failures allowed
- ✅ **All tools verified functional** - 100% coverage, no fake responses
- ✅ **Documentation enables deployment** - Third party can deploy successfully
- ✅ **Error handling graceful** - No crashes, clear error messages
- ✅ **Dependencies documented** - All requirements specified
- ✅ **Security validated** - Credentials secure, input sanitized
- ✅ **Performance acceptable** - Response times meet standards

**FINAL FAILURE CRITERIA - ANY ONE FAILS ENTIRE CERTIFICATION:**
- ❌ **Any PyTest failure** 
- ❌ **<100% tool verification**
- ❌ **Any fake/stub responses**
- ❌ **Documentation gaps**
- ❌ **Missing error handling**
- ❌ **Security vulnerabilities**
- ❌ **Performance failures**

---

**Bottom Line:** No MCP server reaches production without passing comprehensive PyTest validation demonstrating real business functionality across 100% of its tools.