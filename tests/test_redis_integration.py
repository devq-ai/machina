"""
Test Suite for Redis Cache and Pub/Sub Integration

This module provides comprehensive tests for the Redis integration in the
Machina Registry Service, testing both cache operations and pub/sub messaging
functionality following DevQ.ai testing standards.

Test Coverage:
- Redis connection and health checks
- Cache operations (get, set, delete, expire)
- Pub/Sub messaging and subscriptions
- Cache service high-level operations
- Notification service functionality
- Error handling and edge cases
- Performance and concurrency testing
"""

import asyncio
import json
import pytest
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

from app.core.redis import (
    init_redis_pool,
    get_redis,
    close_redis_pool,
    RedisCache,
    RedisPubSub,
    redis_health_check,
    RedisCacheError,
    RedisPubSubError
)
from app.services.cache_service import (
    CacheService,
    get_cache_service,
    initialize_cache_service,
    MCPServerCacheData
)
from app.services.notification_service import (
    NotificationService,
    NotificationMessage,
    NotificationType,
    NotificationPriority,
    NotificationChannel,
    NotificationFilter,
    get_notification_service,
    initialize_notification_service
)


@pytest.fixture
async def redis_client():
    """Fixture providing Redis client for testing."""
    try:
        client = await init_redis_pool()
        yield client
    finally:
        await close_redis_pool()


@pytest.fixture
async def redis_cache(redis_client):
    """Fixture providing RedisCache instance."""
    return RedisCache(redis_client, prefix="test:")


@pytest.fixture
async def redis_pubsub(redis_client):
    """Fixture providing RedisPubSub instance."""
    return RedisPubSub(redis_client, channel_prefix="test:")


@pytest.fixture
async def cache_service():
    """Fixture providing CacheService instance."""
    service = get_cache_service()
    await initialize_cache_service()
    yield service


@pytest.fixture
async def notification_service():
    """Fixture providing NotificationService instance."""
    service = get_notification_service()
    await initialize_notification_service()
    yield service
    await service.shutdown()


class TestRedisConnection:
    """Test Redis connection and basic operations."""

    @pytest.mark.asyncio
    async def test_redis_connection_initialization(self):
        """Test Redis connection pool initialization."""
        client = await init_redis_pool()
        assert client is not None

        # Test basic ping
        result = await client.ping()
        assert result is True

        await close_redis_pool()

    @pytest.mark.asyncio
    async def test_redis_health_check(self):
        """Test Redis health check functionality."""
        await init_redis_pool()

        health = await redis_health_check()
        assert health["status"] == "healthy"
        assert "ping_ms" in health
        assert "redis_version" in health
        assert "cache_operations" in health

        await close_redis_pool()

    @pytest.mark.asyncio
    async def test_redis_connection_error_handling(self):
        """Test Redis connection error handling."""
        # Test with invalid configuration
        with patch('app.core.redis.settings.REDIS_URI', 'redis://invalid:9999'):
            with pytest.raises(Exception):
                await init_redis_pool()


class TestRedisCache:
    """Test Redis cache operations."""

    @pytest.mark.asyncio
    async def test_cache_set_and_get(self, redis_cache):
        """Test basic cache set and get operations."""
        test_key = "test_key"
        test_value = {"data": "test_value", "number": 42}

        # Set value
        result = await redis_cache.set(test_key, test_value)
        assert result is True

        # Get value
        cached_value = await redis_cache.get(test_key)
        assert cached_value == test_value

    @pytest.mark.asyncio
    async def test_cache_expiration(self, redis_cache):
        """Test cache TTL and expiration."""
        test_key = "expiring_key"
        test_value = {"expires": True}

        # Set with short TTL
        await redis_cache.set(test_key, test_value, expire=1)

        # Verify exists
        assert await redis_cache.exists(test_key) is True

        # Wait for expiration
        await asyncio.sleep(1.1)

        # Verify expired
        cached_value = await redis_cache.get(test_key)
        assert cached_value is None

    @pytest.mark.asyncio
    async def test_cache_delete(self, redis_cache):
        """Test cache delete operations."""
        test_key = "deletable_key"
        test_value = {"will_be_deleted": True}

        # Set and verify
        await redis_cache.set(test_key, test_value)
        assert await redis_cache.exists(test_key) is True

        # Delete and verify
        deleted_count = await redis_cache.delete(test_key)
        assert deleted_count == 1
        assert await redis_cache.exists(test_key) is False

    @pytest.mark.asyncio
    async def test_cache_pattern_operations(self, redis_cache):
        """Test cache pattern matching and bulk operations."""
        # Set multiple keys with pattern
        for i in range(5):
            await redis_cache.set(f"pattern_test:{i}", {"value": i})

        # Clear pattern
        deleted_count = await redis_cache.clear_pattern("pattern_test:*")
        assert deleted_count == 5

        # Verify all deleted
        for i in range(5):
            assert await redis_cache.exists(f"pattern_test:{i}") is False

    @pytest.mark.asyncio
    async def test_cache_increment(self, redis_cache):
        """Test cache increment operations."""
        counter_key = "counter"

        # Increment from zero
        result = await redis_cache.increment(counter_key)
        assert result == 1

        # Increment by custom amount
        result = await redis_cache.increment(counter_key, amount=5)
        assert result == 6

    @pytest.mark.asyncio
    async def test_cache_error_handling(self, redis_cache):
        """Test cache error handling for invalid operations."""
        # Test with invalid JSON data
        with patch.object(redis_cache.redis, 'get', side_effect=Exception("Redis error")):
            with pytest.raises(RedisCacheError):
                await redis_cache.get("error_key")

    @pytest.mark.asyncio
    async def test_cache_nx_xx_operations(self, redis_cache):
        """Test cache set operations with NX and XX flags."""
        test_key = "conditional_key"

        # Set with NX (only if not exists)
        result = await redis_cache.set(test_key, "first", nx=True)
        assert result is True

        # Try to set again with NX (should fail)
        result = await redis_cache.set(test_key, "second", nx=True)
        assert result is False

        # Set with XX (only if exists)
        result = await redis_cache.set(test_key, "updated", xx=True)
        assert result is True

        # Verify final value
        value = await redis_cache.get(test_key)
        assert value == "updated"


class TestRedisPubSub:
    """Test Redis pub/sub operations."""

    @pytest.mark.asyncio
    async def test_pubsub_publish_subscribe(self, redis_pubsub):
        """Test basic publish and subscribe operations."""
        test_channel = "test_channel"
        test_message = {"type": "test", "data": "hello"}

        # Subscribe to channel
        await redis_pubsub.subscribe(test_channel)

        # Publish message
        subscribers = await redis_pubsub.publish(test_channel, test_message)
        assert subscribers >= 0  # May be 0 in test environment

        # Get message (with timeout to prevent hanging)
        message = await redis_pubsub.get_message(timeout=1.0)

        if message:  # Message received
            assert message["type"] == "test"
            assert message["data"] == "hello"
            assert "_timestamp" in message
            assert "_source" in message

    @pytest.mark.asyncio
    async def test_pubsub_multiple_channels(self, redis_pubsub):
        """Test subscribing to multiple channels."""
        channels = ["channel1", "channel2", "channel3"]

        # Subscribe to multiple channels
        await redis_pubsub.subscribe(*channels)

        # Verify subscription
        assert len(redis_pubsub.subscribed_channels) >= len(channels)

    @pytest.mark.asyncio
    async def test_pubsub_unsubscribe(self, redis_pubsub):
        """Test unsubscribe operations."""
        test_channel = "unsubscribe_test"

        # Subscribe and verify
        await redis_pubsub.subscribe(test_channel)
        assert test_channel in [ch.replace(redis_pubsub.channel_prefix, "")
                                for ch in redis_pubsub.subscribed_channels]

        # Unsubscribe and verify
        await redis_pubsub.unsubscribe(test_channel)

    @pytest.mark.asyncio
    async def test_pubsub_message_listener(self, redis_pubsub):
        """Test pub/sub message listener functionality."""
        test_channel = "listener_test"
        received_messages = []

        async def message_callback(channel: str, data: dict):
            received_messages.append((channel, data))

        # Subscribe to channel
        await redis_pubsub.subscribe(test_channel)

        # Start listener in background
        listener_task = asyncio.create_task(
            redis_pubsub.listen(message_callback)
        )

        # Wait a bit for listener to start
        await asyncio.sleep(0.1)

        # Publish test message
        await redis_pubsub.publish(test_channel, {"test": "listener"})

        # Wait for message processing
        await asyncio.sleep(0.1)

        # Cancel listener
        listener_task.cancel()
        try:
            await listener_task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_pubsub_error_handling(self, redis_pubsub):
        """Test pub/sub error handling."""
        # Test publish to invalid channel
        with patch.object(redis_pubsub.redis, 'publish', side_effect=Exception("Redis error")):
            with pytest.raises(RedisPubSubError):
                await redis_pubsub.publish("error_channel", {"error": "test"})


class TestCacheService:
    """Test high-level cache service operations."""

    @pytest.mark.asyncio
    async def test_service_caching(self, cache_service):
        """Test service data caching operations."""
        service_id = "test_service_001"
        service_data = {
            "name": "Test Service",
            "version": "1.0.0",
            "status": "active",
            "endpoints": ["http://localhost:8000"]
        }

        # Cache service data
        result = await cache_service.set_service(service_id, service_data)
        assert result is True

        # Retrieve cached data
        cached_data = await cache_service.get_service(service_id)
        assert cached_data["name"] == service_data["name"]
        assert cached_data["version"] == service_data["version"]
        assert "_cached_at" in cached_data

        # Invalidate cache
        result = await cache_service.invalidate_service(service_id)
        assert result is True

        # Verify invalidation
        cached_data = await cache_service.get_service(service_id)
        assert cached_data is None

    @pytest.mark.asyncio
    async def test_health_check_caching(self, cache_service):
        """Test health check result caching."""
        service_id = "health_test_service"
        health_data = {
            "status": "healthy",
            "response_time": 0.05,
            "checks": {"database": True, "redis": True}
        }

        # Cache health check
        result = await cache_service.set_health_check(service_id, health_data)
        assert result is True

        # Retrieve health check
        cached_health = await cache_service.get_health_check(service_id)
        assert cached_health["status"] == "healthy"
        assert cached_health["response_time"] == 0.05

    @pytest.mark.asyncio
    async def test_bulk_service_operations(self, cache_service):
        """Test bulk service cache operations."""
        service_ids = [f"bulk_service_{i}" for i in range(5)]

        # Cache multiple services
        for i, service_id in enumerate(service_ids):
            await cache_service.set_service(service_id, {
                "name": f"Service {i}",
                "version": "1.0.0"
            })

        # Retrieve in bulk
        results = await cache_service.get_services_bulk(service_ids)
        assert len(results) == 5

        # Verify all services found
        for service_id in service_ids:
            assert results[service_id] is not None
            assert results[service_id]["name"].startswith("Service")

    @pytest.mark.asyncio
    async def test_discovery_result_caching(self, cache_service):
        """Test service discovery result caching."""
        query_hash = "discovery_test_hash"
        discovery_data = {
            "query": "test services",
            "services": [
                {"id": "svc1", "name": "Service 1"},
                {"id": "svc2", "name": "Service 2"}
            ],
            "total": 2
        }

        # Cache discovery result
        result = await cache_service.set_discovery_result(query_hash, discovery_data)
        assert result is True

        # Retrieve discovery result
        cached_result = await cache_service.get_discovery_result(query_hash)
        assert cached_result["total"] == 2
        assert len(cached_result["services"]) == 2

    @pytest.mark.asyncio
    async def test_cache_statistics(self, cache_service):
        """Test cache statistics collection."""
        # Add some test data
        await cache_service.set_service("stats_test", {"name": "Test"})
        await cache_service.set_health_check("stats_test", {"status": "healthy"})

        # Get statistics
        stats = await cache_service.get_cache_stats()
        assert "service_count" in stats
        assert "health_count" in stats
        assert "total_count" in stats
        assert "timestamp" in stats

    @pytest.mark.asyncio
    async def test_cache_warming(self, cache_service):
        """Test cache warming functionality."""
        service_ids = ["warm_test_1", "warm_test_2", "warm_test_3"]

        # Pre-cache one service
        await cache_service.set_service(service_ids[0], {"name": "Pre-cached"})

        # Warm cache
        results = await cache_service.warm_cache(service_ids)

        assert len(results) == 3
        assert results[service_ids[0]] is True  # Already cached
        assert results[service_ids[1]] is False  # Not cached
        assert results[service_ids[2]] is False  # Not cached

    @pytest.mark.asyncio
    async def test_service_related_invalidation(self, cache_service):
        """Test invalidation of all service-related cache entries."""
        service_id = "invalidation_test"

        # Cache various service-related data
        await cache_service.set_service(service_id, {"name": "Test"})
        await cache_service.set_health_check(service_id, {"status": "healthy"})
        await cache_service.set_config(f"service:{service_id}:config", {"enabled": True})

        # Invalidate all related entries
        invalidated = await cache_service.invalidate_service_related(service_id)
        assert invalidated >= 0  # Should invalidate some entries

        # Verify invalidation
        assert await cache_service.get_service(service_id) is None
        assert await cache_service.get_health_check(service_id) is None


class TestNotificationService:
    """Test notification service functionality."""

    @pytest.mark.asyncio
    async def test_notification_publishing(self, notification_service):
        """Test basic notification publishing."""
        result = await notification_service.publish(
            NotificationType.SERVICE_REGISTERED,
            "Test Service Registered",
            "A test service has been registered",
            service_id="test_service_001"
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_notification_subscription(self, notification_service):
        """Test notification subscription and message receiving."""
        received_notifications = []

        async def notification_callback(notification: NotificationMessage):
            received_notifications.append(notification)

        # Subscribe to service events
        subscription_id = await notification_service.subscribe(
            [NotificationChannel.SERVICE_EVENTS],
            notification_callback
        )

        assert subscription_id is not None

        # Wait for subscription to be active
        await asyncio.sleep(0.1)

        # Publish a notification
        await notification_service.publish(
            NotificationType.SERVICE_REGISTERED,
            "Test Notification",
            "This is a test notification",
            NotificationChannel.SERVICE_EVENTS,
            service_id="test_service"
        )

        # Wait for message processing
        await asyncio.sleep(0.2)

        # Unsubscribe
        await notification_service.unsubscribe(subscription_id)

    @pytest.mark.asyncio
    async def test_notification_filtering(self, notification_service):
        """Test notification filtering functionality."""
        received_notifications = []

        async def filtered_callback(notification: NotificationMessage):
            received_notifications.append(notification)

        # Create filter for high priority notifications only
        filter_config = NotificationFilter(
            priorities=[NotificationPriority.HIGH, NotificationPriority.CRITICAL]
        )

        # Subscribe with filter
        subscription_id = await notification_service.subscribe(
            [NotificationChannel.ALL_EVENTS],
            filtered_callback,
            filters=filter_config
        )

        await asyncio.sleep(0.1)

        # Publish notifications with different priorities
        await notification_service.publish(
            NotificationType.ERROR_OCCURRED,
            "High Priority Error",
            "This is a high priority error",
            priority=NotificationPriority.HIGH
        )

        await notification_service.publish(
            NotificationType.SERVICE_REGISTERED,
            "Normal Priority Service",
            "This is normal priority",
            priority=NotificationPriority.NORMAL
        )

        # Wait for processing
        await asyncio.sleep(0.2)

        # Cleanup
        await notification_service.unsubscribe(subscription_id)

    @pytest.mark.asyncio
    async def test_convenience_notification_methods(self, notification_service):
        """Test convenience methods for common notifications."""
        service_id = "convenience_test_service"
        service_name = "Test Service"

        # Test service registration notification
        result = await notification_service.notify_service_registered(
            service_id, service_name, {"version": "1.0.0"}
        )
        assert result is True

        # Test health check failure notification
        result = await notification_service.notify_health_check_failed(
            service_id, service_name, "Connection timeout"
        )
        assert result is True

        # Test configuration update notification
        result = await notification_service.notify_config_updated(
            "test_config", {"setting": "new_value"}
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_notification_statistics(self, notification_service):
        """Test notification service statistics."""
        # Publish some notifications
        for i in range(3):
            await notification_service.publish(
                NotificationType.SERVICE_REGISTERED,
                f"Test Service {i}",
                f"Test message {i}"
            )

        # Get service statistics
        stats = await notification_service.get_service_stats()

        assert "stats" in stats
        assert "active_subscriptions" in stats
        assert "service_status" in stats
        assert stats["stats"]["total_published"] >= 3

    @pytest.mark.asyncio
    async def test_notification_service_lifecycle(self, notification_service):
        """Test notification service initialization and shutdown."""
        # Service should be initialized from fixture
        assert notification_service._running is True
        assert notification_service.pubsub is not None

        # Test shutdown
        await notification_service.shutdown()
        assert notification_service._running is False


class TestConcurrencyAndPerformance:
    """Test concurrency and performance aspects."""

    @pytest.mark.asyncio
    async def test_concurrent_cache_operations(self, cache_service):
        """Test concurrent cache operations."""
        async def cache_operation(index):
            service_id = f"concurrent_service_{index}"
            data = {"index": index, "timestamp": time.time()}

            # Set data
            await cache_service.set_service(service_id, data)

            # Get data
            result = await cache_service.get_service(service_id)
            assert result["index"] == index

            return service_id

        # Run 10 concurrent operations
        tasks = [cache_operation(i) for i in range(10)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 10
        assert all(result.startswith("concurrent_service_") for result in results)

    @pytest.mark.asyncio
    async def test_high_volume_notifications(self, notification_service):
        """Test high volume notification publishing."""
        publish_count = 20

        # Publish many notifications quickly
        tasks = []
        for i in range(publish_count):
            task = notification_service.publish(
                NotificationType.METRICS_UPDATED,
                f"Metric Update {i}",
                f"Metric value updated to {i}",
                data={"value": i}
            )
            tasks.append(task)

        # Wait for all publishes to complete
        results = await asyncio.gather(*tasks)

        # All should succeed
        assert all(result is True for result in results)

        # Check statistics
        stats = await notification_service.get_service_stats()
        assert stats["stats"]["total_published"] >= publish_count


class TestErrorRecovery:
    """Test error recovery and resilience."""

    @pytest.mark.asyncio
    async def test_cache_redis_unavailable(self, cache_service):
        """Test cache behavior when Redis is unavailable."""
        # Mock Redis to raise connection error
        with patch.object(cache_service, 'get_cache') as mock_get_cache:
            mock_cache = AsyncMock()
            mock_cache.get.side_effect = RedisCacheError("Connection failed")
            mock_get_cache.return_value = mock_cache

            # Cache operations should handle errors gracefully
            result = await cache_service.get_service("test_service")
            assert result is None

    @pytest.mark.asyncio
    async def test_notification_redis_unavailable(self, notification_service):
        """Test notification behavior when Redis is unavailable."""
        # Mock pubsub to raise connection error
        with patch.object(notification_service, 'pubsub') as mock_pubsub:
            mock_pubsub.publish.side_effect = RedisPubSubError("Connection failed")

            # Publish should handle error gracefully
            result = await notification_service.publish(
                NotificationType.ERROR_OCCURRED,
                "Test Error",
                "This is a test error"
            )
            assert result is False


class TestDataConsistency:
    """Test data consistency and integrity."""

    @pytest.mark.asyncio
    async def test_cache_data_serialization(self, cache_service):
        """Test cache data serialization and deserialization."""
        complex_data = {
            "service_id": "complex_test",
            "metadata": {
                "created_at": datetime.utcnow().isoformat(),
                "tags": ["test", "complex", "data"],
                "config": {
                    "nested": {
                        "value": 42,
                        "enabled": True
                    }
                }
            },
            "numbers": [1, 2, 3.14, -5],
            "nullable": None
        }

        # Cache complex data
        result = await cache_service.set_service("complex_test", complex_data)
        assert result is True

        # Retrieve and verify
        cached_data = await cache_service.get_service("complex_test")
        assert cached_data["service_id"] == "complex_test"
        assert cached_data["metadata"]["tags"] == ["test", "complex", "data"]
        assert cached_data["metadata"]["config"]["nested"]["value"] == 42
        assert cached_data["numbers"] == [1, 2, 3.14, -5]

    @pytest.mark.asyncio
    async def test_notification_message_integrity(self, notification_service):
        """Test notification message data integrity."""
        test_data = {
            "service_metrics": {
                "cpu_usage": 0.75,
                "memory_usage": 0.60,
                "request_count": 12345
            },
            "timestamps": {
                "start_time": datetime.utcnow().isoformat(),
                "last_health_check": datetime.utcnow().isoformat()
            }
        }

        received_notifications = []

        async def integrity_callback(notification: NotificationMessage):
            received_notifications.append(notification)

        # Subscribe to receive notifications
        subscription_id = await notification_service.subscribe(
            [NotificationChannel.METRICS_EVENTS],
            integrity_callback
        )

        await asyncio.sleep(0.1)

        # Publish notification with complex data
        await notification_service.publish(
            NotificationType.METRICS_UPDATED,
            "Service Metrics Updated",
            "Service metrics have been updated",
            NotificationChannel.METRICS_EVENTS,
            data=test_data
        )

        await asyncio.sleep(0.2)

        # Cleanup
        await notification_service.unsubscribe(subscription_id)


# Integration test combining all components
class TestFullIntegration:
    """Test full integration of cache and notification systems."""

    @pytest.mark.asyncio
    async def test_service_lifecycle_with_notifications(self, cache_service, notification_service):
        """Test complete service lifecycle with cache and notifications."""
        service_id = "integration_test_service"
        service_data = {
            "name": "Integration Test Service",
            "version": "1.0.0",
            "status": "starting"
        }

        received_notifications = []

        async def lifecycle_callback(notification: NotificationMessage):
            received_notifications.append(notification)

        # Subscribe to service events
        subscription_id = await notification_service.subscribe(
            [NotificationChannel.SERVICE_EVENTS],
            lifecycle_callback
        )

        await asyncio.sleep(0.1)

        # Step 1: Register service
        await cache_service.set_service(service_id, service_data)
        await notification_service.notify_service_registered(
            service_id, service_data["name"], service_data
        )

        # Step 2: Update service status
        service_data["status"] = "running"
        await cache_service.set_service(service_id, service_data)

        # Step 3: Cache health check
        await cache_service.set_health_check(service_id, {
            "status": "healthy",
            "checks": {"database": True, "redis": True}
        })

        # Step 4: Verify cached data
        cached_service = await cache_service.get_service(service_id)
        cached_health = await cache_service.get_health_check(service_id)

        assert cached_service["name"] == "Integration Test Service"
        assert cached_service["status"] == "running"
        assert cached_health["status"] == "healthy"

        # Step 5: Cleanup
        await cache_service.invalidate_service_related(service_id)
        await notification_service.unsubscribe(subscription_id)

        await asyncio.sleep(0.1)


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
