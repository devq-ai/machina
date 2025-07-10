# MCP Testing Framework Usage Guide

## 🎯 Overview

This guide explains how to use the comprehensive MCP testing framework that enforces 100% success rate requirements with real service connections and zero tolerance for mock/fake data.

## 📋 Quick Start

### Prerequisites

1. **Environment Setup**
   ```bash
   cd machina
   source .env  # Load real API credentials
   pip install pytest pytest-asyncio pytest-cov pytest-json-report
   ```

2. **Required Credentials**
   ```bash
   # Logfire MCP
   export LOGFIRE_WRITE_TOKEN="pylf_v1_us_..."
   export LOGFIRE_READ_TOKEN="pylf_v1_us_..."

   # Context7 MCP
   export OPENAI_API_KEY="sk-proj-..."
   export UPSTASH_REDIS_REST_URL="https://..."
   export UPSTASH_REDIS_REST_TOKEN="..."

   # Other MCPs as needed
   ```

### Basic Usage

#### Test Single MCP
```bash
# Test Logfire MCP with full validation
python run_mcp_tests.py --mcp logfire

# Test with performance focus only
python run_mcp_tests.py --mcp logfire --performance-only

# Test with verbose output
python run_mcp_tests.py --mcp context7 --verbose
```

#### Test All MCPs
```bash
# Comprehensive testing of all MCPs
python run_mcp_tests.py --mcp all

# Save custom report location
python run_mcp_tests.py --mcp all --output results/full_validation.json
```

#### Direct PyTest Execution
```bash
# Run pytest for specific MCP
cd primer/mcp-servers/logfire-mcp
pytest tests/ -v --cov=. --cov-report=html

# Run with real service markers
pytest tests/ -m "real_services" -v

# Run performance tests only
pytest tests/ -m "performance" -v
```

## 🎯 Success Criteria (100% Required)

### Critical Requirements

- **100% Test Pass Rate**: Any failure = complete failure
- **Real Service Connections**: No mock/fake/stub data allowed
- **Performance Targets Met**: All response time requirements
- **Full MCP Protocol Compliance**: Complete protocol adherence
- **90%+ Code Coverage**: Comprehensive test coverage required

### Performance Targets by MCP Type

| MCP Type | Status Response | Collection/Query | Health Check |
|----------|----------------|------------------|--------------|
| Logfire  | <100ms         | <1s              | <2s          |
| Context7 | <200ms         | <500ms           | <1s          |
| Memory   | <50ms          | <100ms           | <500ms       |
| PyTest   | <100ms         | <5s              | <1s          |

## 📊 Test Categories

### A. Core Functionality Tests
- **Server Initialization**: All components properly initialized
- **Tool Registration**: All tools accessible and configured
- **Basic Operations**: Core functionality working
- **Data Storage/Retrieval**: Persistent operations functional

### B. Integration Tests
- **External Service Connectivity**: Real API connections
- **Authentication**: Valid credentials and tokens
- **Data Export/Import**: All formats functional
- **Cross-Service Operations**: Multi-service workflows

### C. Performance Tests
- **Response Times**: Sub-second targets
- **Concurrent Operations**: Multi-user handling
- **Resource Usage**: Memory/CPU efficiency
- **Scalability**: Load handling capabilities

### D. Error Handling Tests
- **Invalid Inputs**: Graceful malformed request handling
- **Network Failures**: Timeout and retry mechanisms
- **Authentication Failures**: Clear error messages
- **Resource Limits**: Appropriate quota responses

### E. Compliance Tests
- **MCP Protocol**: Full protocol adherence
- **Type Safety**: Proper data type enforcement
- **Schema Validation**: Request/response compliance
- **Security**: No credential leakage

## 🔧 Test Framework Components

### 1. Validation Scripts
Located: `primer/mcp-servers/{mcp-name}/validate_server.py`

Purpose: Comprehensive server validation with real service testing
- Tests all MCP tools with real data
- Generates detailed JSON reports
- Measures performance metrics
- Validates protocol compliance

Usage:
```bash
cd primer/mcp-servers/logfire-mcp
python validate_server.py
```

Output: `validation_report_YYYYMMDD_HHMMSS.json`

### 2. PyTest Suites
Located: `primer/mcp-servers/{mcp-name}/tests/test_{mcp-name}.py`

Purpose: Comprehensive unit and integration testing
- Real service connection tests
- Performance validation
- Error handling verification
- Type safety enforcement

Usage:
```bash
cd primer/mcp-servers/logfire-mcp
pytest tests/test_logfire_mcp.py -v
```

### 3. Test Execution Script
Located: `machina/run_mcp_tests.py`

Purpose: Orchestrate comprehensive testing across all MCPs
- Environment validation
- Parallel test execution
- Performance analysis
- Comprehensive reporting

### 4. Testing Criteria Document
Located: `machina/MCP_TESTING_CRITERIA.md`

Purpose: Define success requirements and standards
- 100% success rate requirements
- Performance targets
- Real service connection mandates
- Report format specifications

## 📋 Report Formats

### Validation Reports
Naming: `{mcp-name}-YYYYMMDD_HHMMSS.json`
Location: `machina/`

Structure:
```json
{
  "server_info": {
    "name": "logfire-mcp",
    "version": "1.0.0",
    "initialization_time": 0.003,
    "prometheus_metrics": 6,
    "external_dependencies": ["logfire-api"]
  },
  "tests": [
    {
      "name": "Metrics Export",
      "status": "PASSED",
      "details": "All formats working",
      "timestamp": "2025-07-10T03:35:36.712120"
    }
  ],
  "summary": {
    "overall_status": "PASSED",
    "success_rate": 100.0,
    "total_tests": 12,
    "passed": 12,
    "failed": 0
  }
}
```

### Comprehensive Reports
Naming: `mcp_test_comprehensive_YYYYMMDD_HHMMSS.json`

Contains:
- All individual MCP results
- Cross-MCP performance comparison
- Overall ecosystem status
- Recommendations for failures

## 🚀 Development Workflow

### Adding New Tests

1. **Create Test Case**
   ```python
   @pytest.mark.asyncio
   async def test_new_functionality(self, logfire_server):
       """Test new functionality with real service."""
       # PASS CRITERIA: Specific success requirements
       result = await logfire_server._handle_new_function({})
       assert result["status"] == "success"
   ```

2. **Add Performance Validation**
   ```python
   def test_performance_target(self, performance_tracker):
       performance_tracker.start("operation")
       # ... perform operation
       duration = performance_tracker.end("operation")
       assert duration < 0.1  # 100ms target
   ```

3. **Update Criteria Document**
   - Add new success requirements
   - Define performance targets
   - Specify validation methods

### Debugging Failures

1. **Check Environment**
   ```bash
   python run_mcp_tests.py --mcp logfire --verbose
   ```

2. **Run Single Test**
   ```bash
   cd primer/mcp-servers/logfire-mcp
   pytest tests/test_logfire_mcp.py::TestLogfireMCPComprehensive::test_specific_function -v -s
   ```

3. **Analyze Performance**
   ```bash
   pytest tests/ -m "performance" --durations=10
   ```

4. **Review Validation Details**
   ```bash
   python validate_server.py
   cat validation_report_*.json | jq '.tests[] | select(.status=="FAILED")'
   ```

## ❌ Common Failure Patterns

### Authentication Issues
```bash
# Check credentials
echo $LOGFIRE_WRITE_TOKEN | cut -c1-20
echo $OPENAI_API_KEY | cut -c1-20

# Test connectivity
curl -H "Authorization: Bearer $LOGFIRE_WRITE_TOKEN" \
     https://logfire-us.pydantic.dev/api/health
```

### Performance Failures
```bash
# Profile slow operations
pytest tests/ --profile --profile-svg

# Check resource usage
pytest tests/ -m "performance" --benchmark-only
```

### Mock Data Detection
```bash
# Search for prohibited patterns
grep -r "mock\|fake\|stub" tests/
grep -r "return.*fake\|hardcoded" primer/mcp-servers/*/
```

## 🎯 Best Practices

### Test Design
- **Real Data Only**: Connect to actual services
- **Comprehensive Coverage**: Test all code paths
- **Performance Aware**: Include timing validations
- **Error Scenarios**: Test failure modes
- **Cleanup**: Remove test data after completion

### Maintenance
- **Regular Updates**: Keep credentials current
- **Performance Monitoring**: Track degradation
- **Dependency Updates**: Maintain service compatibility
- **Documentation**: Update criteria as needed

### Continuous Integration
```yaml
# Example CI configuration
test-mcps:
  runs-on: ubuntu-latest
  env:
    LOGFIRE_WRITE_TOKEN: ${{ secrets.LOGFIRE_WRITE_TOKEN }}
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
  steps:
    - name: Test All MCPs
      run: python run_mcp_tests.py --mcp all
    - name: Validate 100% Success
      run: |
        if [ "$(jq -r '.summary.overall_status' mcp_test_*.json)" != "PASSED" ]; then
          echo "❌ Tests failed - 100% success rate required"
          exit 1
        fi
```

## 📞 Support

### Getting Help
- Review `MCP_TESTING_CRITERIA.md` for requirements
- Check existing test examples in `tests/test_*_mcp.py`
- Examine validation scripts for implementation patterns
- Use `--verbose` flag for detailed debugging output

### Reporting Issues
When tests fail:
1. Include full error output
2. Attach validation report JSON
3. Specify environment details
4. Describe expected vs actual behavior
5. Confirm real credentials are used

### Contributing
1. Follow established test patterns
2. Maintain 100% success requirement
3. Use real service connections only
4. Update documentation for new features
5. Test across all supported MCPs

---

**Remember**: The goal is production-ready reliability with real-world functionality that users can depend on in critical DevQ.ai workflows. Anything less than 100% success rate is unacceptable for production deployment.
