"""
Cache Service for Machina Registry Service

This module provides high-level caching operations specifically designed for
the Machina Registry Service, implementing DevQ.ai patterns with proper
error handling, type safety, and observability.

Features:
- Service registry data caching with intelligent invalidation
- Health check result caching with TTL management
- Configuration caching with change detection
- Statistics and metrics caching
- Bulk operations for improved performance
- Cache warming strategies for critical data
- Rate limiting utilities using Redis
- Session management helpers
- Function result caching
- Domain-specific cache operations for MCP servers and tools
- Metrics and monitoring utilities
"""

import asyncio
import functools
import hashlib
import json
import time
from typing import Any, Callable, Dict, List, Optional, Union, TypeVar, Awaitable
from datetime import datetime, timedelta

import logfire
from pydantic import BaseModel

from ..core.cache import CacheService, CacheKeyType, PubSubChannel, RedisMessage
from ..core.config import Settings

# Type variables for generic decorators
F = TypeVar('F', bound=Callable[..., Awaitable[Any]])


class CacheDecoratorConfig(BaseModel):
    """Configuration for cache decorators."""
    ttl: int = 3600  # Default 1 hour
    key_prefix: str = ""
    serialize_args: bool = True
    ignore_self: bool = True  # Ignore 'self' parameter in key generation
    ignore_kwargs: List[str] = []  # Kwargs to ignore in key generation


class RateLimitConfig(BaseModel):
    """Rate limiting configuration."""
    max_requests: int = 100
    window_seconds: int = 3600  # 1 hour window
    block_duration: int = 300   # 5 minute block


class MCPServerCacheData(BaseModel):
    """Cached MCP server data structure."""
    server_id: str
    name: str
    version: str
    status: str
    tools: List[Dict[str, Any]]
    last_health_check: datetime
    performance_metrics: Dict[str, float]
    configuration: Dict[str, Any]


class CacheUtilities:
    """
    High-level cache utilities and domain-specific operations.

    This class provides convenient methods for common caching patterns
    used throughout the Machina Registry Service.
    """

    def __init__(self, cache_service: CacheService):
        """
        Initialize cache utilities.

        Args:
            cache_service: Core Redis cache service instance
        """
        self.cache = cache_service
        self.settings = cache_service.settings
        self.prefix = "registry:"
        self.default_ttl = self.settings.CACHE_TTL

        # TTL configurations for different data types
        self.ttl_config = {
            "service": 3600,           # Service data - 1 hour
            "health": 300,             # Health check results - 5 minutes
            "config": 1800,            # Configuration data - 30 minutes
            "stats": 600,              # Statistics - 10 minutes
            "discovery": 900,          # Service discovery - 15 minutes
            "metadata": 7200,          # Service metadata - 2 hours
        }

    def _get_ttl(self, data_type: str) -> int:
        """Get TTL for specific data type."""
        return self.ttl_config.get(data_type, self.default_ttl)

    # Cache Decorators

    def cached(
        self,
        ttl: int = 3600,
        key_prefix: str = "",
        serialize_args: bool = True,
        ignore_self: bool = True,
        ignore_kwargs: Optional[List[str]] = None
    ):
        """
        Decorator to automatically cache function results.

        Args:
            ttl: Time to live in seconds
            key_prefix: Prefix for cache keys
            serialize_args: Whether to serialize function arguments for key generation
            ignore_self: Whether to ignore 'self' parameter in key generation
            ignore_kwargs: List of kwargs to ignore in key generation

        Usage:
            @cache_utilities.cached(ttl=1800, key_prefix="mcp_server")
            async def get_server_status(self, server_id: str) -> dict:
                # Expensive operation
                return await fetch_server_status(server_id)
        """
        ignore_kwargs = ignore_kwargs or []

        def decorator(func: F) -> F:
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                # Generate cache key from function and arguments
                cache_key = self._generate_function_cache_key(
                    func,
                    args,
                    kwargs,
                    key_prefix,
                    serialize_args,
                    ignore_self,
                    ignore_kwargs
                )

                # Try to get from cache first
                cached_result = await self.cache.get(
                    CacheKeyType.MCP_TOOL,  # Generic key type for function caching
                    cache_key,
                    deserialize=True
                )

                if cached_result is not None:
                    logfire.debug(
                        "Cache hit for function",
                        function=func.__name__,
                        cache_key=cache_key
                    )
                    return cached_result

                # Execute function and cache result
                result = await func(*args, **kwargs)

                # Cache the result
                await self.cache.set(
                    CacheKeyType.MCP_TOOL,
                    cache_key,
                    result,
                    ttl=ttl,
                    serialize=True
                )

                logfire.debug(
                    "Function result cached",
                    function=func.__name__,
                    cache_key=cache_key,
                    ttl=ttl
                )

                return result

            return wrapper
        return decorator

    def _generate_function_cache_key(
        self,
        func: Callable,
        args: tuple,
        kwargs: dict,
        prefix: str,
        serialize_args: bool,
        ignore_self: bool,
        ignore_kwargs: List[str]
    ) -> str:
        """Generate cache key for function call."""
        key_parts = [func.__module__, func.__name__]

        if prefix:
            key_parts.insert(0, prefix)

        if serialize_args:
            # Process args
            processed_args = list(args)
            if ignore_self and processed_args and hasattr(processed_args[0], '__class__'):
                processed_args = processed_args[1:]  # Remove 'self'

            # Process kwargs
            processed_kwargs = {
                k: v for k, v in kwargs.items()
                if k not in ignore_kwargs
            }

            # Create deterministic hash of arguments
            if processed_args or processed_kwargs:
                args_str = json.dumps({
                    'args': processed_args,
                    'kwargs': processed_kwargs
                }, sort_keys=True, default=str)

                args_hash = hashlib.md5(args_str.encode()).hexdigest()[:12]
                key_parts.append(args_hash)

        return ":".join(key_parts)

    # Domain-Specific Cache Operations

    async def cache_mcp_server(
        self,
        server_id: str,
        server_data: MCPServerCacheData,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache MCP server data with structured format.

        Args:
            server_id: Unique server identifier
            server_data: Server data to cache
            ttl: Time to live (uses default if None)

        Returns:
            True if successfully cached
        """
        return await self.cache.set(
            CacheKeyType.MCP_SERVER,
            server_id,
            server_data.model_dump(),
            ttl=ttl or self.settings.CACHE_TTL
        )

    async def get_mcp_server(self, server_id: str) -> Optional[MCPServerCacheData]:
        """
        Retrieve cached MCP server data.

        Args:
            server_id: Unique server identifier

        Returns:
            Cached server data or None if not found
        """
        cached_data = await self.cache.get(
            CacheKeyType.MCP_SERVER,
            server_id,
            deserialize=True
        )

        if cached_data:
            try:
                return MCPServerCacheData(**cached_data)
            except Exception as e:
                logfire.error(
                    "Error deserializing cached MCP server data",
                    server_id=server_id,
                    error=str(e)
                )

        return None

    async def cache_mcp_tool(
        self,
        tool_id: str,
        tool_data: Dict[str, Any],
        server_id: Optional[str] = None,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache MCP tool data.

        Args:
            tool_id: Unique tool identifier
            tool_data: Tool data to cache
            server_id: Optional server ID for namespacing
            ttl: Time to live

        Returns:
            True if successfully cached
        """
        cache_key = f"{server_id}:{tool_id}" if server_id else tool_id

        return await self.cache.set(
            CacheKeyType.MCP_TOOL,
            cache_key,
            tool_data,
            ttl=ttl or self.settings.CACHE_TTL
        )

    async def get_mcp_tool(
        self,
        tool_id: str,
        server_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached MCP tool data.

        Args:
            tool_id: Unique tool identifier
            server_id: Optional server ID for namespacing

        Returns:
            Cached tool data or None if not found
        """
        cache_key = f"{server_id}:{tool_id}" if server_id else tool_id

        return await self.cache.get(
            CacheKeyType.MCP_TOOL,
            cache_key,
            deserialize=True
        )

    # Rate Limiting Utilities

    async def is_rate_limited(
        self,
        identifier: str,
        config: RateLimitConfig
    ) -> tuple[bool, Dict[str, Any]]:
        """
        Check if identifier is rate limited.

        Args:
            identifier: Unique identifier (user ID, IP address, etc.)
            config: Rate limiting configuration

        Returns:
            Tuple of (is_limited, rate_limit_info)
        """
        current_time = int(time.time())
        window_start = current_time - config.window_seconds

        # Check if currently blocked
        block_key = f"rate_limit_block:{identifier}"
        is_blocked = await self.cache.exists(
            CacheKeyType.API_RATE_LIMIT,
            block_key
        )

        if is_blocked:
            block_ttl = await self.cache._redis.ttl(
                self.cache._build_cache_key(CacheKeyType.API_RATE_LIMIT, block_key)
            )

            return True, {
                "limited": True,
                "reason": "blocked",
                "reset_time": current_time + block_ttl,
                "retry_after": block_ttl
            }

        # Count requests in current window
        requests_key = f"rate_limit_requests:{identifier}:{window_start}"
        current_requests = await self.cache.get(
            CacheKeyType.API_RATE_LIMIT,
            requests_key,
            deserialize=False
        )

        current_count = int(current_requests) if current_requests else 0

        if current_count >= config.max_requests:
            # Apply block
            await self.cache.set(
                CacheKeyType.API_RATE_LIMIT,
                block_key,
                "blocked",
                ttl=config.block_duration,
                serialize=False
            )

            logfire.warning(
                "Rate limit exceeded, applying block",
                identifier=identifier,
                requests=current_count,
                max_requests=config.max_requests
            )

            return True, {
                "limited": True,
                "reason": "rate_exceeded",
                "requests": current_count,
                "max_requests": config.max_requests,
                "reset_time": current_time + config.block_duration,
                "retry_after": config.block_duration
            }

        # Increment request counter
        await self.cache.set(
            CacheKeyType.API_RATE_LIMIT,
            requests_key,
            current_count + 1,
            ttl=config.window_seconds,
            serialize=False
        )

        return False, {
            "limited": False,
            "requests": current_count + 1,
            "max_requests": config.max_requests,
            "window_seconds": config.window_seconds,
            "reset_time": current_time + config.window_seconds
        }

    # Session Management

    async def create_user_session(
        self,
        user_id: str,
        session_data: Dict[str, Any],
        ttl: int = 3600
    ) -> str:
        """
        Create user session with automatic cleanup.

        Args:
            user_id: User identifier
            session_data: Session data to store
            ttl: Session time to live in seconds

        Returns:
            Session ID
        """
        session_id = hashlib.sha256(
            f"{user_id}:{time.time()}:{id(session_data)}".encode()
        ).hexdigest()[:32]

        session_info = {
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "last_accessed": datetime.utcnow().isoformat(),
            "data": session_data
        }

        await self.cache.set(
            CacheKeyType.USER_SESSION,
            session_id,
            session_info,
            ttl=ttl
        )

        logfire.info(
            "User session created",
            user_id=user_id,
            session_id=session_id,
            ttl=ttl
        )

        return session_id

    async def get_user_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve user session and update last accessed time.

        Args:
            session_id: Session identifier

        Returns:
            Session data or None if not found/expired
        """
        session_info = await self.cache.get(
            CacheKeyType.USER_SESSION,
            session_id,
            deserialize=True
        )

        if session_info:
            # Update last accessed time
            session_info["last_accessed"] = datetime.utcnow().isoformat()
            await self.cache.set(
                CacheKeyType.USER_SESSION,
                session_id,
                session_info,
                ttl=3600  # Reset TTL
            )

        return session_info

    async def delete_user_session(self, session_id: str) -> bool:
        """Delete user session."""
        return await self.cache.delete(CacheKeyType.USER_SESSION, session_id)

    # Cache Management Operations

    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate cache entries matching pattern.

        Args:
            pattern: Cache key pattern with wildcards

        Returns:
            Number of entries invalidated
        """
        with logfire.span("Cache Invalidate Pattern", pattern=pattern):
            try:
                # This is a simplified implementation
                # In production, you might want to use Redis SCAN for better performance
                keys = await self.cache._redis.keys(f"{self.cache.settings.CACHE_PREFIX}{pattern}")

                if keys:
                    deleted = await self.cache._redis.delete(*keys)
                    logfire.info("Cache pattern invalidated", pattern=pattern, count=deleted)
                    return deleted

                return 0

            except Exception as e:
                logfire.error("Failed to invalidate cache pattern", pattern=pattern, error=str(e))
                return 0

    async def invalidate_service_related(self, service_id: str) -> int:
        """
        Invalidate all cache entries related to a service.

        Args:
            service_id: Service ID

        Returns:
            Number of entries invalidated
        """
        with logfire.span("Cache Invalidate Service Related", service_id=service_id):
            patterns = [
                f"service:{service_id}",
                f"health:{service_id}",
                f"config:service:{service_id}:*",
                f"stats:service:{service_id}:*"
            ]

            total_invalidated = 0
            for pattern in patterns:
                try:
                    if "*" in pattern:
                        count = await self.invalidate_pattern(pattern)
                    else:
                        count = 1 if await self.cache.delete(CacheKeyType.REGISTRY_STATUS, pattern.replace(self.prefix, "")) else 0
                    total_invalidated += count
                except Exception as e:
                    logfire.error("Failed to invalidate pattern", pattern=pattern, error=str(e))

            logfire.info("Service-related cache invalidated", service_id=service_id, total_invalidated=total_invalidated)

            return total_invalidated

    async def warm_cache(self, service_ids: List[str]) -> Dict[str, bool]:
        """
        Warm cache for critical services.

        Args:
            service_ids: List of service IDs to warm

        Returns:
            Dictionary mapping service IDs to success status
        """
        with logfire.span("Cache Warm", count=len(service_ids)):
            # This would typically fetch fresh data and cache it
            # For now, we'll just check what's already cached
            results = {}

            for service_id in service_ids:
                try:
                    exists = await self.cache.exists(CacheKeyType.MCP_SERVER, service_id)
                    results[service_id] = exists

                    if not exists:
                        logfire.info("Service cache miss during warm", service_id=service_id)

                except Exception as e:
                    logfire.error("Cache warm failed for service", service_id=service_id, error=str(e))
                    results[service_id] = False

            warm_count = sum(1 for v in results.values() if v)
            logfire.info("Cache warm completed", total=len(service_ids), warmed=warm_count)

            return results

    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache usage statistics.

        Returns:
            Dictionary containing cache statistics
        """
        with logfire.span("Cache Get Stats"):
            try:
                # Count keys by type
                stats = {
                    "service_count": 0,
                    "health_count": 0,
                    "config_count": 0,
                    "discovery_count": 0,
                    "stats_count": 0,
                    "total_count": 0,
                    "timestamp": datetime.utcnow().isoformat()
                }

                # This is a simplified version - in production you might want
                # to use Redis SCAN for better performance
                patterns = {
                    "service_count": "service:*",
                    "health_count": "health:*",
                    "config_count": "config:*",
                    "discovery_count": "discovery:*",
                    "stats_count": "stats:*"
                }

                for stat_key, pattern in patterns.items():
                    try:
                        keys = await self.cache._redis.keys(f"{self.cache.settings.CACHE_PREFIX}{pattern}")
                        count = len(keys) if keys else 0
                        stats[stat_key] = count
                        stats["total_count"] += count
                    except Exception as e:
                        logfire.warning("Failed to count cache keys", pattern=pattern, error=str(e))
                        stats[stat_key] = -1

                return stats

            except Exception as e:
                logfire.error("Failed to get cache statistics", error=str(e))
                return {
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }

    # Pub/Sub Utilities

    async def notify_mcp_server_update(
        self,
        server_id: str,
        update_type: str,
        data: Dict[str, Any]
    ) -> int:
        """
        Notify subscribers about MCP server updates.

        Args:
            server_id: Server identifier
            update_type: Type of update (status_change, config_update, etc.)
            data: Update data

        Returns:
            Number of subscribers notified
        """
        return await self.cache.publish(
            PubSubChannel.MCP_SERVER_UPDATES,
            update_type,
            {
                "server_id": server_id,
                "update_type": update_type,
                "data": data,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    async def notify_registry_event(
        self,
        event_type: str,
        data: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> int:
        """
        Notify subscribers about registry events.

        Args:
            event_type: Type of event
            data: Event data
            correlation_id: Optional correlation ID

        Returns:
            Number of subscribers notified
        """
        return await self.cache.publish(
            PubSubChannel.REGISTRY_EVENTS,
            event_type,
            data,
            correlation_id=correlation_id
        )

    # Monitoring and Metrics

    async def get_cache_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive cache metrics and statistics.

        Returns:
            Dictionary with cache metrics
        """
        stats = self.cache.get_stats()
        health = await self.cache.health_check()

        metrics = {
            "cache_stats": stats.model_dump(),
            "health_check": health,
            "redis_info": health.get("redis_info", {}),
            "performance": {
                "hit_rate": (
                    stats.cache_hits / (stats.cache_hits + stats.cache_misses)
                    if (stats.cache_hits + stats.cache_misses) > 0 else 0
                ),
                "success_rate": (
                    stats.successful_operations / stats.total_operations
                    if stats.total_operations > 0 else 0
                ),
                "average_response_time_ms": stats.average_response_time * 1000
            },
            "collected_at": datetime.utcnow().isoformat()
        }

        return metrics

    async def clear_cache_namespace(
        self,
        key_type: CacheKeyType,
        pattern: Optional[str] = None
    ) -> int:
        """
        Clear all keys in a cache namespace.

        Args:
            key_type: Type of cache keys to clear
            pattern: Optional pattern to match (uses * if None)

        Returns:
            Number of keys deleted
        """
        search_pattern = self.cache._build_cache_key(
            key_type,
            pattern or "*"
        )

        keys = await self.cache._redis.keys(search_pattern)

        if keys:
            deleted = await self.cache._redis.delete(*keys)
            logfire.info(
                "Cache namespace cleared",
                key_type=key_type.value,
                pattern=pattern,
                keys_deleted=deleted
            )
            return deleted

        return 0


# Global cache utilities instance
_cache_utilities: Optional[CacheUtilities] = None


async def get_cache_utilities(cache_service: Optional[CacheService] = None) -> CacheUtilities:
    """
    Get or create the global cache utilities instance.

    Args:
        cache_service: Optional cache service instance

    Returns:
        CacheUtilities instance
    """
    global _cache_utilities

    if _cache_utilities is None:
        if cache_service is None:
            from ..core.cache import get_cache_service
            cache_service = await get_cache_service()

        _cache_utilities = CacheUtilities(cache_service)

    return _cache_utilities
