"""
Redis Cache and Pub/Sub Service Implementation

This module provides comprehensive Redis integration for the Machina Registry Service,
implementing DevQ.ai's standard caching and messaging patterns with async support,
structured logging, and robust error handling.

Features:
- Async Redis connection management with connection pooling
- Cache operations with TTL support and serialization
- Pub/Sub messaging system for real-time updates
- Health monitoring and connection recovery
- Structured logging with Logfire integration
- Type-safe operations with Pydantic models
- Circuit breaker pattern for resilience
"""

import json
import asyncio
import time
from typing import Any, Dict, List, Optional, Callable, Union, AsyncGenerator
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from enum import Enum

import redis.asyncio as redis
from redis.asyncio import Redis, ConnectionPool
from redis.exceptions import RedisError, ConnectionError, TimeoutError
import logfire
from pydantic import BaseModel

from .config import Settings


class CacheKeyType(str, Enum):
    """Enumeration of cache key types for consistent naming."""
    MCP_SERVER = "mcp:server"
    MCP_TOOL = "mcp:tool"
    REGISTRY_STATUS = "registry:status"
    USER_SESSION = "user:session"
    API_RATE_LIMIT = "api:rate_limit"
    HEALTH_CHECK = "health:check"


class CacheOperation(str, Enum):
    """Cache operation types for logging and monitoring."""
    GET = "get"
    SET = "set"
    DELETE = "delete"
    EXISTS = "exists"
    EXPIRE = "expire"
    PUBLISH = "publish"
    SUBSCRIBE = "subscribe"


class PubSubChannel(str, Enum):
    """Pub/Sub channel names for consistent messaging."""
    MCP_SERVER_UPDATES = "mcp:server:updates"
    REGISTRY_EVENTS = "registry:events"
    SYSTEM_ALERTS = "system:alerts"
    USER_NOTIFICATIONS = "user:notifications"


class CacheStats(BaseModel):
    """Cache statistics model for monitoring."""
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    average_response_time: float = 0.0
    last_operation: Optional[datetime] = None
    connection_status: str = "unknown"


class RedisMessage(BaseModel):
    """Standardized Redis pub/sub message format."""
    channel: str
    message_type: str
    data: Dict[str, Any]
    timestamp: datetime = datetime.utcnow()
    source: str = "machina-registry"
    correlation_id: Optional[str] = None


class CacheService:
    """
    Comprehensive Redis cache and pub/sub service.

    This service provides high-level cache operations with automatic serialization,
    connection management, health monitoring, and pub/sub messaging capabilities.
    """

    def __init__(self, settings: Settings):
        """
        Initialize Redis cache service.

        Args:
            settings: Application settings containing Redis configuration
        """
        self.settings = settings
        self._redis: Optional[Redis] = None
        self._connection_pool: Optional[ConnectionPool] = None
        self._pubsub_clients: Dict[str, Redis] = {}
        self._subscribers: Dict[str, asyncio.Task] = {}
        self._stats = CacheStats()
        self._circuit_breaker_open = False
        self._last_failure_time: Optional[float] = None
        self._failure_count = 0
        self._max_failures = 3
        self._recovery_timeout = 30  # seconds

    async def initialize(self) -> None:
        """
        Initialize Redis connection and connection pool.

        Creates the connection pool and establishes the primary Redis connection
        with proper error handling and logging.
        """
        try:
            with logfire.span("Redis initialization", service="cache"):
                # Create connection pool
                self._connection_pool = ConnectionPool.from_url(
                    self.settings.REDIS_URI,
                    max_connections=20,
                    retry_on_timeout=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    health_check_interval=30,
                )

                # Create Redis client
                self._redis = Redis(
                    connection_pool=self._connection_pool,
                    decode_responses=True,
                    protocol=3,
                )

                # Test connection
                await self._redis.ping()

                self._stats.connection_status = "connected"
                self._circuit_breaker_open = False

                logfire.info(
                    "Redis connection established",
                    redis_uri=self.settings.REDIS_URI,
                    pool_size=20
                )

        except Exception as e:
            self._stats.connection_status = "failed"
            self._circuit_breaker_open = True
            logfire.error("Redis initialization failed", error=str(e))
            raise

    async def close(self) -> None:
        """Clean up Redis connections and resources."""
        try:
            with logfire.span("Redis cleanup", service="cache"):
                # Stop all subscribers
                for task in self._subscribers.values():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

                # Close pub/sub clients
                for client in self._pubsub_clients.values():
                    await client.close()

                # Close main Redis connection
                if self._redis:
                    await self._redis.close()

                # Close connection pool
                if self._connection_pool:
                    await self._connection_pool.disconnect()

                self._stats.connection_status = "disconnected"
                logfire.info("Redis connections closed")

        except Exception as e:
            logfire.error("Error during Redis cleanup", error=str(e))

    def _is_circuit_breaker_open(self) -> bool:
        """Check if circuit breaker should prevent operations."""
        if not self._circuit_breaker_open:
            return False

        # Check if recovery timeout has passed
        if (self._last_failure_time and
            time.time() - self._last_failure_time > self._recovery_timeout):
            self._circuit_breaker_open = False
            self._failure_count = 0
            logfire.info("Circuit breaker reset - attempting Redis reconnection")
            return False

        return True

    def _record_operation(self, operation: CacheOperation, success: bool,
                         response_time: float = 0.0) -> None:
        """Record operation statistics for monitoring."""
        self._stats.total_operations += 1
        self._stats.last_operation = datetime.utcnow()

        if success:
            self._stats.successful_operations += 1
            # Reset failure count on success
            self._failure_count = 0
        else:
            self._stats.failed_operations += 1
            self._failure_count += 1
            self._last_failure_time = time.time()

            # Open circuit breaker if too many failures
            if self._failure_count >= self._max_failures:
                self._circuit_breaker_open = True
                logfire.warning(
                    "Circuit breaker opened due to Redis failures",
                    failure_count=self._failure_count
                )

        # Update average response time
        if response_time > 0:
            total_time = (self._stats.average_response_time *
                         (self._stats.total_operations - 1) + response_time)
            self._stats.average_response_time = total_time / self._stats.total_operations

    def _build_cache_key(self, key_type: Union[CacheKeyType, str], identifier: str,
                        suffix: Optional[str] = None) -> str:
        """
        Build standardized cache key with prefix and structure.

        Args:
            key_type: Type of cache key (enum or string)
            identifier: Unique identifier
            suffix: Optional suffix for the key

        Returns:
            Formatted cache key string
        """
        # Handle both enum and string inputs
        key_type_str = key_type.value if hasattr(key_type, 'value') else str(key_type)
        key_parts = [self.settings.CACHE_PREFIX, key_type_str, identifier]
        if suffix:
            key_parts.append(suffix)
        return ":".join(key_parts)

    async def _execute_with_monitoring(self, operation: CacheOperation,
                                     func: Callable, *args, **kwargs) -> Any:
        """
        Execute Redis operation with monitoring and error handling.

        Args:
            operation: Type of cache operation
            func: Redis operation function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Operation result or None if circuit breaker is open

        Raises:
            RedisError: If operation fails and circuit breaker is closed
        """
        if self._is_circuit_breaker_open():
            logfire.warning(
                "Redis operation blocked by circuit breaker",
                operation=operation.value
            )
            return None

        start_time = time.time()

        try:
            with logfire.span(f"Redis {operation.value}", service="cache"):
                result = await func(*args, **kwargs)

                response_time = time.time() - start_time
                self._record_operation(operation, True, response_time)

                logfire.debug(
                    f"Redis {operation.value} successful",
                    response_time=response_time,
                    args_count=len(args),
                    kwargs_count=len(kwargs)
                )

                return result

        except (ConnectionError, TimeoutError) as e:
            response_time = time.time() - start_time
            self._record_operation(operation, False, response_time)

            logfire.error(
                f"Redis {operation.value} failed",
                error=str(e),
                response_time=response_time,
                operation=operation.value
            )

            raise

    # Cache Operations

    async def get(self, key_type: CacheKeyType, identifier: str,
                  suffix: Optional[str] = None,
                  deserialize: bool = True) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key_type: Type of cache key
            identifier: Unique identifier
            suffix: Optional key suffix
            deserialize: Whether to deserialize JSON values

        Returns:
            Cached value or None if not found
        """
        cache_key = self._build_cache_key(key_type, identifier, suffix)

        result = await self._execute_with_monitoring(
            CacheOperation.GET,
            self._redis.get,
            cache_key
        )

        if result is None:
            self._stats.cache_misses += 1
            return None

        self._stats.cache_hits += 1

        if deserialize and isinstance(result, str):
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                return result

        return result

    async def set(self, key_type: CacheKeyType, identifier: str,
                  value: Any, ttl: Optional[int] = None,
                  suffix: Optional[str] = None,
                  serialize: bool = True) -> bool:
        """
        Set value in cache.

        Args:
            key_type: Type of cache key
            identifier: Unique identifier
            value: Value to cache
            ttl: Time to live in seconds (uses default if None)
            suffix: Optional key suffix
            serialize: Whether to serialize value as JSON

        Returns:
            True if successful, False otherwise
        """
        cache_key = self._build_cache_key(key_type, identifier, suffix)
        ttl = ttl or self.settings.CACHE_TTL

        if serialize and not isinstance(value, str):
            try:
                value = json.dumps(value, default=str)
            except (TypeError, ValueError) as e:
                logfire.error(f"Failed to serialize cache value", error=str(e))
                return False

        result = await self._execute_with_monitoring(
            CacheOperation.SET,
            self._redis.setex,
            cache_key,
            ttl,
            value
        )

        return result is not None

    async def delete(self, key_type: CacheKeyType, identifier: str,
                    suffix: Optional[str] = None) -> bool:
        """
        Delete value from cache.

        Args:
            key_type: Type of cache key
            identifier: Unique identifier
            suffix: Optional key suffix

        Returns:
            True if key was deleted, False if key didn't exist
        """
        cache_key = self._build_cache_key(key_type, identifier, suffix)

        result = await self._execute_with_monitoring(
            CacheOperation.DELETE,
            self._redis.delete,
            cache_key
        )

        return result > 0

    async def exists(self, key_type: CacheKeyType, identifier: str,
                    suffix: Optional[str] = None) -> bool:
        """
        Check if key exists in cache.

        Args:
            key_type: Type of cache key
            identifier: Unique identifier
            suffix: Optional key suffix

        Returns:
            True if key exists, False otherwise
        """
        cache_key = self._build_cache_key(key_type, identifier, suffix)

        result = await self._execute_with_monitoring(
            CacheOperation.EXISTS,
            self._redis.exists,
            cache_key
        )

        return result > 0

    async def expire(self, key_type: CacheKeyType, identifier: str,
                    ttl: int, suffix: Optional[str] = None) -> bool:
        """
        Set expiration time for existing key.

        Args:
            key_type: Type of cache key
            identifier: Unique identifier
            ttl: Time to live in seconds
            suffix: Optional key suffix

        Returns:
            True if expiration was set, False if key doesn't exist
        """
        cache_key = self._build_cache_key(key_type, identifier, suffix)

        result = await self._execute_with_monitoring(
            CacheOperation.EXPIRE,
            self._redis.expire,
            cache_key,
            ttl
        )

        return result

    async def get_multiple(self, keys: List[tuple]) -> Dict[str, Any]:
        """
        Get multiple values from cache in a single operation.

        Args:
            keys: List of (key_type, identifier, suffix) tuples

        Returns:
            Dictionary mapping cache keys to values
        """
        if not keys:
            return {}

        cache_keys = [
            self._build_cache_key(key_type, identifier, suffix)
            for key_type, identifier, suffix in keys
        ]

        results = await self._execute_with_monitoring(
            CacheOperation.GET,
            self._redis.mget,
            cache_keys
        )

        if not results:
            return {}

        # Build result dictionary with deserialization
        result_dict = {}
        for i, (cache_key, value) in enumerate(zip(cache_keys, results)):
            if value is not None:
                try:
                    result_dict[cache_key] = json.loads(value)
                    self._stats.cache_hits += 1
                except json.JSONDecodeError:
                    result_dict[cache_key] = value
                    self._stats.cache_hits += 1
            else:
                self._stats.cache_misses += 1

        return result_dict

    # Pub/Sub Operations

    async def publish(self, channel: PubSubChannel, message_type: str,
                     data: Dict[str, Any],
                     correlation_id: Optional[str] = None) -> int:
        """
        Publish message to Redis pub/sub channel.

        Args:
            channel: Pub/sub channel
            message_type: Type of the message
            data: Message data
            correlation_id: Optional correlation ID for tracking

        Returns:
            Number of subscribers that received the message
        """
        message = RedisMessage(
            channel=channel.value,
            message_type=message_type,
            data=data,
            correlation_id=correlation_id
        )

        message_json = message.model_dump_json()

        result = await self._execute_with_monitoring(
            CacheOperation.PUBLISH,
            self._redis.publish,
            channel.value,
            message_json
        )

        logfire.info(
            "Message published",
            channel=channel.value,
            message_type=message_type,
            subscribers=result,
            correlation_id=correlation_id
        )

        return result or 0

    async def subscribe(self, channel: PubSubChannel,
                       handler: Callable[[RedisMessage], None]) -> str:
        """
        Subscribe to Redis pub/sub channel with message handler.

        Args:
            channel: Pub/sub channel to subscribe to
            handler: Async function to handle received messages

        Returns:
            Subscription ID for managing the subscription
        """
        subscription_id = f"{channel.value}:{int(time.time())}"

        # Create dedicated Redis client for this subscription
        pubsub_client = Redis(
            connection_pool=self._connection_pool,
            decode_responses=True
        )

        self._pubsub_clients[subscription_id] = pubsub_client

        async def subscription_handler():
            """Handle subscription lifecycle and message processing."""
            try:
                pubsub = pubsub_client.pubsub()
                await pubsub.subscribe(channel.value)

                logfire.info(
                    "Subscribed to channel",
                    channel=channel.value,
                    subscription_id=subscription_id
                )

                async for message in pubsub.listen():
                    if message["type"] == "message":
                        try:
                            # Parse message
                            redis_message = RedisMessage.model_validate_json(
                                message["data"]
                            )

                            # Call handler
                            await handler(redis_message)

                            logfire.debug(
                                "Message processed",
                                channel=channel.value,
                                message_type=redis_message.message_type,
                                subscription_id=subscription_id
                            )

                        except Exception as e:
                            logfire.error(
                                "Error processing pub/sub message",
                                error=str(e),
                                channel=channel.value,
                                subscription_id=subscription_id
                            )

            except asyncio.CancelledError:
                logfire.info(
                    "Subscription cancelled",
                    channel=channel.value,
                    subscription_id=subscription_id
                )
            except Exception as e:
                logfire.error(
                    "Subscription error",
                    error=str(e),
                    channel=channel.value,
                    subscription_id=subscription_id
                )
            finally:
                try:
                    await pubsub.close()
                except:
                    pass

        # Start subscription task
        task = asyncio.create_task(subscription_handler())
        self._subscribers[subscription_id] = task

        return subscription_id

    async def unsubscribe(self, subscription_id: str) -> bool:
        """
        Unsubscribe from a pub/sub channel.

        Args:
            subscription_id: Subscription ID returned from subscribe()

        Returns:
            True if successfully unsubscribed, False otherwise
        """
        if subscription_id not in self._subscribers:
            return False

        try:
            # Cancel subscription task
            task = self._subscribers.pop(subscription_id)
            task.cancel()

            try:
                await task
            except asyncio.CancelledError:
                pass

            # Close pub/sub client
            if subscription_id in self._pubsub_clients:
                client = self._pubsub_clients.pop(subscription_id)
                await client.close()

            logfire.info("Unsubscribed", subscription_id=subscription_id)
            return True

        except Exception as e:
            logfire.error(
                "Error during unsubscribe",
                error=str(e),
                subscription_id=subscription_id
            )
            return False

    # Health and Monitoring

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive Redis health check.

        Returns:
            Health check results with connection status and statistics
        """
        health_data = {
            "status": "unknown",
            "connection": False,
            "latency_ms": None,
            "circuit_breaker_open": self._circuit_breaker_open,
            "stats": self._stats.model_dump(),
            "timestamp": datetime.utcnow().isoformat()
        }

        try:
            start_time = time.time()

            # Test basic connectivity
            await self._redis.ping()

            latency = (time.time() - start_time) * 1000
            health_data.update({
                "status": "healthy",
                "connection": True,
                "latency_ms": round(latency, 2)
            })

            # Get Redis info if available
            try:
                info = await self._redis.info()
                health_data["redis_info"] = {
                    "version": info.get("redis_version"),
                    "uptime_seconds": info.get("uptime_in_seconds"),
                    "connected_clients": info.get("connected_clients"),
                    "used_memory": info.get("used_memory"),
                    "keyspace_hits": info.get("keyspace_hits"),
                    "keyspace_misses": info.get("keyspace_misses")
                }
            except Exception:
                # Redis info not critical for health check
                pass

        except Exception as e:
            health_data.update({
                "status": "unhealthy",
                "connection": False,
                "error": str(e)
            })

        return health_data

    def get_stats(self) -> CacheStats:
        """Get current cache statistics."""
        return self._stats.model_copy()

    async def clear_stats(self) -> None:
        """Reset cache statistics."""
        self._stats = CacheStats()
        self._stats.connection_status = "connected" if self._redis else "disconnected"

    @asynccontextmanager
    async def batch_operations(self):
        """
        Context manager for batching Redis operations using pipeline.

        Usage:
            async with cache_service.batch_operations() as pipe:
                await pipe.set(...)
                await pipe.get(...)
                results = await pipe.execute()
        """
        if self._is_circuit_breaker_open():
            raise RedisError("Circuit breaker is open")

        pipe = self._redis.pipeline()
        try:
            yield pipe
        finally:
            # Pipeline is automatically executed when exiting context
            pass


# Global cache service instance
_cache_service: Optional[CacheService] = None


async def get_cache_service(settings: Optional[Settings] = None) -> CacheService:
    """
    Get or create the global cache service instance.

    Args:
        settings: Optional settings to use for initialization

    Returns:
        CacheService instance
    """
    global _cache_service

    if _cache_service is None:
        from .config import get_settings
        settings = settings or get_settings()
        _cache_service = CacheService(settings)
        await _cache_service.initialize()

    return _cache_service


async def close_cache_service() -> None:
    """Close the global cache service instance."""
    global _cache_service

    if _cache_service:
        await _cache_service.close()
        _cache_service = None
