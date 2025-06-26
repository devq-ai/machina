#!/usr/bin/env python3
"""
Comprehensive test suite for Logfire MCP Server

Tests all observability, monitoring, and alerting capabilities
following DevQ.ai testing standards with async operations and mock integrations.
"""

import pytest
import asyncio
import json
import sys
import time
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, List
from datetime import datetime, timedelta

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

# Import server components
try:
    from server import (
        LogfireMCPServer,
        MetricType,
        AlertSeverity,
        MonitoringScope,
        MetricPoint,
        Alert,
        HealthCheck
    )
    print("✅ Successfully imported Logfire MCP Server components")
except ImportError as e:
    print(f"❌ Import error: {e}")
    pytest.skip("Cannot import server components", allow_module_level=True)

class TestLogfireMCPServer:
    """Test suite for Logfire MCP Server."""

    @pytest.fixture
    async def server(self):
        """Create a test server instance."""
        with patch.dict('os.environ', {
            'LOGFIRE_TOKEN': 'test-logfire-token',
            'LOGFIRE_DB_PATH': ':memory:',
            'REDIS_URL': 'redis://localhost:6379/0',
            'INFLUXDB_URL': 'http://localhost:8086',
            'INFLUXDB_TOKEN': 'test-token',
            'INFLUXDB_ORG': 'test-org'
        }):
            with patch('psutil.cpu_percent', return_value=25.0), \
                 patch('psutil.virtual_memory') as mock_memory, \
                 patch('psutil.disk_usage') as mock_disk:

                mock_memory.return_value.percent = 60.0
                mock_disk.return_value.percent = 45.0

                server = LogfireMCPServer()
                yield server

    @pytest.fixture
    def sample_metric(self):
        """Sample metric for testing."""
        return MetricPoint(
            name="test_metric",
            value=42.0,
            tags={"service": "test", "env": "development"},
            timestamp=datetime.utcnow(),
            metric_type=MetricType.GAUGE
        )

    @pytest.fixture
    def sample_alert(self):
        """Sample alert for testing."""
        return Alert(
            id="test_alert_001",
            name="Test Alert",
            description="Test alert for unit testing",
            condition="test_metric > 40",
            severity=AlertSeverity.MEDIUM,
            enabled=True
        )

    @pytest.mark.asyncio
    async def test_server_initialization(self, server):
        """Test server initialization."""
        assert server.server.name == "logfire-mcp"
        assert hasattr(server, 'metrics_registry')
        assert hasattr(server, 'metrics_cache')
        assert hasattr(server, 'alerts')
        assert hasattr(server, 'health_checks')
        assert hasattr(server, 'prom_metrics')

    @pytest.mark.asyncio
    async def test_prometheus_metrics_setup(self, server):
        """Test Prometheus metrics setup."""
        expected_metrics = [
            'mcp_requests_total',
            'mcp_request_duration',
            'mcp_server_health',
            'system_cpu_usage',
            'system_memory_usage',
            'system_disk_usage'
        ]

        for metric_name in expected_metrics:
            assert metric_name in server.prom_metrics

    @pytest.mark.asyncio
    async def test_collect_metrics(self, server):
        """Test metrics collection functionality."""
        arguments = {
            "source": "test_system",
            "metrics": [
                {
                    "name": "cpu_usage",
                    "value": 75.5,
                    "metric_type": "gauge",
                    "tags": {"host": "test-host"}
                },
                {
                    "name": "request_count",
                    "value": 1000,
                    "metric_type": "counter",
                    "tags": {"service": "api"}
                }
            ]
        }

        result = await server._handle_collect_metrics(arguments)

        assert len(result) == 1
        assert result[0].type == "text"

        response_data = json.loads(result[0].text)
        assert response_data["status"] == "success"
        assert response_data["collected_count"] == 2
        assert response_data["source"] == "test_system"

    @pytest.mark.asyncio
    async def test_metric_storage(self, server, sample_metric):
        """Test metric storage functionality."""
        # Test storing metric
        await server._store_metric(sample_metric)

        # Check if metric is in cache
        cache_key = f"{sample_metric.name}:{hash(frozenset(sample_metric.tags.items()))}"
        assert cache_key in server.metrics_cache
        assert server.metrics_cache[cache_key].value == 42.0

    @pytest.mark.asyncio
    async def test_query_metrics(self, server):
        """Test metrics querying functionality."""
        # First store some test metrics
        test_metrics = [
            MetricPoint("test_query_metric", 10.0, {"env": "test"}, datetime.utcnow(), MetricType.GAUGE),
            MetricPoint("test_query_metric", 20.0, {"env": "test"}, datetime.utcnow(), MetricType.GAUGE),
            MetricPoint("test_query_metric", 30.0, {"env": "prod"}, datetime.utcnow(), MetricType.GAUGE)
        ]

        for metric in test_metrics:
            await server._store_metric(metric)

        arguments = {
            "metric_name": "test_query_metric",
            "tags": {"env": "test"},
            "aggregation": "avg"
        }

        result = await server._handle_query_metrics(arguments)

        assert len(result) == 1
        response_data = json.loads(result[0].text)
        assert response_data["metric_name"] == "test_query_metric"
        assert response_data["aggregation"] == "avg"

    @pytest.mark.asyncio
    async def test_health_check_system(self, server):
        """Test system health check functionality."""
        with patch('psutil.cpu_percent', return_value=25.0), \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk:

            mock_memory.return_value.percent = 60.0
            mock_disk.return_value.percent = 45.0

            results = await server._check_system_health()

            assert len(results) == 3

            # Check CPU health
            cpu_result = next(r for r in results if r["name"] == "System CPU")
            assert cpu_result["healthy"] == True
            assert cpu_result["value"] == 25.0

            # Check Memory health
            memory_result = next(r for r in results if r["name"] == "System Memory")
            assert memory_result["healthy"] == True
            assert memory_result["value"] == 60.0

    @pytest.mark.asyncio
    async def test_health_check_endpoints(self, server):
        """Test endpoint health check functionality."""
        endpoints = ["http://test-endpoint/health"]

        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

            results = await server._check_specific_endpoints(endpoints)

            assert len(results) == 1
            assert results[0]["endpoint"] == "http://test-endpoint/health"
            assert results[0]["healthy"] == True
            assert results[0]["status_code"] == 200

    @pytest.mark.asyncio
    async def test_create_alert(self, server):
        """Test alert creation functionality."""
        arguments = {
            "name": "Test High CPU Alert",
            "description": "Alert when CPU usage is high",
            "condition": "system_cpu_usage > 80",
            "severity": "high",
            "enabled": True
        }

        result = await server._handle_create_alert(arguments)

        assert len(result) == 1
        response_data = json.loads(result[0].text)
        assert response_data["status"] == "success"
        assert "alert_id" in response_data
        assert response_data["alert"]["name"] == "Test High CPU Alert"

        # Check if alert is stored
        alert_id = response_data["alert_id"]
        assert alert_id in server.alerts

    @pytest.mark.asyncio
    async def test_manage_alerts_list(self, server, sample_alert):
        """Test alert management - list functionality."""
        # Add sample alert
        server.alerts[sample_alert.id] = sample_alert

        arguments = {"action": "list"}

        result = await server._handle_manage_alerts(arguments)

        assert len(result) == 1
        response_data = json.loads(result[0].text)
        assert "alerts" in response_data
        assert response_data["total_count"] >= 1

        # Find our test alert
        test_alert = next((a for a in response_data["alerts"] if a["id"] == sample_alert.id), None)
        assert test_alert is not None
        assert test_alert["name"] == "Test Alert"

    @pytest.mark.asyncio
    async def test_manage_alerts_enable_disable(self, server, sample_alert):
        """Test alert management - enable/disable functionality."""
        # Add sample alert
        server.alerts[sample_alert.id] = sample_alert

        # Test disable
        arguments = {"action": "disable", "alert_id": sample_alert.id}
        result = await server._handle_manage_alerts(arguments)

        response_data = json.loads(result[0].text)
        assert response_data["status"] == "success"
        assert not server.alerts[sample_alert.id].enabled

        # Test enable
        arguments = {"action": "enable", "alert_id": sample_alert.id}
        result = await server._handle_manage_alerts(arguments)

        response_data = json.loads(result[0].text)
        assert response_data["status"] == "success"
        assert server.alerts[sample_alert.id].enabled

    @pytest.mark.asyncio
    async def test_system_overview(self, server):
        """Test system overview functionality."""
        arguments = {
            "include_details": True,
            "time_range": "1h"
        }

        with patch('psutil.cpu_percent', return_value=45.0), \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk:

            mock_memory.return_value.percent = 70.0
            mock_disk.return_value.percent = 55.0

            result = await server._handle_system_overview(arguments)

            assert len(result) == 1
            response_data = json.loads(result[0].text)

            assert "summary" in response_data
            assert "system_metrics" in response_data
            assert "mcp_servers" in response_data
            assert response_data["time_range"] == "1h"

    @pytest.mark.asyncio
    async def test_export_metrics_json(self, server, sample_metric):
        """Test metrics export in JSON format."""
        # Store sample metric
        await server._store_metric(sample_metric)

        arguments = {
            "format": "json",
            "metric_names": ["test_metric"]
        }

        result = await server._handle_export_metrics(arguments)

        assert len(result) == 1

        # Should be valid JSON
        try:
            exported_data = json.loads(result[0].text)
            assert isinstance(exported_data, list)
        except json.JSONDecodeError:
            pytest.fail("Exported data is not valid JSON")

    @pytest.mark.asyncio
    async def test_export_metrics_prometheus(self, server, sample_metric):
        """Test metrics export in Prometheus format."""
        # Store sample metric
        await server._store_metric(sample_metric)

        arguments = {
            "format": "prometheus",
            "metric_names": ["test_metric"]
        }

        result = await server._handle_export_metrics(arguments)

        assert len(result) == 1
        exported_data = result[0].text

        # Should contain Prometheus-formatted metrics
        assert "test_metric" in exported_data
        assert "42" in exported_data  # The metric value

    @pytest.mark.asyncio
    async def test_server_status(self, server):
        """Test server status endpoint."""
        result = await server._handle_get_server_status({})

        assert len(result) == 1
        status_data = json.loads(result[0].text)

        required_fields = ["server_name", "version", "status", "components", "metrics", "system_info"]
        for field in required_fields:
            assert field in status_data

        assert status_data["server_name"] == "logfire-mcp"
        assert status_data["status"] == "running"

    @pytest.mark.asyncio
    async def test_alert_condition_evaluation(self, server):
        """Test alert condition evaluation."""
        with patch('psutil.cpu_percent', return_value=85.0):
            # Test CPU condition
            result = await server._evaluate_alert_condition("system_cpu_usage > 80")
            assert result == True

        with patch('psutil.cpu_percent', return_value=70.0):
            result = await server._evaluate_alert_condition("system_cpu_usage > 80")
            assert result == False

        with patch('psutil.virtual_memory') as mock_memory:
            mock_memory.return_value.percent = 90.0
            result = await server._evaluate_alert_condition("system_memory_usage > 85")
            assert result == True

    @pytest.mark.asyncio
    async def test_error_handling(self, server):
        """Test error handling in tool calls."""
        # Test with invalid arguments
        arguments = {
            "source": "invalid_source",
            "metrics": [
                {
                    "name": "test_metric",
                    "value": "invalid_value",  # Should be numeric
                    "metric_type": "gauge"
                }
            ]
        }

        result = await server._handle_collect_metrics(arguments)

        assert len(result) == 1
        assert "Error" in result[0].text or "error" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_metric_aggregation(self, server):
        """Test metric aggregation functionality."""
        # Create test metrics with different values
        test_values = [10.0, 20.0, 30.0, 40.0, 50.0]

        for value in test_values:
            metric = MetricPoint(
                "aggregation_test_metric",
                value,
                {"env": "test"},
                datetime.utcnow(),
                MetricType.GAUGE
            )
            await server._store_metric(metric)

        # Test different aggregations
        aggregations = ["avg", "sum", "min", "max", "count"]

        for agg in aggregations:
            arguments = {
                "metric_name": "aggregation_test_metric",
                "aggregation": agg
            }

            result = await server._handle_query_metrics(arguments)
            response_data = json.loads(result[0].text)

            assert response_data["aggregation"] == agg

            if agg == "avg":
                assert response_data["results"][0]["value"] == 30.0  # (10+20+30+40+50)/5
            elif agg == "sum":
                assert response_data["results"][0]["value"] == 150.0
            elif agg == "min":
                assert response_data["results"][0]["value"] == 10.0
            elif agg == "max":
                assert response_data["results"][0]["value"] == 50.0
            elif agg == "count":
                assert response_data["results"][0]["value"] == 5

    @pytest.mark.asyncio
    async def test_health_check_timeout(self, server):
        """Test health check timeout handling."""
        endpoints = ["http://slow-endpoint/health"]

        with patch('httpx.AsyncClient') as mock_client:
            # Simulate timeout
            mock_client.return_value.__aenter__.return_value.get.side_effect = asyncio.TimeoutError()

            results = await server._check_specific_endpoints(endpoints)

            assert len(results) == 1
            assert results[0]["healthy"] == False
            assert "error" in results[0]

    @pytest.mark.asyncio
    async def test_default_alerts_setup(self, server):
        """Test that default alerts are properly set up."""
        expected_default_alerts = [
            "high_cpu_usage",
            "high_memory_usage",
            "mcp_server_down",
            "high_error_rate"
        ]

        for alert_id in expected_default_alerts:
            assert alert_id in server.alerts
            assert server.alerts[alert_id].enabled

    @pytest.mark.asyncio
    async def test_default_health_checks_setup(self, server):
        """Test that default health checks are properly set up."""
        expected_servers = [
            "task-master-mcp-server",
            "crawl4ai-mcp",
            "context7-mcp",
            "surrealdb-mcp",
            "magic-mcp"
        ]

        for server_name in expected_servers:
            health_check_key = f"{server_name}_health"
            assert health_check_key in server.health_checks
            assert server.health_checks[health_check_key].interval == 30
            assert server.health_checks[health_check_key].timeout == 10

class TestMetricModels:
    """Test data models and enums."""

    def test_metric_point_creation(self):
        """Test MetricPoint creation."""
        metric = MetricPoint(
            name="test_metric",
            value=42.5,
            tags={"service": "test"},
            timestamp=datetime.utcnow(),
            metric_type=MetricType.GAUGE
        )

        assert metric.name == "test_metric"
        assert metric.value == 42.5
        assert metric.tags["service"] == "test"
        assert metric.metric_type == MetricType.GAUGE

    def test_alert_creation(self):
        """Test Alert creation."""
        alert = Alert(
            id="test_001",
            name="Test Alert",
            description="Test description",
            condition="metric > 100",
            severity=AlertSeverity.HIGH,
            enabled=True
        )

        assert alert.id == "test_001"
        assert alert.name == "Test Alert"
        assert alert.severity == AlertSeverity.HIGH
        assert alert.enabled == True
        assert alert.trigger_count == 0

    def test_health_check_creation(self):
        """Test HealthCheck creation."""
        health_check = HealthCheck(
            name="API Health Check",
            endpoint="http://api/health",
            interval=60,
            timeout=30
        )

        assert health_check.name == "API Health Check"
        assert health_check.endpoint == "http://api/health"
        assert health_check.interval == 60
        assert health_check.timeout == 30
        assert health_check.status == "unknown"

    def test_enum_values(self):
        """Test enum values."""
        assert MetricType.COUNTER == "counter"
        assert MetricType.GAUGE == "gauge"
        assert MetricType.HISTOGRAM == "histogram"

        assert AlertSeverity.CRITICAL == "critical"
        assert AlertSeverity.HIGH == "high"
        assert AlertSeverity.MEDIUM == "medium"

        assert MonitoringScope.SERVER == "server"
        assert MonitoringScope.SYSTEM == "system"

class TestIntegrationScenarios:
    """Integration test scenarios."""

    @pytest.mark.asyncio
    async def test_full_monitoring_workflow(self):
        """Test complete monitoring workflow."""
        with patch.dict('os.environ', {'LOGFIRE_TOKEN': 'test-token'}):
            server = LogfireMCPServer()

            # 1. Collect metrics
            arguments = {
                "source": "integration_test",
                "metrics": [
                    {
                        "name": "integration_metric",
                        "value": 85.0,
                        "metric_type": "gauge",
                        "tags": {"test": "integration"}
                    }
                ]
            }

            collect_result = await server._handle_collect_metrics(arguments)
            assert json.loads(collect_result[0].text)["status"] == "success"

            # 2. Query metrics
            query_args = {
                "metric_name": "integration_metric",
                "aggregation": "avg"
            }

            query_result = await server._handle_query_metrics(query_args)
            query_data = json.loads(query_result[0].text)
            assert query_data["metric_name"] == "integration_metric"

            # 3. Create alert
            alert_args = {
                "name": "Integration Test Alert",
                "condition": "integration_metric > 80",
                "severity": "medium"
            }

            alert_result = await server._handle_create_alert(alert_args)
            alert_data = json.loads(alert_result[0].text)
            assert alert_data["status"] == "success"

            # 4. Check system overview
            overview_result = await server._handle_system_overview({"include_details": True})
            overview_data = json.loads(overview_result[0].text)
            assert "summary" in overview_data
            assert "system_metrics" in overview_data

    @pytest.mark.asyncio
    async def test_error_recovery_scenarios(self):
        """Test error recovery in various scenarios."""
        with patch.dict('os.environ', {}):  # No environment variables
            server = LogfireMCPServer()

            # Should not crash, should provide fallback responses
            arguments = {
                "source": "error_test",
                "metrics": [{"name": "test", "value": 1, "metric_type": "gauge"}]
            }

            result = await server._handle_collect_metrics(arguments)

            # Should not crash and should return some response
            assert len(result) == 1
            assert result[0].type == "text"

    @pytest.mark.asyncio
    async def test_concurrent_operations(self):
        """Test concurrent operations handling."""
        with patch.dict('os.environ', {'LOGFIRE_TOKEN': 'test-token'}):
            server = LogfireMCPServer()

            async def collect_metric(metric_name, value):
                arguments = {
                    "source": "concurrent_test",
                    "metrics": [
                        {
                            "name": metric_name,
                            "value": value,
                            "metric_type": "gauge"
                        }
                    ]
                }
                return await server._handle_collect_metrics(arguments)

            # Create multiple concurrent metric collection tasks
            tasks = [
                collect_metric(f"concurrent_metric_{i}", i * 10)
                for i in range(5)
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # All tasks should complete successfully
            assert len(results) == 5
            for result in results:
                assert not isinstance(result, Exception)
                assert len(result) == 1

if __name__ == "__main__":
    # Run tests with asyncio support
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
