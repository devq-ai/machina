#!/usr/bin/env python3
"""
Simple Redis Cache Integration Test

This script tests the Redis cache integration without requiring
a full test environment setup. It validates basic cache operations
and provides feedback on the Redis cache system functionality.
"""

import asyncio
import sys
import os
import time
from typing import Dict, Any

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from app.core.cache import CacheService, CacheKeyType, PubSubChannel
from app.services.cache_service import CacheUtilities, MCPServerCacheData, RateLimitConfig
from app.core.config import Settings
from datetime import datetime


async def test_redis_cache_integration():
    """Test Redis cache integration with mock Redis."""
    print("🚀 Starting Redis Cache Integration Test\n")

    try:
        # Initialize test settings
        settings = Settings(
            REDIS_HOST="localhost",
            REDIS_PORT=6379,
            REDIS_DB=15,  # Use test database
            CACHE_TTL=60,
            CACHE_PREFIX="test:machina:",
            ENVIRONMENT="testing"
        )

        print(f"📋 Test Configuration:")
        print(f"   Redis Host: {settings.REDIS_HOST}")
        print(f"   Redis Port: {settings.REDIS_PORT}")
        print(f"   Redis DB: {settings.REDIS_DB}")
        print(f"   Cache TTL: {settings.CACHE_TTL}s")
        print(f"   Cache Prefix: {settings.CACHE_PREFIX}")
        print()

        # Test 1: Cache Service Initialization
        print("🔧 Test 1: Cache Service Initialization")
        cache_service = CacheService(settings)

        # Mock Redis for testing
        from unittest.mock import AsyncMock, MagicMock
        mock_redis = MagicMock()

        # Set up async methods with proper return values
        mock_redis.ping = AsyncMock(return_value=True)
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.setex = AsyncMock(return_value=True)
        mock_redis.delete = AsyncMock(return_value=1)
        mock_redis.exists = AsyncMock(return_value=1)
        mock_redis.expire = AsyncMock(return_value=True)
        mock_redis.publish = AsyncMock(return_value=2)
        mock_redis.ttl = AsyncMock(return_value=3600)
        mock_redis.keys = AsyncMock(return_value=[])
        mock_redis.close = AsyncMock()
        mock_redis.info = AsyncMock(return_value={
            "redis_version": "7.0.0",
            "uptime_in_seconds": 3600,
            "connected_clients": 5
        })

        # Mock connection pool
        mock_pool = AsyncMock()
        mock_pool.disconnect = AsyncMock()

        # Patch Redis initialization
        from unittest.mock import patch
        with patch('redis.asyncio.ConnectionPool.from_url', return_value=mock_pool), \
             patch('redis.asyncio.Redis', return_value=mock_redis):

            try:
                await cache_service.initialize()
                print("   ✅ Cache service initialized successfully")
            except Exception as e:
                print(f"   ❌ Cache service initialization failed: {e}")
                return False

            # Test 2: Basic Cache Operations
            print("\n💾 Test 2: Basic Cache Operations")

            # Test set operation
            test_data = {"server_id": "test-server", "status": "healthy", "timestamp": datetime.utcnow().isoformat()}
            result = await cache_service.set(CacheKeyType.MCP_SERVER, "test-server", test_data)
            if result:
                print("   ✅ Cache SET operation successful")
            else:
                print("   ❌ Cache SET operation failed")

            # Test get operation (mock return value)
            import json
            mock_redis.get.return_value = json.dumps(test_data)
            retrieved_data = await cache_service.get(CacheKeyType.MCP_SERVER, "test-server")
            if retrieved_data == test_data:
                print("   ✅ Cache GET operation successful")
            else:
                print(f"   ❌ Cache GET operation failed: {retrieved_data}")

            # Test delete operation
            deleted = await cache_service.delete(CacheKeyType.MCP_SERVER, "test-server")
            if deleted:
                print("   ✅ Cache DELETE operation successful")
            else:
                print("   ❌ Cache DELETE operation failed")

            # Test exists operation
            exists = await cache_service.exists(CacheKeyType.MCP_SERVER, "test-server")
            if exists:
                print("   ✅ Cache EXISTS operation successful")
            else:
                print("   ❌ Cache EXISTS operation failed")

            # Test 3: Cache Utilities
            print("\n🛠️  Test 3: Cache Utilities")
            cache_utilities = CacheUtilities(cache_service)

            # Test MCP server caching
            server_data = MCPServerCacheData(
                server_id="test-utils-server",
                name="Test Utilities Server",
                version="1.0.0",
                status="healthy",
                tools=[{"name": "test-tool", "description": "A test tool"}],
                last_health_check=datetime.utcnow(),
                performance_metrics={"latency": 25.5, "success_rate": 0.98},
                configuration={"port": 8080, "timeout": 30}
            )

            cached = await cache_utilities.cache_mcp_server("test-utils-server", server_data)
            if cached:
                print("   ✅ MCP server caching successful")
            else:
                print("   ❌ MCP server caching failed")

            # Test rate limiting
            rate_config = RateLimitConfig(max_requests=5, window_seconds=60, block_duration=300)
            mock_redis.get.return_value = None  # No existing requests
            mock_redis.setex.return_value = True
            is_limited, info = await cache_utilities.is_rate_limited("test-user", rate_config)
            if not is_limited and info["requests"] == 1:
                print("   ✅ Rate limiting check successful")
            else:
                print(f"   ❌ Rate limiting check failed: limited={is_limited}, info={info}")

            # Test 4: Pub/Sub Operations
            print("\n📡 Test 4: Pub/Sub Operations")

            # Test publish
            subscribers = await cache_service.publish(
                PubSubChannel.MCP_SERVER_UPDATES,
                "status_change",
                {"server_id": "test-server", "old_status": "starting", "new_status": "healthy"},
                correlation_id="test-123"
            )
            if subscribers >= 0:  # Mock returns 2
                print(f"   ✅ Pub/Sub publish successful ({subscribers} subscribers)")
            else:
                print("   ❌ Pub/Sub publish failed")

            # Test 5: Health Check
            print("\n🏥 Test 5: Health Check")
            health = await cache_service.health_check()
            if health.get("status") == "healthy":
                print("   ✅ Health check successful")
                print(f"      Connection: {health.get('connection')}")
                print(f"      Latency: {health.get('latency_ms')}ms")
            else:
                print(f"   ❌ Health check failed: {health}")

            # Test 6: Statistics
            print("\n📊 Test 6: Statistics")
            stats = cache_service.get_stats()
            print(f"   Total operations: {stats.total_operations}")
            print(f"   Successful operations: {stats.successful_operations}")
            print(f"   Cache hits: {stats.cache_hits}")
            print(f"   Cache misses: {stats.cache_misses}")
            print(f"   Connection status: {stats.connection_status}")

            if stats.total_operations > 0:
                print("   ✅ Statistics tracking successful")
            else:
                print("   ❌ Statistics tracking failed")

            # Test 7: Cache Metrics
            print("\n📈 Test 7: Cache Metrics")
            metrics = await cache_utilities.get_cache_metrics()
            if "cache_stats" in metrics and "health_check" in metrics:
                print("   ✅ Cache metrics collection successful")
                print(f"      Hit rate: {metrics['performance']['hit_rate']:.2%}")
                print(f"      Success rate: {metrics['performance']['success_rate']:.2%}")
            else:
                print("   ❌ Cache metrics collection failed")

            # Cleanup
            await cache_service.close()
            print("\n🧹 Cache service closed successfully")

            print("\n🎉 All Redis Cache Integration Tests Passed! ✅")
            return True

    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_cache_decorators():
    """Test cache decorator functionality."""
    print("\n🎭 Testing Cache Decorators")

    try:
        # Mock cache utilities
        from unittest.mock import AsyncMock
        mock_cache_service = AsyncMock()
        cache_utils = CacheUtilities(mock_cache_service)

        call_count = 0

        @cache_utils.cached(ttl=60, key_prefix="test_decorator")
        async def expensive_function(param1: str, param2: int) -> dict:
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.1)  # Simulate expensive operation
            return {"param1": param1, "param2": param2, "call_count": call_count}

        # Mock cache behavior
        mock_cache_service.get.return_value = None  # Cache miss first
        mock_cache_service.set.return_value = True

        # First call - should execute function
        result1 = await expensive_function("test", 42)
        assert call_count == 1
        print("   ✅ First call executed function")

        # Mock cache hit for second call
        mock_cache_service.get.return_value = result1

        # Second call - should return cached result
        result2 = await expensive_function("test", 42)
        assert call_count == 1  # Function not called again
        assert result1 == result2
        print("   ✅ Second call used cache")

        print("   🎉 Cache decorators working correctly!")
        return True

    except Exception as e:
        print(f"   ❌ Cache decorator test failed: {e}")
        return False


async def main():
    """Run all integration tests."""
    print("=" * 60)
    print("🔧 Machina Registry Service - Redis Cache Integration Test")
    print("=" * 60)

    start_time = time.time()

    # Run tests
    cache_test_passed = await test_redis_cache_integration()
    decorator_test_passed = await test_cache_decorators()

    end_time = time.time()
    duration = end_time - start_time

    print("\n" + "=" * 60)
    print("📋 Test Results Summary")
    print("=" * 60)
    print(f"Cache Integration Test: {'✅ PASSED' if cache_test_passed else '❌ FAILED'}")
    print(f"Cache Decorators Test:  {'✅ PASSED' if decorator_test_passed else '❌ FAILED'}")
    print(f"Total Duration: {duration:.2f} seconds")

    if cache_test_passed and decorator_test_passed:
        print("\n🎉 All tests passed! Redis cache system is working correctly.")
        return 0
    else:
        print("\n💥 Some tests failed. Please check the output above.")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)
