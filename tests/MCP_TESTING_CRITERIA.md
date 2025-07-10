# MCP SERVER TESTING CRITERIA & EXPECTATIONS

## 🎯 OVERVIEW

This document defines the **mandatory testing criteria** and **success expectations** for all MCP servers in the DevQ.ai ecosystem. Every MCP server must achieve **100% success rate** with real service connections and zero fake/mock data to be considered production-ready.

## 🚨 CRITICAL SUCCESS REQUIREMENTS

### **ABSOLUTE RULE: 100% SUCCESS RATE MANDATORY**
- Any result less than 100% is considered a **COMPLETE FAILURE**
- No partial credit or "acceptable" failure rates
- Must use **REAL services** and **REAL credentials** only
- **ZERO tolerance** for fake/mock/stub data or responses

### **PRP (Project Rules Protocol) COMPLIANCE**
- **ZERO FAKE DATA**: All tool calls must use real MCP server connections
- **AUTHENTIC RESPONSES**: All operations must produce genuine results
- **COMPREHENSIVE TESTING**: Every tool must be tested with multiple scenarios
- **ERROR HANDLING**: Proper error responses for edge cases required
- **TIMESTAMPED RESULTS**: All operations must be logged with precise timestamps

## 📋 TESTING FRAMEWORK STRUCTURE

### **1. Test Categories (All Required)**

#### **A. Core Functionality Tests**
- **Server Initialization**: All components properly initialized
- **Tool Registration**: All tools accessible and properly configured
- **Basic Operations**: Core functionality working as designed
- **Data Storage/Retrieval**: Persistent data operations functional

#### **B. Integration Tests**
- **External Service Connectivity**: Real API connections working
- **Authentication**: Valid credentials and token management
- **Data Export/Import**: All supported formats functional
- **Cross-Service Operations**: Multi-service workflows operational

#### **C. Performance Tests**
- **Response Times**: Sub-second response targets
- **Concurrent Operations**: Multi-user/multi-request handling
- **Resource Usage**: Memory and CPU efficiency validation
- **Scalability**: Load handling capabilities

#### **D. Error Handling Tests**
- **Invalid Inputs**: Graceful handling of malformed requests
- **Network Failures**: Proper timeout and retry mechanisms
- **Authentication Failures**: Clear error messages for auth issues
- **Resource Limits**: Appropriate responses for quota/limit hits

#### **E. Compliance Tests**
- **MCP Protocol**: Full protocol adherence verification
- **Type Safety**: Proper data type enforcement
- **Schema Validation**: Request/response schema compliance
- **Security**: No credential leakage or security vulnerabilities

### **2. Required Test Data Types**

#### **Real Service Connections**
```json
{
  "acceptable": {
    "api_keys": "Real production or sandbox API keys",
    "databases": "Real database connections (local or cloud)",
    "external_services": "Actual third-party service integrations",
    "file_systems": "Real file operations on actual storage"
  },
  "prohibited": {
    "mock_responses": "Simulated API responses",
    "fake_data": "Generated or hardcoded test data",
    "stub_functions": "Non-functional placeholder implementations",
    "dummy_services": "Simulated external service responses"
  }
}
```

## 🎯 SPECIFIC SUCCESS CRITERIA BY MCP TYPE

### **OBSERVABILITY MCPs (e.g., Logfire)**
- **✅ Metrics Collection**: Real metric ingestion with proper timestamps
- **✅ Export Formats**: JSON, Prometheus, CSV all functional
- **✅ Query Operations**: Aggregation, filtering, time-range queries
- **✅ Alert Management**: Creation, modification, deletion operations
- **✅ Health Monitoring**: System and service health checks
- **✅ Performance**: Sub-100ms for status, sub-1s for collection

**Example Success Query:**
```json
{
  "query": {"format": "json", "metric_names": ["cpu_usage"]},
  "expected_result": {
    "format": "valid_json_array",
    "contains": ["name", "value", "timestamp", "tags"],
    "performance": "<100ms response time"
  }
}
```

### **CONTEXT/MEMORY MCPs (e.g., Context7)**
- **✅ Document Storage**: Real embeddings generation and storage
- **✅ Semantic Search**: Actual similarity calculations
- **✅ Context Retrieval**: Accurate document and metadata return
- **✅ External APIs**: OpenAI/Redis connectivity functional
- **✅ Vector Operations**: Real vector database operations
- **✅ Performance**: Sub-100ms for retrieval, sub-500ms for embedding

**Example Success Query:**
```json
{
  "query": {"action": "search", "query": "machine learning", "limit": 5},
  "expected_result": {
    "format": "ranked_results",
    "contains": ["content", "similarity_score", "metadata"],
    "validation": "actual_embedding_calculation"
  }
}
```

### **TESTING MCPs (e.g., PyTest)**
- **✅ Test Execution**: Real test runner operations
- **✅ Coverage Analysis**: Actual code coverage calculation
- **✅ Report Generation**: Valid test reports and artifacts
- **✅ Integration**: Real codebase testing capabilities
- **✅ Configuration**: Test environment setup and teardown
- **✅ Performance**: Test execution time tracking

### **API/SERVICE MCPs (e.g., GitHub, FastAPI)**
- **✅ Authentication**: Real token validation and usage
- **✅ CRUD Operations**: Create, read, update, delete functionality
- **✅ Data Synchronization**: Real-time or batch data operations
- **✅ Webhook Handling**: Event processing capabilities
- **✅ Rate Limiting**: Proper handling of API limits
- **✅ Error Recovery**: Retry logic and failure handling

## 📊 VALIDATION REPORT REQUIREMENTS

### **Report Naming Convention**
```
{mcp_name}-{YYYYMMDD}_{HHMMSS}.json
```

**Examples:**
- `logfire-20250710_033537.json`
- `context7-20250710_025316.json`
- `pytest-20250710_041523.json`

### **Required Report Structure**
```json
{
  "server_info": {
    "name": "string",
    "version": "string",
    "initialization_time": "number (seconds)",
    "tool_count": "number",
    "external_dependencies": ["array of services"]
  },
  "tests": [
    {
      "name": "string",
      "status": "PASSED|FAILED",
      "details": "string (specific results)",
      "timestamp": "ISO 8601 format",
      "performance_metrics": {
        "response_time": "number (seconds)",
        "memory_usage": "number (MB)",
        "data_transferred": "number (bytes)"
      }
    }
  ],
  "performance": {
    "average_response_time": "number",
    "total_operations": "number",
    "memory_efficient": "boolean",
    "concurrent_capable": "boolean"
  },
  "compliance": {
    "mcp_protocol": "compliant|non_compliant",
    "type_safety": "enforced|not_enforced",
    "security": "secure|vulnerable"
  },
  "summary": {
    "overall_status": "PASSED|FAILED",
    "total_tests": "number",
    "passed": "number",
    "failed": "number",
    "success_rate": "number (0-100)",
    "total_time": "number (seconds)"
  }
}
```

## 🔍 VALIDATION EXECUTION PROTOCOL

### **Pre-Testing Setup**
1. **Environment Verification**: Ensure all required credentials available
2. **Dependency Check**: Verify all external services accessible
3. **Clean State**: Reset any cached data or temporary files
4. **Logging Configuration**: Enable detailed operation logging

### **Testing Execution**
1. **Sequential Test Run**: Execute all test categories in order
2. **Real Data Operations**: Perform actual operations with real services
3. **Error Scenario Testing**: Deliberately trigger error conditions
4. **Performance Measurement**: Track timing and resource usage
5. **Result Validation**: Verify all responses contain expected data

### **Post-Testing Validation**
1. **Report Generation**: Create comprehensive JSON validation report
2. **Data Verification**: Confirm all operations produced real results
3. **Performance Analysis**: Verify performance targets met
4. **Cleanup Operations**: Remove test data if necessary
5. **Status Documentation**: Update MCP testing pipeline status

## 🚀 SUCCESS CRITERIA EXAMPLES

### **LOGFIRE MCP - ACTUAL SUCCESS EXAMPLE**
```json
{
  "test": "Metrics Export",
  "query": {"format": "prometheus", "metric_names": ["cpu_usage"]},
  "actual_result": "cpu_usage{host=\"server1\"} 45.2",
  "validation": {
    "metric_name_present": true,
    "value_numeric": true,
    "format_valid": true,
    "response_time": "0.056s"
  },
  "status": "PASSED"
}
```

### **CONTEXT7 MCP - ACTUAL SUCCESS EXAMPLE**
```json
{
  "test": "Semantic Search",
  "query": {"text": "machine learning algorithms", "top_k": 3},
  "actual_result": [
    {
      "content": "Neural networks are a subset of machine learning...",
      "similarity": 0.89,
      "source": "ml_docs.pdf"
    }
  ],
  "validation": {
    "results_count": 3,
    "similarity_calculated": true,
    "content_relevant": true,
    "response_time": "0.234s"
  },
  "status": "PASSED"
}
```

## ❌ FAILURE PATTERNS TO AVOID

### **Common Failure Indicators**
- **Mock Data Usage**: Any simulated or fake responses
- **Network Simulation**: Fake network calls or responses
- **Incomplete Operations**: Partial functionality implementation
- **Performance Issues**: Response times exceeding targets
- **Error Suppression**: Hidden or ignored error conditions

### **Immediate Failure Triggers**
- Success rate < 100%
- Any fake/mock/stub data detected
- Authentication failures with real credentials
- Missing required functionality
- Performance targets not met
- MCP protocol violations

## 🎯 CONTINUOUS IMPROVEMENT

### **Monthly Review Process**
1. **Success Rate Analysis**: Track trends across all MCPs
2. **Performance Monitoring**: Identify degradation patterns
3. **New Test Cases**: Add tests for new functionality
4. **Criteria Updates**: Enhance testing requirements as needed
5. **Best Practice Sharing**: Document successful patterns

### **Failure Response Protocol**
1. **Immediate Investigation**: Diagnose root cause of failures
2. **Rapid Remediation**: Fix issues with highest priority
3. **Re-testing**: Validate fixes with full test suite
4. **Documentation Update**: Record lessons learned
5. **Prevention Measures**: Implement safeguards against recurrence

---

**REMEMBER**: The goal is not just passing tests, but ensuring **production-ready reliability** with **real-world functionality** that users can depend on in critical DevQ.ai workflows.
