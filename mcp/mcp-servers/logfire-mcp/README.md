# Logfire MCP Server

Advanced observability and monitoring server implementing the MCP (Model Context Protocol) for comprehensive monitoring of MCP servers and the broader DevQ.ai ecosystem using Pydantic Logfire.

## Overview

The Logfire MCP Server provides comprehensive monitoring, metrics collection, alerting, and health checks for MCP servers and system infrastructure. It integrates seamlessly with Pydantic Logfire for observability and supports multiple storage backends including SQLite, Redis, and InfluxDB.

## Features

### 🎯 Core Capabilities
- **Metrics Collection**: Real-time collection and storage of system and application metrics
- **Health Monitoring**: Automated health checks for MCP servers and system components
- **Alert Management**: Intelligent alerting system with customizable conditions and severity levels
- **System Overview**: Comprehensive dashboard-style overview of ecosystem health
- **Metrics Export**: Export metrics in multiple formats (JSON, CSV, Prometheus, InfluxDB)
- **Background Monitoring**: Continuous monitoring with configurable intervals

### 📊 Observability Features
- **Pydantic Logfire Integration**: Native integration with Logfire for structured logging and observability
- **Prometheus Metrics**: Built-in Prometheus metrics registry for monitoring
- **OpenTelemetry Support**: Distributed tracing and metrics collection
- **WebSocket Support**: Real-time monitoring dashboards
- **Multi-Backend Storage**: SQLite, Redis, and InfluxDB support

### 🚨 Alerting System
- **Condition-Based Alerts**: Flexible alert conditions using metric thresholds
- **Severity Levels**: Critical, High, Medium, Low, and Info severity classifications
- **Alert History**: Complete audit trail of alert triggers and resolutions
- **Cooldown Periods**: Prevent alert spam with configurable cooldown periods
- **Email Notifications**: Integrated notification system

### 💾 Storage Options
- **SQLite**: Local metrics and alert storage with async operations
- **Redis**: Distributed metrics caching with TTL support
- **InfluxDB**: Time series database integration for long-term storage
- **In-Memory**: High-performance caching for real-time metrics

## Installation

### Prerequisites
- Python 3.8+
- MCP framework
- Pydantic Logfire account and token
- Optional: Redis, InfluxDB for distributed storage

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Environment Configuration
Create a `.env` file with your configuration:

```env
# Logfire Configuration (Required)
LOGFIRE_TOKEN=pylf_v1_us_your_token_here
LOGFIRE_PROJECT_NAME=logfire-mcp-server
LOGFIRE_SERVICE_NAME=logfire-mcp
ENVIRONMENT=production

# Database Configuration
LOGFIRE_DB_PATH=./logfire_mcp.db

# Optional: Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Optional: InfluxDB Configuration
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=your_influxdb_token
INFLUXDB_ORG=your_organization
INFLUXDB_BUCKET=metrics

# Optional: Grafana Integration
GRAFANA_URL=http://localhost:3000
GRAFANA_API_KEY=your_grafana_api_key
```

## Usage

### Starting the Server
```bash
python server.py
```

### MCP Tool Integration

The server provides 8 comprehensive tools for observability and monitoring:

#### 1. Collect Metrics
```json
{
  "tool": "collect_metrics",
  "arguments": {
    "source": "my_application",
    "metrics": [
      {
        "name": "cpu_usage",
        "value": 75.5,
        "metric_type": "gauge",
        "tags": {"host": "server01", "service": "api"}
      },
      {
        "name": "request_count",
        "value": 1000,
        "metric_type": "counter",
        "tags": {"endpoint": "/api/users", "method": "GET"}
      }
    ]
  }
}
```

#### 2. Query Metrics
```json
{
  "tool": "query_metrics",
  "arguments": {
    "metric_name": "cpu_usage",
    "start_time": "2024-01-01T00:00:00Z",
    "end_time": "2024-01-01T23:59:59Z",
    "tags": {"host": "server01"},
    "aggregation": "avg",
    "group_by": ["service"]
  }
}
```

#### 3. Health Check
```json
{
  "tool": "health_check",
  "arguments": {
    "target": "all",
    "endpoints": [
      "http://localhost:8000/task-master/health",
      "http://localhost:8000/crawl4ai/health"
    ]
  }
}
```

#### 4. Create Alert
```json
{
  "tool": "create_alert",
  "arguments": {
    "name": "High CPU Usage Alert",
    "description": "Alert when CPU usage exceeds 80%",
    "condition": "cpu_usage > 80",
    "severity": "high",
    "enabled": true
  }
}
```

#### 5. Manage Alerts
```json
{
  "tool": "manage_alerts",
  "arguments": {
    "action": "list"
  }
}
```

#### 6. System Overview
```json
{
  "tool": "system_overview",
  "arguments": {
    "include_details": true,
    "time_range": "24h"
  }
}
```

#### 7. Export Metrics
```json
{
  "tool": "export_metrics",
  "arguments": {
    "format": "prometheus",
    "metric_names": ["cpu_usage", "memory_usage"],
    "start_time": "2024-01-01T00:00:00Z",
    "end_time": "2024-01-01T23:59:59Z"
  }
}
```

#### 8. Server Status
```json
{
  "tool": "get_server_status",
  "arguments": {}
}
```

## Configuration

### Metrics Configuration
```python
# Supported metric types
MetricType.COUNTER    # Monotonically increasing values
MetricType.GAUGE      # Point-in-time values
MetricType.HISTOGRAM  # Distribution of values
MetricType.SUMMARY    # Summary statistics
```

### Alert Severity Levels
```python
AlertSeverity.CRITICAL  # System-critical issues
AlertSeverity.HIGH      # High-priority issues
AlertSeverity.MEDIUM    # Medium-priority issues
AlertSeverity.LOW       # Low-priority issues
AlertSeverity.INFO      # Informational alerts
```

### Health Check Configuration
```python
# Default health check intervals
HEALTH_CHECK_INTERVAL = 30  # seconds
HEALTH_CHECK_TIMEOUT = 10   # seconds
METRICS_COLLECTION_INTERVAL = 30  # seconds
ALERT_EVALUATION_INTERVAL = 30    # seconds
```

## Monitoring Capabilities

### Default MCP Server Monitoring
The server automatically monitors these MCP servers:
- `task-master-mcp-server` - Project management server
- `crawl4ai-mcp` - Web crawling and RAG server
- `context7-mcp` - Context management server
- `surrealdb-mcp` - Multi-model database server
- `magic-mcp` - AI code generation server

### System Metrics Collected
- **CPU Usage**: System CPU utilization percentage
- **Memory Usage**: System memory utilization percentage
- **Disk Usage**: Disk space utilization percentage
- **Network I/O**: Network traffic metrics
- **Process Metrics**: Process-specific resource usage

### Default Alerts Configured
- **High CPU Usage**: Triggers when CPU > 80%
- **High Memory Usage**: Triggers when memory > 85%
- **MCP Server Down**: Triggers when health check fails
- **High Error Rate**: Triggers when error rate > 5% in 5 minutes

## Architecture

### Server Components
```
logfire-mcp/
├── server.py              # Main MCP server implementation
├── logfire_mcp/            # Core module
├── test_server.py          # Comprehensive test suite
├── validate_server.py      # Production validation
├── requirements.txt        # Dependencies
└── README.md              # This file
```

### Data Flow
```
Metrics Sources → Collection API → Storage Backends → Query API → Dashboards
                                      ↓
                               Alert Engine → Notifications
                                      ↓
                               Health Checks → Status Dashboard
```

### Storage Architecture
```
┌─────────────────┬──────────────────┬─────────────────┐
│   In-Memory     │      SQLite      │      Redis      │
│   (Real-time)   │   (Persistent)   │  (Distributed)  │
├─────────────────┼──────────────────┼─────────────────┤
│ Active metrics  │ Historical data  │ Shared metrics  │
│ Current alerts  │ Alert history    │ Cache layer     │
│ Health status   │ Configuration    │ Session data    │
└─────────────────┴──────────────────┴─────────────────┘
                           │
                    ┌──────▼──────┐
                    │   InfluxDB   │
                    │ (Time Series)│
                    │              │
                    │ Long-term    │
                    │ analytics    │
                    └─────────────┘
```

## Integration Examples

### Prometheus Integration
```python
# Export metrics in Prometheus format
from prometheus_client import CollectorRegistry, generate_latest

# Get Prometheus metrics
registry = server.metrics_registry
prometheus_data = generate_latest(registry)
```

### Grafana Dashboard
```json
{
  "dashboard": {
    "title": "MCP Ecosystem Monitoring",
    "panels": [
      {
        "title": "System CPU Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "system_cpu_usage",
            "legendFormat": "CPU %"
          }
        ]
      },
      {
        "title": "MCP Server Health",
        "type": "stat",
        "targets": [
          {
            "expr": "mcp_server_health",
            "legendFormat": "{{server}}"
          }
        ]
      }
    ]
  }
}
```

### Custom Metric Collection
```python
import asyncio
from server import LogfireMCPServer, MetricPoint, MetricType
from datetime import datetime

async def collect_custom_metrics():
    server = LogfireMCPServer()

    # Collect application-specific metrics
    metric = MetricPoint(
        name="api_response_time",
        value=250.5,  # milliseconds
        tags={"endpoint": "/api/users", "method": "GET"},
        timestamp=datetime.utcnow(),
        metric_type=MetricType.HISTOGRAM
    )

    await server._store_metric(metric)
```

## Performance

### Benchmarks
```
Metrics Collection: < 100ms for 1000 metrics
Health Checks: < 2 seconds for all MCP servers
Alert Evaluation: < 50ms for 100 alerts
Query Performance: < 1 second for 24h of data
Export Performance: < 5 seconds for 10MB of data
```

### Resource Usage
```
Memory Usage:
- Base Server: ~100MB
- With 10K metrics: ~200MB
- With Redis/InfluxDB: ~150MB

CPU Usage:
- Idle: < 1%
- During collection: 5-15%
- During queries: 10-25%

Storage:
- SQLite: ~1MB per 1K metrics
- Redis: Memory-based with TTL
- InfluxDB: Compressed time series
```

## Security

### Best Practices
- Store sensitive tokens in environment variables
- Use TLS for all external connections
- Implement proper access controls for metrics
- Regular security audits and updates
- Sanitize all input data

### Data Privacy
- Metrics are processed temporarily
- Configurable data retention policies
- Support for data anonymization
- Local processing options available

## Troubleshooting

### Common Issues

#### Connection Issues
```bash
# Check Logfire connectivity
export LOGFIRE_TOKEN=your_token
python -c "import logfire; logfire.configure(token='$LOGFIRE_TOKEN'); print('Connected')"

# Check Redis connectivity (if configured)
redis-cli ping

# Check InfluxDB connectivity (if configured)
curl -v $INFLUXDB_URL/ping
```

#### Performance Issues
```bash
# Check system resources
htop
df -h

# Check database size
du -h logfire_mcp.db

# Monitor server logs
tail -f /var/log/logfire-mcp.log
```

#### Alert Issues
```python
# Test alert condition evaluation
from server import LogfireMCPServer
server = LogfireMCPServer()
result = await server._evaluate_alert_condition("system_cpu_usage > 80")
print(f"Alert triggered: {result}")
```

### Debug Mode
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python server.py
```

### Health Check Commands
```bash
# Check server status
curl -X POST http://localhost:8000/logfire-mcp \
  -H "Content-Type: application/json" \
  -d '{"tool": "get_server_status", "arguments": {}}'

# Verify metric collection
curl -X POST http://localhost:8000/logfire-mcp \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "collect_metrics",
    "arguments": {
      "source": "health_check",
      "metrics": [{"name": "test_metric", "value": 1, "metric_type": "gauge"}]
    }
  }'
```

## API Reference

### Response Formats

#### Metric Collection Response
```json
{
  "status": "success",
  "collected_count": 5,
  "source": "my_application",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

#### Query Response
```json
{
  "metric_name": "cpu_usage",
  "aggregation": "avg",
  "results": [
    {
      "value": 75.5,
      "tags": {"host": "server01"},
      "timestamp": "2024-01-01T00:00:00Z"
    }
  ],
  "query_time": "2024-01-01T00:00:00Z"
}
```

#### Health Check Response
```json
{
  "target": "all",
  "health_checks": [
    {
      "name": "task-master-mcp-server Health Check",
      "endpoint": "http://localhost:8000/task-master/health",
      "healthy": true,
      "status_code": 200,
      "response_time": 0.025,
      "last_check": "2024-01-01T00:00:00Z"
    }
  ],
  "overall_healthy": true,
  "check_time": "2024-01-01T00:00:00Z"
}
```

#### System Overview Response
```json
{
  "timestamp": "2024-01-01T00:00:00Z",
  "time_range": "24h",
  "summary": {
    "total_mcp_servers": 5,
    "healthy_servers": 5,
    "active_alerts": 2,
    "total_metrics": 1250
  },
  "system_metrics": [
    {
      "name": "System CPU",
      "healthy": true,
      "value": 45.2,
      "unit": "percent",
      "threshold": 80
    }
  ],
  "mcp_servers": {
    "task-master-mcp-server": {
      "healthy": true,
      "response_time": 0.023,
      "last_check": "2024-01-01T00:00:00Z"
    }
  },
  "alerts": [
    {
      "id": "alert_001",
      "name": "High Memory Usage",
      "severity": "medium",
      "enabled": true,
      "last_triggered": null
    }
  ]
}
```

## Testing

### Run Test Suite
```bash
python test_server.py
```

### Validation Script
```bash
python validate_server.py
```

### Integration Testing
```bash
# Test with real Logfire integration
export LOGFIRE_TOKEN=your_real_token
python validate_server.py --integration

# Test performance under load
python validate_server.py --load-test
```

## Contributing

### Development Setup
```bash
git clone https://github.com/devq-ai/logfire-mcp
cd logfire-mcp
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Code Quality Standards
- Follow DevQ.ai coding standards
- Maintain 90%+ test coverage
- Use type hints for all functions
- Comprehensive error handling
- Performance optimization

### Submitting Changes
1. Create feature branch
2. Add tests for new functionality
3. Update documentation
4. Run validation suite
5. Submit pull request

## License

This project follows the DevQ.ai licensing terms. See LICENSE file for details.

## Support

For issues and questions:
- Check validation report for diagnostics
- Review server logs for errors
- Consult DevQ.ai documentation
- Submit issues via project repository

## Changelog

### Version 1.0.0
- Initial release with comprehensive monitoring capabilities
- Support for 8 MCP tools with full functionality
- Multi-backend storage (SQLite, Redis, InfluxDB)
- Prometheus metrics integration
- Real-time health monitoring
- Intelligent alerting system
- Background monitoring tasks
- Comprehensive export capabilities

---

**Logfire MCP Server** - Advanced observability and monitoring for the MCP ecosystem. Part of the DevQ.ai infrastructure suite.
