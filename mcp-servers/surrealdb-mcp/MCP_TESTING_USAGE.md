# MCP Testing Usage Guide for SurrealDB MCP Server

## **🚀 QUICK START GUIDE**

This guide provides practical instructions for testing the SurrealDB MCP Server using the comprehensive testing framework.

### **⚡ INSTANT VALIDATION**

```bash
# Quick validation of SurrealDB MCP server
cd machina/primer/mcp-servers/surrealdb-mcp
python validate_server.py
```

### **🧪 COMPREHENSIVE TESTING**

```bash
# Run full PyTest suite
pytest tests/test_surrealdb_mcp.py -v --cov=. --cov-report=html

# Run specific test categories
pytest tests/test_surrealdb_mcp.py::test_core_functionality -v
pytest tests/test_surrealdb_mcp.py::test_performance_targets -v
pytest tests/test_surrealdb_mcp.py::test_error_handling -v
```

---

## **📋 PREREQUISITES**

### **1. SurrealDB Server Setup**

```bash
# Install SurrealDB (if not already installed)
curl --proto '=https' --tlsv1.2 -sSf https://install.surrealdb.com | sh

# Start SurrealDB server
surreal start --log trace --user root --pass root memory
# or for persistent storage:
surreal start --log trace --user root --pass root file://mydatabase.db
```

### **2. Environment Configuration**

```bash
# Required environment variables
export SURREALDB_URL="ws://localhost:8000/rpc"
export SURREALDB_USERNAME="root"
export SURREALDB_PASSWORD="root"
export SURREALDB_NAMESPACE="devqai"
export SURREALDB_DATABASE="main"

# Optional testing configuration
export SURREALDB_TIMEOUT="30"
export SURREALDB_RECONNECT_ATTEMPTS="3"
export TEST_PERFORMANCE_TARGETS="true"
```

### **3. Python Dependencies**

```bash
# Install testing dependencies
pip install pytest pytest-asyncio pytest-cov pytest-mock httpx aiofiles
pip install -r requirements.txt
```

---

## **🔧 TESTING COMMANDS**

### **Basic Test Execution**

```bash
# Run all tests with verbose output
pytest tests/test_surrealdb_mcp.py -v

# Run tests with coverage report
pytest tests/test_surrealdb_mcp.py --cov=surrealdb_mcp --cov-report=html

# Run tests in parallel (faster execution)
pytest tests/test_surrealdb_mcp.py -n auto
```

### **Category-Specific Testing**

```bash
# Core functionality tests
pytest tests/test_surrealdb_mcp.py -k "core_functionality" -v

# Integration tests (requires real SurrealDB)
pytest tests/test_surrealdb_mcp.py -k "integration" -v

# Performance tests
pytest tests/test_surrealdb_mcp.py -k "performance" -v

# Error handling tests
pytest tests/test_surrealdb_mcp.py -k "error_handling" -v

# Compliance tests
pytest tests/test_surrealdb_mcp.py -k "compliance" -v
```

### **Advanced Testing Options**

```bash
# Run tests with real service validation
pytest tests/test_surrealdb_mcp.py --real-service -v

# Skip slow tests (performance tests)
pytest tests/test_surrealdb_mcp.py -m "not slow" -v

# Run only failed tests from last run
pytest tests/test_surrealdb_mcp.py --lf -v

# Generate detailed test report
pytest tests/test_surrealdb_mcp.py --html=report.html --self-contained-html
```

---

## **📊 TEST EXECUTION EXAMPLES**

### **Example 1: Complete Test Suite**

```bash
# Full validation with all categories
pytest tests/test_surrealdb_mcp.py -v --cov=surrealdb_mcp --cov-report=html

# Expected output:
# ========== test session starts ==========
# tests/test_surrealdb_mcp.py::test_server_initialization PASSED     [  7%]
# tests/test_surrealdb_mcp.py::test_tool_registration PASSED         [ 14%]
# tests/test_surrealdb_mcp.py::test_real_surrealdb_connectivity PASSED [ 21%]
# tests/test_surrealdb_mcp.py::test_document_operations PASSED       [ 28%]
# tests/test_surrealdb_mcp.py::test_graph_operations PASSED          [ 35%]
# tests/test_surrealdb_mcp.py::test_key_value_operations PASSED      [ 42%]
# tests/test_surrealdb_mcp.py::test_query_execution PASSED           [ 49%]
# tests/test_surrealdb_mcp.py::test_performance_targets PASSED       [ 56%]
# tests/test_surrealdb_mcp.py::test_concurrent_operations PASSED     [ 63%]
# tests/test_surrealdb_mcp.py::test_error_handling PASSED            [ 70%]
# tests/test_surrealdb_mcp.py::test_mcp_protocol_compliance PASSED   [ 77%]
# tests/test_surrealdb_mcp.py::test_data_type_safety PASSED          [ 84%]
# tests/test_surrealdb_mcp.py::test_security_validation PASSED       [ 91%]
# tests/test_surrealdb_mcp.py::test_cleanup_operations PASSED        [100%]
#
# ========== 14 passed, 0 failed in 2.45s ==========
# Coverage: 95%
```

### **Example 2: Performance Validation**

```bash
# Run performance tests with benchmarking
pytest tests/test_surrealdb_mcp.py::test_performance_targets -v --benchmark-autosave

# Expected output:
# tests/test_surrealdb_mcp.py::test_performance_targets_status PASSED
# tests/test_surrealdb_mcp.py::test_performance_targets_document_ops PASSED
# tests/test_surrealdb_mcp.py::test_performance_targets_graph_traversal PASSED
# tests/test_surrealdb_mcp.py::test_performance_targets_query_execution PASSED
#
# Performance Results:
# - Status Response: 0.023s (target: <0.1s) ✅
# - Document Create: 0.156s (target: <0.2s) ✅
# - Graph Traverse: 0.234s (target: <0.5s) ✅
# - Query Execute: 0.445s (target: <1.0s) ✅
```

### **Example 3: Integration Testing**

```bash
# Test real SurrealDB service connectivity
pytest tests/test_surrealdb_mcp.py::test_real_surrealdb_connectivity -v

# Expected output:
# tests/test_surrealdb_mcp.py::test_real_surrealdb_connectivity PASSED
#
# Validation Results:
# - Connection established: ✅
# - Authentication successful: ✅
# - Namespace accessible: ✅
# - Database accessible: ✅
# - Response time: 0.045s
```

---

## **🛠️ DEVELOPMENT WORKFLOW**

### **1. Test-Driven Development**

```bash
# Start development session
cd machina/primer/mcp-servers/surrealdb-mcp

# Run tests continuously during development
pytest tests/test_surrealdb_mcp.py --looponfail

# Add new test for feature
# Edit tests/test_surrealdb_mcp.py and add test_new_feature()

# Run specific test during development
pytest tests/test_surrealdb_mcp.py::test_new_feature -v
```

### **2. Debugging Failed Tests**

```bash
# Run with detailed output and don't capture stdout
pytest tests/test_surrealdb_mcp.py -v -s --tb=long

# Run with pdb debugger on failure
pytest tests/test_surrealdb_mcp.py --pdb

# Run with logging enabled
pytest tests/test_surrealdb_mcp.py --log-cli-level=DEBUG
```

### **3. Performance Analysis**

```bash
# Run with profiling
pytest tests/test_surrealdb_mcp.py --profile

# Run with memory profiling
pytest tests/test_surrealdb_mcp.py --profile-svg

# Generate performance report
pytest tests/test_surrealdb_mcp.py --benchmark-json=benchmark.json
```

---

## **📈 VALIDATION EXAMPLES**

### **Document Operations Validation**

```python
# Example test execution result
{
  "test": "Document CRUD Operations",
  "operations": [
    {
      "action": "create_document",
      "table": "users",
      "data": {"name": "Alice Johnson", "email": "alice@example.com"},
      "result": {
        "id": "users:alice_001",
        "name": "Alice Johnson",
        "email": "alice@example.com",
        "created_at": "2025-01-26T10:30:00Z"
      },
      "validation": {
        "id_format_correct": true,
        "data_preserved": true,
        "timestamp_added": true,
        "response_time": "0.023s"
      },
      "status": "PASSED"
    },
    {
      "action": "get_document",
      "id": "users:alice_001",
      "result": {
        "id": "users:alice_001",
        "name": "Alice Johnson",
        "email": "alice@example.com",
        "created_at": "2025-01-26T10:30:00Z"
      },
      "validation": {
        "document_retrieved": true,
        "data_integrity": true,
        "response_time": "0.018s"
      },
      "status": "PASSED"
    }
  ],
  "overall_status": "PASSED"
}
```

### **Graph Operations Validation**

```python
# Example graph traversal result
{
  "test": "Graph Traversal Operations",
  "setup": [
    {"create_node": "users:alice", "data": {"name": "Alice", "role": "developer"}},
    {"create_node": "companies:acme", "data": {"name": "ACME Corp", "industry": "tech"}},
    {"create_relation": "alice -> works_at -> acme", "properties": {"position": "senior"}}
  ],
  "traversal": {
    "start_node": "users:alice",
    "depth": 2,
    "relations": ["works_at", "knows"],
    "result": {
      "nodes": [
        {"id": "users:alice", "name": "Alice", "role": "developer"},
        {"id": "companies:acme", "name": "ACME Corp", "industry": "tech"}
      ],
      "edges": [
        {"from": "users:alice", "to": "companies:acme", "type": "works_at", "properties": {"position": "senior"}}
      ]
    },
    "validation": {
      "traversal_complete": true,
      "relationships_found": true,
      "data_integrity": true,
      "response_time": "0.234s"
    },
    "status": "PASSED"
  }
}
```

### **Performance Validation**

```python
# Example performance test results
{
  "test": "Performance Targets Validation",
  "benchmarks": [
    {
      "operation": "status_check",
      "target": "< 100ms",
      "actual": "0.023s",
      "status": "PASSED",
      "margin": "77ms under target"
    },
    {
      "operation": "document_create",
      "target": "< 200ms",
      "actual": "0.156s",
      "status": "PASSED",
      "margin": "44ms under target"
    },
    {
      "operation": "graph_traverse_depth3",
      "target": "< 500ms",
      "actual": "0.234s",
      "status": "PASSED",
      "margin": "266ms under target"
    },
    {
      "operation": "complex_query",
      "target": "< 1000ms",
      "actual": "0.445s",
      "status": "PASSED",
      "margin": "555ms under target"
    }
  ],
  "overall_performance": "EXCELLENT",
  "all_targets_met": true
}
```

---

## **🔍 TROUBLESHOOTING**

### **Common Issues and Solutions**

#### **1. SurrealDB Connection Failed**

```bash
# Check if SurrealDB is running
curl http://localhost:8000/status

# If not running, start it
surreal start --log trace --user root --pass root memory

# Check connection parameters
echo $SURREALDB_URL
echo $SURREALDB_USERNAME
echo $SURREALDB_PASSWORD
```

#### **2. Authentication Errors**

```bash
# Test authentication manually
surreal sql --conn ws://localhost:8000/rpc --user root --pass root --ns devqai --db main

# If authentication fails, verify credentials
export SURREALDB_USERNAME="root"
export SURREALDB_PASSWORD="root"
```

#### **3. Performance Test Failures**

```bash
# Run performance tests with debugging
pytest tests/test_surrealdb_mcp.py::test_performance_targets -v -s --tb=short

# Check system resources
top -p $(pgrep surreal)
htop

# Adjust performance targets if needed (in pytest.ini)
performance_timeout = 2.0  # Increase timeout for slower systems
```

#### **4. Test Environment Issues**

```bash
# Clean test environment
rm -rf test_data/
mkdir test_data

# Reset SurrealDB (if using file storage)
surreal start --log trace --user root --pass root file://test_database.db

# Clear Python cache
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} +
```

---

## **📋 BEST PRACTICES**

### **1. Test Organization**

- **Group related tests** in classes (e.g., `TestDocumentOperations`)
- **Use descriptive test names** that explain what is being tested
- **Keep tests independent** - each test should be able to run in isolation
- **Use fixtures** for common setup and teardown operations

### **2. Performance Testing**

- **Always test with real SurrealDB** server, not mocks
- **Use consistent test data** for reproducible results
- **Monitor system resources** during performance tests
- **Set realistic targets** based on hardware capabilities

### **3. Error Testing**

- **Test all error conditions** including network failures, invalid inputs, and resource limits
- **Verify error messages** are clear and actionable
- **Test recovery mechanisms** and retry logic
- **Validate proper cleanup** after errors

### **4. Integration Testing**

- **Test with real services** whenever possible
- **Validate data integrity** across all operations
- **Test concurrent access** patterns
- **Verify transaction behavior** and consistency

---

## **🎯 SUCCESS METRICS**

### **Target Metrics**

- **Test Coverage**: ≥ 90% line coverage
- **Success Rate**: 100% (all tests pass)
- **Performance**: All operations meet defined targets
- **Reliability**: Tests pass consistently across multiple runs

### **Quality Indicators**

- **No flaky tests** - tests should pass consistently
- **Clear error messages** - failures should be easy to understand
- **Fast execution** - test suite should complete in reasonable time
- **Comprehensive coverage** - all MCP tools and edge cases tested

---

## **🔄 CONTINUOUS INTEGRATION**

### **CI/CD Pipeline Integration**

```bash
# Add to CI/CD pipeline
script:
  - export SURREALDB_URL="ws://localhost:8000/rpc"
  - export SURREALDB_USERNAME="root"
  - export SURREALDB_PASSWORD="root"
  - surreal start --log trace --user root --pass root memory &
  - sleep 5  # Wait for SurrealDB to start
  - pytest tests/test_surrealdb_mcp.py --cov=surrealdb_mcp --cov-report=xml
  - coverage report --fail-under=90
```

### **Automated Testing**

```bash
# Run tests on code changes
pytest-watch tests/test_surrealdb_mcp.py

# Run tests with notifications
pytest tests/test_surrealdb_mcp.py --notify
```

---

**🎯 GOAL**: Maintain 100% test success rate with comprehensive validation of all SurrealDB MCP server functionality, ensuring production-ready quality and performance.
