"""
Redis Connection and Management Module for Machina Registry Service

This module provides Redis connection management, caching, and pub/sub functionality
following DevQ.ai standards with comprehensive error handling, logging, and async support.

Features:
- Async Redis connection management with connection pooling
- Structured caching with JSON serialization and TTL support
- Pub/Sub messaging system for real-time updates
- Health checking and connection monitoring
- Type-safe interfaces with comprehensive error handling
- Logfire integration for observability
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Union, Callable, Awaitable
from datetime import datetime, timedelta
import redis.asyncio as redis
from redis.asyncio.client import Redis
from redis.asyncio.connection import ConnectionPool
from redis.exceptions import ConnectionError, TimeoutError, RedisError
import logfire

from app.core.config import settings

# Configure logging
logger = logging.getLogger(__name__)

# Global Redis client and connection pool
redis_client: Optional[Redis] = None
redis_pool: Optional[ConnectionPool] = None


class RedisConnectionError(Exception):
    """Custom exception for Redis connection issues."""
    pass


class RedisCacheError(Exception):
    """Custom exception for Redis cache operations."""
    pass


class RedisPubSubError(Exception):
    """Custom exception for Redis pub/sub operations."""
    pass


async def init_redis_pool() -> Redis:
    """
    Initialize Redis connection pool and client.

    Creates a connection pool with health checking and monitoring,
    following DevQ.ai patterns for resource management.

    Returns:
        Redis: Configured Redis client instance

    Raises:
        RedisConnectionError: If connection cannot be established
    """
    global redis_client, redis_pool

    with logfire.span("Redis Connection Initialization"):
        try:
            # Create connection pool with configuration from settings
            redis_pool = ConnectionPool.from_url(
                settings.REDIS_URI,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30,
                max_connections=20,
            )

            # Create Redis client with the pool
            redis_client = Redis(connection_pool=redis_pool)

            # Test the connection
            await redis_client.ping()

            logfire.info(
                "Redis connection established",
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB
            )

            return redis_client

        except Exception as e:
            logfire.error(
                "Failed to initialize Redis connection",
                error=str(e),
                redis_uri=settings.REDIS_URI
            )
            raise RedisConnectionError(f"Failed to connect to Redis: {str(e)}")


async def get_redis() -> Redis:
    """
    Get Redis client instance.

    Returns the global Redis client, initializing it if necessary.

    Returns:
        Redis: Active Redis client instance

    Raises:
        RedisConnectionError: If Redis client is not available
    """
    global redis_client

    if redis_client is None:
        await init_redis_pool()

    if redis_client is None:
        raise RedisConnectionError("Redis client is not initialized")

    return redis_client


async def close_redis_pool():
    """
    Close Redis connection pool and cleanup resources.

    Should be called during application shutdown to properly
    close connections and free resources.
    """
    global redis_client, redis_pool

    with logfire.span("Redis Connection Cleanup"):
        try:
            if redis_client:
                await redis_client.aclose()
                redis_client = None

            if redis_pool:
                await redis_pool.aclose()
                redis_pool = None

            logfire.info("Redis connections closed successfully")

        except Exception as e:
            logfire.error("Error closing Redis connections", error=str(e))


async def health_check() -> bool:
    """
    Check Redis connection health.

    Returns:
        bool: True if Redis is healthy, False otherwise
    """
    try:
        redis = await get_redis()
        await redis.ping()
        return True
    except Exception as e:
        logfire.warning("Redis health check failed", error=str(e))
        return False


class RedisCache:
    """
    Redis-based caching service with JSON serialization and TTL support.

    Provides high-level caching operations with proper error handling,
    logging, and type safety following DevQ.ai patterns.
    """

    def __init__(self, redis_client: Redis, prefix: str = None):
        """
        Initialize Redis cache service.

        Args:
            redis_client: Redis client instance
            prefix: Optional key prefix for namespacing
        """
        self.redis = redis_client
        self.prefix = prefix or settings.CACHE_PREFIX
        self.default_ttl = settings.CACHE_TTL

    def _make_key(self, key: str) -> str:
        """Generate prefixed cache key."""
        return f"{self.prefix}{key}"

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found

        Raises:
            RedisCacheError: If cache operation fails
        """
        cache_key = self._make_key(key)

        with logfire.span("Redis Cache Get", cache_key=cache_key):
            try:
                data = await self.redis.get(cache_key)
                if data is not None:
                    result = json.loads(data)
                    logfire.info("Cache hit", cache_key=cache_key)
                    return result
                else:
                    logfire.info("Cache miss", cache_key=cache_key)
                    return None

            except json.JSONDecodeError as e:
                logfire.error("Cache data deserialization failed", cache_key=cache_key, error=str(e))
                # Remove corrupted data
                await self.delete(key)
                return None

            except RedisError as e:
                logfire.error("Redis cache get operation failed", cache_key=cache_key, error=str(e))
                raise RedisCacheError(f"Failed to get cache key {key}: {str(e)}")

    async def set(
        self,
        key: str,
        value: Any,
        expire: Optional[int] = None,
        nx: bool = False,
        xx: bool = False
    ) -> bool:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            expire: TTL in seconds (uses default if None)
            nx: Only set if key doesn't exist
            xx: Only set if key exists

        Returns:
            bool: True if operation successful

        Raises:
            RedisCacheError: If cache operation fails
        """
        cache_key = self._make_key(key)
        ttl = expire or self.default_ttl

        with logfire.span("Redis Cache Set", cache_key=cache_key, ttl=ttl):
            try:
                serialized = json.dumps(value, default=str)
                result = await self.redis.set(
                    cache_key,
                    serialized,
                    ex=ttl,
                    nx=nx,
                    xx=xx
                )

                if result:
                    logfire.info("Cache set successful", cache_key=cache_key, ttl=ttl)
                else:
                    logfire.warning("Cache set failed (condition not met)", cache_key=cache_key)

                return bool(result)

            except (TypeError, ValueError) as e:
                logfire.error("Cache data serialization failed", cache_key=cache_key, error=str(e))
                raise RedisCacheError(f"Failed to serialize value for key {key}: {str(e)}")

            except RedisError as e:
                logfire.error("Redis cache set operation failed", cache_key=cache_key, error=str(e))
                raise RedisCacheError(f"Failed to set cache key {key}: {str(e)}")

    async def delete(self, key: str) -> int:
        """
        Delete key from cache.

        Args:
            key: Cache key to delete

        Returns:
            int: Number of keys deleted (0 or 1)

        Raises:
            RedisCacheError: If cache operation fails
        """
        cache_key = self._make_key(key)

        with logfire.span("Redis Cache Delete", cache_key=cache_key):
            try:
                result = await self.redis.delete(cache_key)
                logfire.info("Cache delete", cache_key=cache_key, deleted=result)
                return result

            except RedisError as e:
                logfire.error("Redis cache delete operation failed", cache_key=cache_key, error=str(e))
                raise RedisCacheError(f"Failed to delete cache key {key}: {str(e)}")

    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.

        Args:
            key: Cache key to check

        Returns:
            bool: True if key exists
        """
        cache_key = self._make_key(key)
        try:
            return bool(await self.redis.exists(cache_key))
        except RedisError as e:
            logfire.error("Redis cache exists check failed", cache_key=cache_key, error=str(e))
            return False

    async def expire(self, key: str, seconds: int) -> bool:
        """
        Set TTL for existing key.

        Args:
            key: Cache key
            seconds: TTL in seconds

        Returns:
            bool: True if TTL was set
        """
        cache_key = self._make_key(key)
        try:
            result = await self.redis.expire(cache_key, seconds)
            logfire.info("Cache TTL updated", cache_key=cache_key, ttl=seconds)
            return bool(result)
        except RedisError as e:
            logfire.error("Redis cache expire operation failed", cache_key=cache_key, error=str(e))
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern.

        Args:
            pattern: Key pattern with wildcards

        Returns:
            int: Number of keys deleted

        Raises:
            RedisCacheError: If cache operation fails
        """
        search_pattern = self._make_key(pattern)

        with logfire.span("Redis Cache Clear Pattern", pattern=search_pattern):
            try:
                keys = await self.redis.keys(search_pattern)
                if keys:
                    result = await self.redis.delete(*keys)
                    logfire.info("Cache pattern cleared", pattern=search_pattern, deleted=result)
                    return result
                return 0

            except RedisError as e:
                logfire.error("Redis cache clear pattern failed", pattern=search_pattern, error=str(e))
                raise RedisCacheError(f"Failed to clear cache pattern {pattern}: {str(e)}")

    async def increment(self, key: str, amount: int = 1) -> int:
        """
        Increment numeric value in cache.

        Args:
            key: Cache key
            amount: Amount to increment by

        Returns:
            int: New value after increment
        """
        cache_key = self._make_key(key)
        try:
            result = await self.redis.incrby(cache_key, amount)
            logfire.info("Cache increment", cache_key=cache_key, amount=amount, new_value=result)
            return result
        except RedisError as e:
            logfire.error("Redis cache increment failed", cache_key=cache_key, error=str(e))
            raise RedisCacheError(f"Failed to increment cache key {key}: {str(e)}")


class RedisPubSub:
    """
    Redis pub/sub service for real-time messaging.

    Provides publish/subscribe functionality with proper error handling,
    message serialization, and connection management.
    """

    def __init__(self, redis_client: Redis, channel_prefix: str = None):
        """
        Initialize Redis pub/sub service.

        Args:
            redis_client: Redis client instance
            channel_prefix: Optional channel prefix for namespacing
        """
        self.redis = redis_client
        self.channel_prefix = channel_prefix or "machina:events:"
        self.pubsub = None
        self.subscribed_channels = set()

    def _make_channel(self, channel: str) -> str:
        """Generate prefixed channel name."""
        return f"{self.channel_prefix}{channel}"

    async def publish(self, channel: str, message: Dict[str, Any]) -> int:
        """
        Publish message to channel.

        Args:
            channel: Channel name
            message: Message data (must be JSON serializable)

        Returns:
            int: Number of subscribers that received the message

        Raises:
            RedisPubSubError: If publish operation fails
        """
        channel_name = self._make_channel(channel)

        with logfire.span("Redis Publish", channel=channel_name):
            try:
                # Add metadata to message
                enriched_message = {
                    **message,
                    "_timestamp": datetime.utcnow().isoformat(),
                    "_channel": channel,
                    "_source": "machina-registry"
                }

                serialized = json.dumps(enriched_message, default=str)
                result = await self.redis.publish(channel_name, serialized)

                logfire.info(
                    "Message published",
                    channel=channel_name,
                    subscribers=result,
                    message_size=len(serialized)
                )

                return result

            except (TypeError, ValueError) as e:
                logfire.error("Message serialization failed", channel=channel_name, error=str(e))
                raise RedisPubSubError(f"Failed to serialize message for channel {channel}: {str(e)}")

            except RedisError as e:
                logfire.error("Redis publish operation failed", channel=channel_name, error=str(e))
                raise RedisPubSubError(f"Failed to publish to channel {channel}: {str(e)}")

    async def subscribe(self, *channels: str):
        """
        Subscribe to channels.

        Args:
            *channels: Channel names to subscribe to

        Raises:
            RedisPubSubError: If subscribe operation fails
        """
        if not self.pubsub:
            self.pubsub = self.redis.pubsub()

        channel_names = [self._make_channel(channel) for channel in channels]

        with logfire.span("Redis Subscribe", channels=channel_names):
            try:
                await self.pubsub.subscribe(*channel_names)
                self.subscribed_channels.update(channel_names)

                logfire.info("Subscribed to channels", channels=channel_names)

            except RedisError as e:
                logfire.error("Redis subscribe operation failed", channels=channel_names, error=str(e))
                raise RedisPubSubError(f"Failed to subscribe to channels: {str(e)}")

    async def unsubscribe(self, *channels: str):
        """
        Unsubscribe from channels.

        Args:
            *channels: Channel names to unsubscribe from
        """
        if not self.pubsub:
            return

        channel_names = [self._make_channel(channel) for channel in channels]

        try:
            await self.pubsub.unsubscribe(*channel_names)
            self.subscribed_channels.difference_update(channel_names)

            logfire.info("Unsubscribed from channels", channels=channel_names)

        except RedisError as e:
            logfire.error("Redis unsubscribe operation failed", channels=channel_names, error=str(e))

    async def get_message(self, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """
        Get message from subscribed channels.

        Args:
            timeout: Timeout in seconds (None for blocking)

        Returns:
            Dict containing message data or None if timeout

        Raises:
            RedisPubSubError: If not subscribed to any channels
        """
        if not self.pubsub:
            raise RedisPubSubError("Not subscribed to any channels")

        try:
            message = await self.pubsub.get_message(ignore_subscribe_messages=True, timeout=timeout)

            if message and message.get("type") == "message":
                try:
                    data = json.loads(message["data"])
                    logfire.info(
                        "Message received",
                        channel=message["channel"],
                        timestamp=data.get("_timestamp")
                    )
                    return data
                except json.JSONDecodeError as e:
                    logfire.error("Message deserialization failed", error=str(e), raw_data=message["data"])
                    return None

            return None

        except RedisError as e:
            logfire.error("Redis get message operation failed", error=str(e))
            raise RedisPubSubError(f"Failed to get message: {str(e)}")

    async def listen(
        self,
        callback: Callable[[str, Dict[str, Any]], Awaitable[None]],
        error_handler: Optional[Callable[[Exception], Awaitable[None]]] = None
    ):
        """
        Listen for messages and execute callback.

        Args:
            callback: Async function to handle messages (channel, data)
            error_handler: Optional async function to handle errors
        """
        if not self.pubsub:
            raise RedisPubSubError("Not subscribed to any channels")

        logfire.info("Starting message listener", channels=list(self.subscribed_channels))

        try:
            while True:
                try:
                    message = await self.get_message(timeout=1.0)
                    if message:
                        channel = message.get("_channel", "unknown")
                        await callback(channel, message)

                except asyncio.TimeoutError:
                    # Normal timeout, continue listening
                    continue

                except Exception as e:
                    logfire.error("Error in message callback", error=str(e))
                    if error_handler:
                        await error_handler(e)
                    else:
                        # Re-raise if no error handler provided
                        raise

        except asyncio.CancelledError:
            logfire.info("Message listener cancelled")
            raise
        except Exception as e:
            logfire.error("Message listener failed", error=str(e))
            raise RedisPubSubError(f"Message listener failed: {str(e)}")

    async def close(self):
        """Close pub/sub connection."""
        if self.pubsub:
            try:
                await self.pubsub.aclose()
                self.pubsub = None
                self.subscribed_channels.clear()
                logfire.info("Pub/sub connection closed")
            except Exception as e:
                logfire.error("Error closing pub/sub connection", error=str(e))


# Convenience functions for getting configured instances
async def get_cache(prefix: str = None) -> RedisCache:
    """
    Get configured Redis cache instance.

    Args:
        prefix: Optional custom prefix

    Returns:
        RedisCache: Configured cache instance
    """
    redis = await get_redis()
    return RedisCache(redis, prefix)


async def get_pubsub(channel_prefix: str = None) -> RedisPubSub:
    """
    Get configured Redis pub/sub instance.

    Args:
        channel_prefix: Optional custom channel prefix

    Returns:
        RedisPubSub: Configured pub/sub instance
    """
    redis = await get_redis()
    return RedisPubSub(redis, channel_prefix)


# Health check function
async def redis_health_check() -> Dict[str, Any]:
    """
    Comprehensive Redis health check.

    Returns:
        Dict containing health status and metrics
    """
    try:
        redis = await get_redis()

        # Basic ping test
        start_time = datetime.utcnow()
        await redis.ping()
        ping_time = (datetime.utcnow() - start_time).total_seconds() * 1000

        # Get Redis info
        info = await redis.info()

        # Test cache operations
        test_key = "health_check_test"
        cache = await get_cache()
        await cache.set(test_key, {"test": True}, expire=60)
        test_value = await cache.get(test_key)
        await cache.delete(test_key)

        return {
            "status": "healthy",
            "ping_ms": round(ping_time, 2),
            "redis_version": info.get("redis_version"),
            "connected_clients": info.get("connected_clients"),
            "used_memory_human": info.get("used_memory_human"),
            "cache_operations": "working" if test_value else "failed",
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
