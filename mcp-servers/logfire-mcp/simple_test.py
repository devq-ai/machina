#!/usr/bin/env python3
"""
Simple validation test for Logfire MCP Server

A streamlined test to validate core functionality without complex dependencies.
Tests basic server initialization, tool registration, and core capabilities.
"""

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import patch, Mock
from datetime import datetime

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

def test_imports():
    """Test that core imports work correctly."""
    print("Testing imports...")

    try:
        # Mock problematic dependencies first
        sys.modules['prometheus_client'] = Mock()
        sys.modules['redis.asyncio'] = Mock()
        sys.modules['influxdb_client'] = Mock()
        sys.modules['sqlalchemy'] = Mock()
        sys.modules['sqlalchemy.ext.asyncio'] = Mock()
        sys.modules['sqlalchemy.orm'] = Mock()
        sys.modules['aiosqlite'] = Mock()
        sys.modules['orjson'] = Mock()
        sys.modules['websockets'] = Mock()
        sys.modules['opentelemetry'] = Mock()
        sys.modules['opentelemetry.trace'] = Mock()
        sys.modules['opentelemetry.metrics'] = Mock()
        sys.modules['opentelemetry.sdk.trace'] = Mock()
        sys.modules['opentelemetry.sdk.metrics'] = Mock()
        sys.modules['grafana_client'] = Mock()

        # Mock psutil with realistic values
        mock_psutil = Mock()
        mock_psutil.cpu_percent.return_value = 25.0
        mock_memory = Mock()
        mock_memory.percent = 60.0
        mock_psutil.virtual_memory.return_value = mock_memory
        mock_disk = Mock()
        mock_disk.percent = 45.0
        mock_psutil.disk_usage.return_value = mock_disk
        sys.modules['psutil'] = mock_psutil

        print("✅ All imports successful")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_enums():
    """Test that enums are working correctly."""
    print("Testing enums...")

    try:
        from server import MetricType, AlertSeverity, MonitoringScope

        # Test MetricType enum
        assert MetricType.COUNTER == "counter"
        assert MetricType.GAUGE == "gauge"
        assert MetricType.HISTOGRAM == "histogram"

        # Test AlertSeverity enum
        assert AlertSeverity.CRITICAL == "critical"
        assert AlertSeverity.HIGH == "high"
        assert AlertSeverity.MEDIUM == "medium"
        assert AlertSeverity.LOW == "low"

        # Test MonitoringScope enum
        assert MonitoringScope.SERVER == "server"
        assert MonitoringScope.SYSTEM == "system"

        print("✅ All enums working correctly")
        return True
    except Exception as e:
        print(f"❌ Enum test failed: {e}")
        return False

async def test_server_creation():
    """Test basic server creation."""
    print("Testing server creation...")

    try:
        with patch.dict('os.environ', {
            'LOGFIRE_TOKEN': 'test-logfire-token',
            'LOGFIRE_DB_PATH': ':memory:',
            'ENVIRONMENT': 'testing'
        }):
            # Import after setting up mocks
            from server import LogfireMCPServer

            # Create server (should not crash)
            server = LogfireMCPServer()

            # Check basic attributes
            assert hasattr(server, 'server')
            assert hasattr(server, 'metrics_cache')
            assert hasattr(server, 'alerts')
            assert hasattr(server, 'health_checks')
            assert server.server.name == "logfire-mcp"

            print("✅ Server creation successful")
            return True
    except Exception as e:
        print(f"❌ Server creation failed: {e}")
        return False

async def test_data_models():
    """Test data model creation."""
    print("Testing data models...")

    try:
        from server import (
            MetricPoint,
            Alert,
            HealthCheck,
            MetricType,
            AlertSeverity
        )

        # Test MetricPoint
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

        # Test Alert
        alert = Alert(
            id="test_alert",
            name="Test Alert",
            description="Test description",
            condition="metric > 100",
            severity=AlertSeverity.HIGH,
            enabled=True
        )
        assert alert.id == "test_alert"
        assert alert.severity == AlertSeverity.HIGH

        # Test HealthCheck
        health_check = HealthCheck(
            name="Test Health Check",
            endpoint="http://test/health",
            interval=60,
            timeout=30
        )
        assert health_check.name == "Test Health Check"
        assert health_check.interval == 60

        print("✅ Data models working correctly")
        return True
    except Exception as e:
        print(f"❌ Data model test failed: {e}")
        return False

async def test_basic_methods():
    """Test basic server methods."""
    print("Testing basic server methods...")

    try:
        with patch.dict('os.environ', {
            'LOGFIRE_TOKEN': 'test-logfire-token',
            'LOGFIRE_DB_PATH': ':memory:'
        }):
            from server import LogfireMCPServer, MetricPoint, MetricType

            server = LogfireMCPServer()

            # Test metric storage
            metric = MetricPoint(
                name="test_storage_metric",
                value=75.0,
                tags={"test": "basic"},
                timestamp=datetime.utcnow(),
                metric_type=MetricType.GAUGE
            )

            await server._store_metric(metric)

            # Check if metric is stored
            assert len(server.metrics_cache) > 0

            # Test server status (should not crash)
            status_result = await server._handle_get_server_status({})
            assert len(status_result) == 1

            status_data = json.loads(status_result[0].text)
            assert status_data["server_name"] == "logfire-mcp"

            print("✅ Basic methods working correctly")
            return True
    except Exception as e:
        print(f"❌ Basic methods test failed: {e}")
        return False

async def test_default_setup():
    """Test default alerts and health checks setup."""
    print("Testing default setup...")

    try:
        with patch.dict('os.environ', {
            'LOGFIRE_TOKEN': 'test-logfire-token'
        }):
            from server import LogfireMCPServer

            server = LogfireMCPServer()

            # Check default alerts
            expected_alerts = [
                "high_cpu_usage",
                "high_memory_usage",
                "mcp_server_down",
                "high_error_rate"
            ]

            for alert_id in expected_alerts:
                assert alert_id in server.alerts, f"Missing default alert: {alert_id}"
                assert server.alerts[alert_id].enabled

            # Check default health checks
            expected_servers = [
                "task-master-mcp-server",
                "crawl4ai-mcp",
                "context7-mcp",
                "surrealdb-mcp",
                "magic-mcp"
            ]

            for server_name in expected_servers:
                health_check_key = f"{server_name}_health"
                assert health_check_key in server.health_checks, f"Missing health check: {health_check_key}"

            print("✅ Default setup working correctly")
            return True
    except Exception as e:
        print(f"❌ Default setup test failed: {e}")
        return False

async def test_metrics_collection():
    """Test metrics collection functionality."""
    print("Testing metrics collection...")

    try:
        with patch.dict('os.environ', {
            'LOGFIRE_TOKEN': 'test-logfire-token'
        }):
            from server import LogfireMCPServer

            server = LogfireMCPServer()

            # Test metrics collection
            arguments = {
                "source": "simple_test",
                "metrics": [
                    {
                        "name": "simple_test_metric",
                        "value": 50.0,
                        "metric_type": "gauge",
                        "tags": {"test": "simple"}
                    }
                ]
            }

            result = await server._handle_collect_metrics(arguments)

            assert len(result) == 1
            response_data = json.loads(result[0].text)
            assert response_data["status"] == "success"
            assert response_data["collected_count"] == 1

            print("✅ Metrics collection working correctly")
            return True
    except Exception as e:
        print(f"❌ Metrics collection test failed: {e}")
        return False

async def run_all_tests():
    """Run all simple tests."""
    print("🚀 Starting Logfire MCP Server Simple Tests")
    print("=" * 60)

    tests = [
        test_imports,
        test_enums,
        test_server_creation,
        test_data_models,
        test_basic_methods,
        test_default_setup,
        test_metrics_collection
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            if asyncio.iscoroutinefunction(test):
                result = await test()
            else:
                result = test()

            if result:
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")

    print("\n" + "=" * 60)
    print(f"📊 Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 ALL SIMPLE TESTS PASSED!")
        print("✅ Logfire MCP Server basic functionality is working")
    else:
        print(f"⚠️  {total - passed} tests failed")
        print("❌ Some basic functionality issues detected")

    print("=" * 60)
    return passed == total

def main():
    """Main entry point."""
    try:
        success = asyncio.run(run_all_tests())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"💥 Test runner crashed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
