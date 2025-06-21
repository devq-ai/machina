"""
Comprehensive Test Suite for Redis Cache and Pub/Sub Service

This test module provides thorough testing of the Redis cache and pub/sub
functionality, implementing DevQ.ai's testing standards with fixtures,
mocking, and comprehensive coverage of all cache operations.

Test Coverage:
- Cache service initialization and connection management
- Basic cache operations (get, set, delete, exists, expire)
- Bulk operations and batch processing
- Pub/sub messaging system
- Circuit breaker pattern and error handling
- Health monitoring and statistics
- Domain-specific cache operations
- Rate limiting functionality
- Session management
- Cache warming and preloading
"""

import asyncio
import json
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch

import logfire
from redis.exceptions import ConnectionError, TimeoutError

from app.core.cache import CacheService, CacheKeyType, PubSubChannel, RedisMessage, CacheStats
from app.services.cache_service import (
    CacheUtilities,
    MCPServerCacheData,
    RateLimitConfig,
    get_cache_utilities
)
from app.core.config import Settings


@pytest.fixture
def test_settings():
    """Test settings with Redis configuration."""
    return Settings(
        REDIS_HOST="localhost",
        REDIS_PORT=6379,
        REDIS_DB=1,  # Use separate test database
        REDIS_PASSWORD=None,
        CACHE_TTL=3600,
        CACHE_PREFIX="test:machina:",
        DEBUG=True,
        ENVIRONMENT="testing"
    )


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    mock = AsyncMock()

    # Mock basic operations
    mock.ping = AsyncMock(return_value=True)
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.setex = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=1)
    mock.exists = AsyncMock(return_value=0)
    mock.expire = AsyncMock(return_value=True)
    mock.mget = AsyncMock(return_value=[])
    mock.keys = AsyncMock(return_value=[])
    mock.publish = AsyncMock(return_value=1)
    mock.ttl = AsyncMock(return_value=3600)
    mock.close = AsyncMock()

    # Mock info command
    mock.info = AsyncMock(return_value={
        "redis_version": "7.0.0",
        "uptime_in_seconds": 3600,
        "connected_clients": 5,
        "used_memory": 1024000,
        "keyspace_hits": 100,
        "keyspace_misses": 20
    })

    return mock


@pytest.fixture
def mock_connection_pool():
    """Mock Redis connection pool."""
    mock = AsyncMock()
    mock.disconnect = AsyncMock()
    return mock


@pytest_asyncio.fixture
async def cache_service(test_settings, mock_redis, mock_connection_pool):
    """Create cache service with mocked Redis."""
    service = CacheService(test_settings)

    with patch('redis.asyncio.ConnectionPool.from_url', return_value=mock_connection_pool):
        with patch('redis.asyncio.Redis', return_value=mock_redis):
            await service.initialize()
            yield service
            await service.close()


@pytest_asyncio.fixture
async def cache_utilities(cache_service):
    """Create cache utilities with initialized cache service."""
    return CacheUtilities(cache_service)


class TestCacheService:
    """Test suite for core CacheService functionality."""

    @pytest.mark.asyncio
    async def test_initialization_success(self, test_settings, mock_redis, mock_connection_pool):
        """Test successful cache service initialization."""
        service = CacheService(test_settings)

        with patch('redis.asyncio.ConnectionPool.from_url', return_value=mock_connection_pool):
            with patch('redis.asyncio.Redis', return_value=mock_redis):
                await service.initialize()

                assert service._stats.connection_status == "connected"
                assert not service._circuit_breaker_open
                mock_redis.ping.assert_called_once()

                await service.close()

    @pytest.mark.asyncio
    async def test_initialization_failure(self, test_settings, mock_redis, mock_connection_pool):
        """Test cache service initialization failure handling."""
        mock_redis.ping.side_effect = ConnectionError("Connection failed")
        service = CacheService(test_settings)

        with patch('redis.asyncio.ConnectionPool.from_url', return_value=mock_connection_pool):
            with patch('redis.asyncio.Redis', return_value=mock_redis):
                with pytest.raises(ConnectionError):
                    await service.initialize()

                assert service._stats.connection_status == "failed"
                assert service._circuit_breaker_open

    @pytest.mark.asyncio
    async def test_circuit_breaker_functionality(self, cache_service, mock_redis):
        """Test circuit breaker pattern with Redis failures."""
        # Simulate failures to trigger circuit breaker
        mock_redis.get.side_effect = ConnectionError("Connection lost")

        # First few failures should be recorded
        for _ in range(3):
            with pytest.raises(ConnectionError):
                await cache_service.get(CacheKeyType.MCP_SERVER, "test")

        # Circuit breaker should now be open
        assert cache_service._circuit_breaker_open

        # Further operations should be blocked
        result = await cache_service.get(CacheKeyType.MCP_SERVER, "test")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_key_building(self, cache_service):
        """Test cache key building with different parameters."""
        # Basic key
        key = cache_service._build_cache_key(CacheKeyType.MCP_SERVER, "test-server")
        assert key == "test:machina:mcp:server:test-server"

        # Key with suffix
        key_with_suffix = cache_service._build_cache_key(
            CacheKeyType.MCP_TOOL, "test-tool", "config"
        )
        assert key_with_suffix == "test:machina:mcp:tool:test-tool:config"

    @pytest.mark.asyncio
    async def test_get_operation_success(self, cache_service, mock_redis):
        """Test successful cache get operation."""
        test_data = {"key": "value", "number": 42}
        mock_redis.get.return_value = json.dumps(test_data)

        result = await cache_service.get(CacheKeyType.MCP_SERVER, "test-server")

        assert result == test_data
        assert cache_service._stats.cache_hits == 1
        assert cache_service._stats.cache_misses == 0

    @pytest.mark.asyncio
    async def test_get_operation_miss(self, cache_service, mock_redis):
        """Test cache miss scenario."""
        mock_redis.get.return_value = None

        result = await cache_service.get(CacheKeyType.MCP_SERVER, "nonexistent")

        assert result is None
        assert cache_service._stats.cache_hits == 0
        assert cache_service._stats.cache_misses == 1

    @pytest.mark.asyncio
    async def test_set_operation_success(self, cache_service, mock_redis):
        """Test successful cache set operation."""
        test_data = {"key": "value", "timestamp": datetime.utcnow().isoformat()}
        mock_redis.setex.return_value = True

        result = await cache_service.set(
            CacheKeyType.MCP_SERVER,
            "test-server",
            test_data,
            ttl=1800
        )

        assert result is True
        mock_redis.setex.assert_called_once()

        # Verify the call arguments
        args = mock_redis.setex.call_args
        assert args[0][1] == 1800  # TTL

        # Verify serialized data
        serialized_data = json.loads(args[0][2])
        assert serialized_data == test_data

    @pytest.mark.asyncio
    async def test_delete_operation(self, cache_service, mock_redis):
        """Test cache delete operation."""
        mock_redis.delete.return_value = 1

        result = await cache_service.delete(CacheKeyType.MCP_SERVER, "test-server")

        assert result is True
        mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_exists_operation(self, cache_service, mock_redis):
        """Test cache exists operation."""
        mock_redis.exists.return_value = 1

        result = await cache_service.exists(CacheKeyType.MCP_SERVER, "test-server")

        assert result is True
        mock_redis.exists.assert_called_once()

    @pytest.mark.asyncio
    async def test_expire_operation(self, cache_service, mock_redis):
        """Test cache expire operation."""
        mock_redis.expire.return_value = True

        result = await cache_service.expire(CacheKeyType.MCP_SERVER, "test-server", 1800)

        assert result is True
        mock_redis.expire.assert_called_once_with(
            "test:machina:mcp:server:test-server", 1800
        )

    @pytest.mark.asyncio
    async def test_get_multiple_operation(self, cache_service, mock_redis):
        """Test bulk get operation."""
        test_data = [
            json.dumps({"server": "server1"}),
            json.dumps({"server": "server2"}),
            None  # Cache miss
        ]
        mock_redis.mget.return_value = test_data

        keys = [
            (CacheKeyType.MCP_SERVER, "server1", None),
            (CacheKeyType.MCP_SERVER, "server2", None),
            (CacheKeyType.MCP_SERVER, "server3", None)
        ]

        result = await cache_service.get_multiple(keys)

        assert len(result) == 2  # Only hits returned
        assert cache_service._stats.cache_hits == 2
        assert cache_service._stats.cache_misses == 1

    @pytest.mark.asyncio
    async def test_publish_message(self, cache_service, mock_redis):
        """Test pub/sub message publishing."""
        mock_redis.publish.return_value = 3  # 3 subscribers

        result = await cache_service.publish(
            PubSubChannel.MCP_SERVER_UPDATES,
            "status_change",
            {"server_id": "test-server", "status": "healthy"},
            correlation_id="test-correlation"
        )

        assert result == 3
        mock_redis.publish.assert_called_once()

        # Verify message structure
        args = mock_redis.publish.call_args
        message_data = json.loads(args[0][1])
        assert message_data["message_type"] == "status_change"
        assert message_data["correlation_id"] == "test-correlation"

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, cache_service, mock_redis):
        """Test health check with healthy Redis."""
        health = await cache_service.health_check()

        assert health["status"] == "healthy"
        assert health["connection"] is True
        assert "latency_ms" in health
        assert "redis_info" in health

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, cache_service, mock_redis):
        """Test health check with unhealthy Redis."""
        mock_redis.ping.side_effect = ConnectionError("Connection failed")

        health = await cache_service.health_check()

        assert health["status"] == "unhealthy"
        assert health["connection"] is False
        assert "error" in health

    @pytest.mark.asyncio
    async def test_statistics_tracking(self, cache_service, mock_redis):
        """Test statistics tracking across operations."""
        # Perform various operations
        mock_redis.get.return_value = json.dumps({"test": "data"})
        await cache_service.get(CacheKeyType.MCP_SERVER, "test1")

        mock_redis.get.return_value = None
        await cache_service.get(CacheKeyType.MCP_SERVER, "test2")

        mock_redis.setex.return_value = True
        await cache_service.set(CacheKeyType.MCP_SERVER, "test3", {"data": "test"})

        stats = cache_service.get_stats()
        assert stats.total_operations == 3
        assert stats.cache_hits == 1
        assert stats.cache_misses == 1
        assert stats.successful_operations == 3


class TestCacheUtilities:
    """Test suite for high-level cache utilities."""

    @pytest.mark.asyncio
    async def test_mcp_server_caching(self, cache_utilities, mock_redis):
        """Test MCP server data caching."""
        server_data = MCPServerCacheData(
            server_id="test-server",
            name="Test Server",
            version="1.0.0",
            status="healthy",
            tools=[{"name": "test-tool", "description": "Test tool"}],
            last_health_check=datetime.utcnow(),
            performance_metrics={"latency": 50.0, "success_rate": 0.95},
            configuration={"port": 8080, "debug": True}
        )

        mock_redis.setex.return_value = True
        result = await cache_utilities.cache_mcp_server("test-server", server_data)

        assert result is True
        mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_mcp_server(self, cache_utilities, mock_redis):
        """Test retrieving cached MCP server data."""
        cached_data = {
            "server_id": "test-server",
            "name": "Test Server",
            "version": "1.0.0",
            "status": "healthy",
            "tools": [],
            "last_health_check": datetime.utcnow().isoformat(),
            "performance_metrics": {},
            "configuration": {}
        }
        mock_redis.get.return_value = json.dumps(cached_data)

        result = await cache_utilities.get_mcp_server("test-server")

        assert result is not None
        assert isinstance(result, MCPServerCacheData)
        assert result.server_id == "test-server"

    @pytest.mark.asyncio
    async def test_mcp_tool_caching(self, cache_utilities, mock_redis):
        """Test MCP tool data caching."""
        tool_data = {
            "tool_id": "test-tool",
            "name": "Test Tool",
            "description": "A test tool",
            "parameters": {"param1": "string"},
            "version": "1.0.0"
        }

        mock_redis.setex.return_value = True
        result = await cache_utilities.cache_mcp_tool("test-tool", tool_data, "test-server")

        assert result is True
        mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_rate_limiting(self, cache_utilities, mock_redis):
        """Test rate limiting functionality."""
        config = RateLimitConfig(max_requests=5, window_seconds=60, block_duration=300)

        # Mock no existing requests
        mock_redis.get.return_value = None

        is_limited, info = await cache_utilities.is_rate_limited("user123", config)

        assert not is_limited
        assert info["limited"] is False
        assert info["requests"] == 1  # First request

    @pytest.mark.asyncio
    async def test_rate_limiting_exceeded(self, cache_utilities, mock_redis):
        """Test rate limiting when limit is exceeded."""
        config = RateLimitConfig(max_requests=2, window_seconds=60, block_duration=300)

        # Mock existing requests at limit
        mock_redis.get.return_value = "2"

        is_limited, info = await cache_utilities.is_rate_limited("user123", config)

        assert is_limited
        assert info["limited"] is True
        assert info["reason"] == "rate_exceeded"

    @pytest.mark.asyncio
    async def test_session_management(self, cache_utilities, mock_redis):
        """Test user session management."""
        session_data = {
            "user_id": "user123",
            "username": "testuser",
            "permissions": ["read", "write"]
        }

        mock_redis.setex.return_value = True
        session_id = await cache_utilities.create_user_session("user123", session_data)

        assert session_id is not None
        assert len(session_id) == 32  # SHA256 hash truncated
        mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_session(self, cache_utilities, mock_redis):
        """Test retrieving user session."""
        session_info = {
            "user_id": "user123",
            "created_at": datetime.utcnow().isoformat(),
            "last_accessed": datetime.utcnow().isoformat(),
            "data": {"username": "testuser"}
        }
        mock_redis.get.return_value = json.dumps(session_info)
        mock_redis.setex.return_value = True

        result = await cache_utilities.get_user_session("test-session-id")

        assert result is not None
        assert result["user_id"] == "user123"
        # Should update last_accessed time
        mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_warming(self, cache_utilities, mock_redis):
        """Test cache warming functionality."""
        service_ids = ["server1", "server2", "server3"]

        # Mock some services exist, some don't
        mock_redis.exists.side_effect = [True, False, True]

        results = await cache_utilities.warm_cache(service_ids)

        assert len(results) == 3
        assert results["server1"] is True  # Already cached
        assert results["server2"] is False  # Cache miss
        assert results["server3"] is True  # Already cached

    @pytest.mark.asyncio
    async def test_cache_pattern_invalidation(self, cache_utilities, mock_redis):
        """Test cache invalidation by pattern."""
        mock_redis.keys.return_value = ["key1", "key2", "key3"]
        mock_redis.delete.return_value = 3

        result = await cache_utilities.invalidate_pattern("test:*")

        assert result == 3
        mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_service_related_invalidation(self, cache_utilities, mock_redis):
        """Test invalidating all cache entries related to a service."""
        mock_redis.keys.return_value = []
        mock_redis.delete.return_value = 0

        result = await cache_utilities.invalidate_service_related("test-service")

        assert result >= 0  # Should complete without error

    @pytest.mark.asyncio
    async def test_pub_sub_notifications(self, cache_utilities, mock_redis):
        """Test pub/sub notification system."""
        mock_redis.publish.return_value = 2

        result = await cache_utilities.notify_mcp_server_update(
            "test-server",
            "status_change",
            {"old_status": "starting", "new_status": "healthy"}
        )

        assert result == 2
        mock_redis.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_metrics_collection(self, cache_utilities, mock_redis):
        """Test cache metrics collection."""
        # Mock cache service stats
        cache_utilities.cache._stats.total_operations = 100
        cache_utilities.cache._stats.successful_operations = 95
        cache_utilities.cache._stats.cache_hits = 80
        cache_utilities.cache._stats.cache_misses = 20

        metrics = await cache_utilities.get_cache_metrics()

        assert "cache_stats" in metrics
        assert "health_check" in metrics
        assert "performance" in metrics
        assert metrics["performance"]["hit_rate"] == 0.8
        assert metrics["performance"]["success_rate"] == 0.95


class TestCacheDecorators:
    """Test suite for cache decorators and utilities."""

    @pytest.mark.asyncio
    async def test_cached_decorator(self, cache_utilities, mock_redis):
        """Test the cached decorator functionality."""
        call_count = 0

        @cache_utilities.cached(ttl=1800, key_prefix="test_func")
        async def expensive_operation(param1: str, param2: int) -> dict:
            nonlocal call_count
            call_count += 1
            return {"param1": param1, "param2": param2, "call_count": call_count}

        # First call - should execute function
        mock_redis.get.return_value = None
        mock_redis.setex.return_value = True

        result1 = await expensive_operation("test", 42)
        assert result1["call_count"] == 1
        assert call_count == 1

        # Second call - should return cached result
        mock_redis.get.return_value = json.dumps(result1)

        result2 = await expensive_operation("test", 42)
        assert result2["call_count"] == 1  # Same as cached
        assert call_count == 1  # Function not called again

    @pytest.mark.asyncio
    async def test_cache_key_generation(self, cache_utilities):
        """Test cache key generation for functions."""
        def test_function(arg1, arg2, kwarg1=None):
            pass

        key = cache_utilities._generate_function_cache_key(
            test_function,
            ("value1", "value2"),
            {"kwarg1": "kwvalue"},
            "test_prefix",
            True,
            True,
            []
        )

        assert "test_prefix" in key
        assert "test_function" in key
        # Should include hash of arguments


class TestCacheErrorHandling:
    """Test suite for cache error handling and recovery."""

    @pytest.mark.asyncio
    async def test_redis_connection_error_handling(self, cache_service, mock_redis):
        """Test handling of Redis connection errors."""
        mock_redis.get.side_effect = ConnectionError("Connection lost")

        with pytest.raises(ConnectionError):
            await cache_service.get(CacheKeyType.MCP_SERVER, "test")

        # Should record the failure
        assert cache_service._stats.failed_operations > 0

    @pytest.mark.asyncio
    async def test_redis_timeout_error_handling(self, cache_service, mock_redis):
        """Test handling of Redis timeout errors."""
        mock_redis.get.side_effect = TimeoutError("Operation timed out")

        with pytest.raises(TimeoutError):
            await cache_service.get(CacheKeyType.MCP_SERVER, "test")

    @pytest.mark.asyncio
    async def test_serialization_error_handling(self, cache_service, mock_redis):
        """Test handling of serialization errors."""
        # Create object that can't be serialized
        class UnserializableObject:
            def __init__(self):
                self.func = lambda x: x  # Functions can't be serialized

        mock_redis.setex.return_value = True
        unserializable_data = UnserializableObject()

        result = await cache_service.set(
            CacheKeyType.MCP_SERVER,
            "test",
            unserializable_data
        )

        # Should handle gracefully
        assert result is False

    @pytest.mark.asyncio
    async def test_deserialization_error_handling(self, cache_service, mock_redis):
        """Test handling of deserialization errors."""
        # Return invalid JSON
        mock_redis.get.return_value = "invalid json {"

        result = await cache_service.get(CacheKeyType.MCP_SERVER, "test")

        # Should return the raw string when JSON parsing fails
        assert result == "invalid json {"


class TestCacheIntegration:
    """Integration tests for cache service components."""

    @pytest.mark.asyncio
    async def test_full_cache_workflow(self, cache_utilities, mock_redis):
        """Test complete cache workflow from set to invalidation."""
        # Set up mock responses
        mock_redis.setex.return_value = True
        mock_redis.get.return_value = json.dumps({
            "server_id": "integration-test",
            "name": "Integration Test Server",
            "status": "healthy"
        })
        mock_redis.exists.return_value = 1
        mock_redis.delete.return_value = 1

        # 1. Cache server data
        server_data = MCPServerCacheData(
            server_id="integration-test",
            name="Integration Test Server",
            version="1.0.0",
            status="healthy",
            tools=[],
            last_health_check=datetime.utcnow(),
            performance_metrics={},
            configuration={}
        )

        cache_result = await cache_utilities.cache_mcp_server("integration-test", server_data)
        assert cache_result is True

        # 2. Retrieve cached data
        retrieved_data = await cache_utilities.get_mcp_server("integration-test")
        assert retrieved_data is not None
        assert retrieved_data.server_id == "integration-test"

        # 3. Check existence
        exists = await cache_utilities.cache.exists(CacheKeyType.MCP_SERVER, "integration-test")
        assert exists is True

        # 4. Invalidate cache
        invalidated = await cache_utilities.cache.delete(CacheKeyType.MCP_SERVER, "integration-test")
        assert invalidated is True

    @pytest.mark.asyncio
    async def test_concurrent_cache_operations(self, cache_service, mock_redis):
        """Test concurrent cache operations."""
        mock_redis.get.return_value = json.dumps({"concurrent": "test"})
        mock_redis.setex.return_value = True

        # Create multiple concurrent operations
        tasks = []
        for i in range(10):
            tasks.append(cache_service.get(CacheKeyType.MCP_SERVER, f"concurrent-{i}"))
            tasks.append(cache_service.set(CacheKeyType.MCP_SERVER, f"concurrent-{i}", {"id": i}))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All operations should complete without exceptions
        for result in results:
            assert not isinstance(result, Exception)


@pytest.mark.asyncio
async def test_cache_service_global_instance():
    """Test global cache service instance management."""
    from app.core.cache import get_cache_service, close_cache_service

    with patch('app.core.cache.CacheService') as MockCacheService:
        mock_instance = AsyncMock()
        MockCacheService.return_value = mock_instance

        # Get service instance
        service1 = await get_cache_service()
        service2 = await get_cache_service()

        # Should return same instance
        assert service1 is service2

        # Close service
        await close_cache_service()
        mock_instance.close.assert_called_once()


@pytest.mark.asyncio
async def test_cache_utilities_global_instance(cache_service):
    """Test global cache utilities instance management."""
    utils1 = await get_cache_utilities(cache_service)
    utils2 = await get_cache_utilities(cache_service)

    # Should return same instance
    assert utils1 is utils2


class TestCacheConfiguration:
    """Test suite for cache configuration and settings."""

    def test_cache_key_types(self):
        """Test cache key type enumeration."""
        assert CacheKeyType.MCP_SERVER == "mcp:server"
        assert CacheKeyType.MCP_TOOL == "mcp:tool"
        assert CacheKeyType.REGISTRY_STATUS == "registry:status"

    def test_pubsub_channels(self):
        """Test pub/sub channel enumeration."""
        assert PubSubChannel.MCP_SERVER_UPDATES == "mcp:server:updates"
        assert PubSubChannel.REGISTRY_EVENTS == "registry:events"

    def test_redis_message_validation(self):
        """Test Redis message model validation."""
        message = RedisMessage(
            channel="test:channel",
            message_type="test",
            data={"key": "value"}
        )

        assert message.channel == "test:channel"
        assert message.source == "machina-registry"
        assert isinstance(message.timestamp, datetime)

    def test_cache_stats_model(self):
        """Test cache statistics model."""
        stats = CacheStats()

        assert stats.total_operations == 0
        assert stats.connection_status == "unknown"

        # Test stats copying
        stats.total_operations = 100
        stats_copy = stats.model_copy()
        assert stats_copy.total_operations == 100

    def test_rate_limit_config(self):
        """Test rate limiting configuration."""
        config = RateLimitConfig(max_requests=50, window_seconds=3600)

        assert config.max_requests == 50
        assert config.window_seconds == 3600
        assert config.block_duration == 300  # Default

    def test_mcp_server_cache_data(self):
        """Test MCP server cache data model."""
        server_data = MCPServerCacheData(
            server_id="test-server",
            name="Test Server",
            version="1.0.0",
            status="healthy",
            tools=[{"name": "test-tool"}],
            last_health_check=datetime.utcnow(),
            performance_metrics={"latency": 50.0},
            configuration={"debug": True}
        )

        assert server_data.server_id == "test-server"
        assert len(server_data.tools) == 1
        assert server_data.performance_metrics["latency"] == 50.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
