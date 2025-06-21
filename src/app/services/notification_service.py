"""
Notification Service for Machina Registry Service

This module provides pub/sub messaging functionality for real-time notifications
and event distribution across the Machina Registry Service, implementing DevQ.ai
patterns with proper error handling, type safety, and observability.

Features:
- Real-time event publishing and subscription
- Service discovery notifications
- Health status change notifications
- Configuration update notifications
- Error and alert notifications
- Message routing and filtering
- Connection management and retry logic
- Metrics and monitoring for message flow
"""

import asyncio
import json
from typing import Any, Callable, Dict, List, Optional, Set, Union, Awaitable
from datetime import datetime
from enum import Enum
import uuid

import logfire
from pydantic import BaseModel

from app.core.redis import get_pubsub, RedisPubSub, RedisPubSubError
from app.core.config import settings


class NotificationType(str, Enum):
    """Types of notifications that can be sent."""
    SERVICE_REGISTERED = "service_registered"
    SERVICE_UNREGISTERED = "service_unregistered"
    SERVICE_STATUS_CHANGED = "service_status_changed"
    HEALTH_CHECK_FAILED = "health_check_failed"
    HEALTH_CHECK_RECOVERED = "health_check_recovered"
    CONFIG_UPDATED = "config_updated"
    DISCOVERY_COMPLETED = "discovery_completed"
    ERROR_OCCURRED = "error_occurred"
    ALERT_TRIGGERED = "alert_triggered"
    METRICS_UPDATED = "metrics_updated"


class NotificationPriority(str, Enum):
    """Priority levels for notifications."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationChannel(str, Enum):
    """Predefined notification channels."""
    SERVICE_EVENTS = "service_events"
    HEALTH_EVENTS = "health_events"
    CONFIG_EVENTS = "config_events"
    DISCOVERY_EVENTS = "discovery_events"
    ERROR_EVENTS = "error_events"
    ALERT_EVENTS = "alert_events"
    METRICS_EVENTS = "metrics_events"
    ALL_EVENTS = "all_events"


class NotificationMessage(BaseModel):
    """Structured notification message."""
    id: str
    type: NotificationType
    priority: NotificationPriority
    channel: str
    service_id: Optional[str] = None
    title: str
    message: str
    data: Dict[str, Any] = {}
    timestamp: datetime
    correlation_id: Optional[str] = None
    source: str = "machina-registry"
    tags: List[str] = []


class NotificationFilter(BaseModel):
    """Filter configuration for notification subscriptions."""
    types: Optional[List[NotificationType]] = None
    priorities: Optional[List[NotificationPriority]] = None
    service_ids: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    exclude_types: Optional[List[NotificationType]] = None


class NotificationSubscription(BaseModel):
    """Subscription configuration."""
    subscription_id: str
    channels: List[str]
    filters: Optional[NotificationFilter] = None
    callback: Optional[Callable[[NotificationMessage], Awaitable[None]]] = None
    active: bool = True
    created_at: datetime
    last_message_at: Optional[datetime] = None
    message_count: int = 0

    class Config:
        arbitrary_types_allowed = True


class NotificationStats(BaseModel):
    """Notification system statistics."""
    total_published: int = 0
    total_delivered: int = 0
    total_failed: int = 0
    active_subscribers: int = 0
    messages_by_type: Dict[str, int] = {}
    messages_by_priority: Dict[str, int] = {}
    average_delivery_time_ms: float = 0.0
    last_reset: datetime


class NotificationService:
    """
    High-level notification service for pub/sub messaging.

    Provides structured notification publishing, subscription management,
    and real-time event distribution with filtering and routing capabilities.
    """

    def __init__(self):
        """Initialize notification service."""
        self.channel_prefix = "notifications:"
        self.pubsub: Optional[RedisPubSub] = None
        self.subscriptions: Dict[str, NotificationSubscription] = {}
        self.stats = NotificationStats(last_reset=datetime.utcnow())
        self._running = False
        self._listener_task: Optional[asyncio.Task] = None

    async def initialize(self):
        """Initialize the notification service."""
        with logfire.span("Notification Service Initialization"):
            try:
                self.pubsub = await get_pubsub(self.channel_prefix)
                logfire.info("Notification service initialized successfully")
                self._running = True
            except Exception as e:
                logfire.error("Failed to initialize notification service", error=str(e))
                raise

    async def shutdown(self):
        """Shutdown the notification service."""
        with logfire.span("Notification Service Shutdown"):
            self._running = False

            if self._listener_task:
                self._listener_task.cancel()
                try:
                    await self._listener_task
                except asyncio.CancelledError:
                    pass

            if self.pubsub:
                await self.pubsub.close()

            logfire.info("Notification service shutdown completed")

    async def publish(
        self,
        notification_type: NotificationType,
        title: str,
        message: str,
        channel: Union[NotificationChannel, str] = NotificationChannel.ALL_EVENTS,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        service_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        correlation_id: Optional[str] = None
    ) -> bool:
        """
        Publish a notification message.

        Args:
            notification_type: Type of notification
            title: Notification title
            message: Notification message
            channel: Target channel
            priority: Message priority
            service_id: Optional service ID
            data: Additional data
            tags: Message tags
            correlation_id: Optional correlation ID

        Returns:
            True if published successfully
        """
        if not self.pubsub:
            await self.initialize()

        notification = NotificationMessage(
            id=str(uuid.uuid4()),
            type=notification_type,
            priority=priority,
            channel=channel.value if isinstance(channel, NotificationChannel) else channel,
            service_id=service_id,
            title=title,
            message=message,
            data=data or {},
            timestamp=datetime.utcnow(),
            correlation_id=correlation_id,
            tags=tags or []
        )

        with logfire.span(
            "Publish Notification",
            notification_type=notification_type.value,
            priority=priority.value,
            channel=notification.channel
        ):
            try:
                # Publish to specific channel
                subscribers = await self.pubsub.publish(
                    notification.channel,
                    notification.model_dump()
                )

                # Also publish to all_events channel if not already
                if notification.channel != NotificationChannel.ALL_EVENTS.value:
                    await self.pubsub.publish(
                        NotificationChannel.ALL_EVENTS.value,
                        notification.model_dump()
                    )

                # Update statistics
                self.stats.total_published += 1
                self.stats.messages_by_type[notification_type.value] = (
                    self.stats.messages_by_type.get(notification_type.value, 0) + 1
                )
                self.stats.messages_by_priority[priority.value] = (
                    self.stats.messages_by_priority.get(priority.value, 0) + 1
                )

                logfire.info(
                    "Notification published",
                    notification_id=notification.id,
                    type=notification_type.value,
                    subscribers=subscribers,
                    title=title
                )

                return True

            except RedisPubSubError as e:
                logfire.error(
                    "Failed to publish notification",
                    notification_type=notification_type.value,
                    error=str(e)
                )
                self.stats.total_failed += 1
                return False

    async def subscribe(
        self,
        channels: Union[List[str], List[NotificationChannel]],
        callback: Callable[[NotificationMessage], Awaitable[None]],
        filters: Optional[NotificationFilter] = None,
        subscription_id: Optional[str] = None
    ) -> str:
        """
        Subscribe to notification channels.

        Args:
            channels: List of channels to subscribe to
            callback: Async callback function for messages
            filters: Optional message filters
            subscription_id: Optional custom subscription ID

        Returns:
            Subscription ID
        """
        if not self.pubsub:
            await self.initialize()

        sub_id = subscription_id or str(uuid.uuid4())

        # Convert enum channels to strings
        channel_names = []
        for channel in channels:
            if isinstance(channel, NotificationChannel):
                channel_names.append(channel.value)
            else:
                channel_names.append(channel)

        subscription = NotificationSubscription(
            subscription_id=sub_id,
            channels=channel_names,
            filters=filters,
            callback=callback,
            created_at=datetime.utcnow()
        )

        self.subscriptions[sub_id] = subscription

        # Subscribe to Redis channels
        await self.pubsub.subscribe(*channel_names)

        # Start listener if not already running
        if not self._listener_task or self._listener_task.done():
            self._listener_task = asyncio.create_task(self._message_listener())

        self.stats.active_subscribers = len(self.subscriptions)

        logfire.info(
            "Notification subscription created",
            subscription_id=sub_id,
            channels=channel_names,
            has_filters=filters is not None
        )

        return sub_id

    async def unsubscribe(self, subscription_id: str) -> bool:
        """
        Unsubscribe from notifications.

        Args:
            subscription_id: Subscription ID to remove

        Returns:
            True if unsubscribed successfully
        """
        if subscription_id not in self.subscriptions:
            logfire.warning("Subscription not found", subscription_id=subscription_id)
            return False

        subscription = self.subscriptions.pop(subscription_id)
        subscription.active = False

        # Check if any other subscriptions use these channels
        channels_in_use = set()
        for sub in self.subscriptions.values():
            channels_in_use.update(sub.channels)

        # Unsubscribe from channels no longer needed
        unused_channels = set(subscription.channels) - channels_in_use
        if unused_channels and self.pubsub:
            await self.pubsub.unsubscribe(*unused_channels)

        self.stats.active_subscribers = len(self.subscriptions)

        logfire.info(
            "Notification subscription removed",
            subscription_id=subscription_id,
            channels=subscription.channels
        )

        return True

    async def _message_listener(self):
        """Internal message listener for processing incoming notifications."""
        if not self.pubsub:
            return

        logfire.info("Starting notification message listener")

        try:
            await self.pubsub.listen(
                self._handle_message,
                self._handle_error
            )
        except asyncio.CancelledError:
            logfire.info("Notification message listener cancelled")
        except Exception as e:
            logfire.error("Notification message listener failed", error=str(e))

    async def _handle_message(self, channel: str, data: Dict[str, Any]):
        """Handle incoming notification message."""
        try:
            notification = NotificationMessage(**data)

            # Find matching subscriptions
            matching_subs = []
            for sub in self.subscriptions.values():
                if not sub.active:
                    continue

                if channel in sub.channels or NotificationChannel.ALL_EVENTS.value in sub.channels:
                    if self._passes_filter(notification, sub.filters):
                        matching_subs.append(sub)

            # Deliver to matching subscriptions
            for sub in matching_subs:
                try:
                    await sub.callback(notification)
                    sub.last_message_at = datetime.utcnow()
                    sub.message_count += 1
                    self.stats.total_delivered += 1

                    logfire.debug(
                        "Notification delivered",
                        subscription_id=sub.subscription_id,
                        notification_id=notification.id
                    )

                except Exception as e:
                    logfire.error(
                        "Error in notification callback",
                        subscription_id=sub.subscription_id,
                        notification_id=notification.id,
                        error=str(e)
                    )
                    self.stats.total_failed += 1

        except Exception as e:
            logfire.error("Error processing notification message", error=str(e), data=data)

    async def _handle_error(self, error: Exception):
        """Handle errors in message listener."""
        logfire.error("Error in notification message listener", error=str(error))

    def _passes_filter(
        self,
        notification: NotificationMessage,
        filters: Optional[NotificationFilter]
    ) -> bool:
        """Check if notification passes filter criteria."""
        if not filters:
            return True

        # Check type filters
        if filters.types and notification.type not in filters.types:
            return False

        if filters.exclude_types and notification.type in filters.exclude_types:
            return False

        # Check priority filters
        if filters.priorities and notification.priority not in filters.priorities:
            return False

        # Check service ID filters
        if filters.service_ids and notification.service_id not in filters.service_ids:
            return False

        # Check tag filters
        if filters.tags:
            if not any(tag in notification.tags for tag in filters.tags):
                return False

        return True

    # Convenience methods for common notifications

    async def notify_service_registered(
        self,
        service_id: str,
        service_name: str,
        service_data: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> bool:
        """Notify that a service has been registered."""
        return await self.publish(
            NotificationType.SERVICE_REGISTERED,
            f"Service Registered: {service_name}",
            f"Service {service_id} ({service_name}) has been registered",
            NotificationChannel.SERVICE_EVENTS,
            NotificationPriority.NORMAL,
            service_id=service_id,
            data=service_data,
            correlation_id=correlation_id
        )

    async def notify_service_unregistered(
        self,
        service_id: str,
        service_name: str,
        correlation_id: Optional[str] = None
    ) -> bool:
        """Notify that a service has been unregistered."""
        return await self.publish(
            NotificationType.SERVICE_UNREGISTERED,
            f"Service Unregistered: {service_name}",
            f"Service {service_id} ({service_name}) has been unregistered",
            NotificationChannel.SERVICE_EVENTS,
            NotificationPriority.NORMAL,
            service_id=service_id,
            correlation_id=correlation_id
        )

    async def notify_health_check_failed(
        self,
        service_id: str,
        service_name: str,
        error_details: str,
        correlation_id: Optional[str] = None
    ) -> bool:
        """Notify that a health check has failed."""
        return await self.publish(
            NotificationType.HEALTH_CHECK_FAILED,
            f"Health Check Failed: {service_name}",
            f"Health check failed for service {service_id}: {error_details}",
            NotificationChannel.HEALTH_EVENTS,
            NotificationPriority.HIGH,
            service_id=service_id,
            data={"error": error_details},
            tags=["health", "failure"],
            correlation_id=correlation_id
        )

    async def notify_health_check_recovered(
        self,
        service_id: str,
        service_name: str,
        correlation_id: Optional[str] = None
    ) -> bool:
        """Notify that a service has recovered from health check failure."""
        return await self.publish(
            NotificationType.HEALTH_CHECK_RECOVERED,
            f"Health Check Recovered: {service_name}",
            f"Service {service_id} has recovered and is now healthy",
            NotificationChannel.HEALTH_EVENTS,
            NotificationPriority.NORMAL,
            service_id=service_id,
            tags=["health", "recovery"],
            correlation_id=correlation_id
        )

    async def notify_config_updated(
        self,
        config_key: str,
        changes: Dict[str, Any],
        service_id: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> bool:
        """Notify that configuration has been updated."""
        return await self.publish(
            NotificationType.CONFIG_UPDATED,
            f"Configuration Updated: {config_key}",
            f"Configuration {config_key} has been updated",
            NotificationChannel.CONFIG_EVENTS,
            NotificationPriority.NORMAL,
            service_id=service_id,
            data={"config_key": config_key, "changes": changes},
            tags=["config"],
            correlation_id=correlation_id
        )

    async def notify_error(
        self,
        error_type: str,
        error_message: str,
        error_details: Dict[str, Any],
        service_id: Optional[str] = None,
        priority: NotificationPriority = NotificationPriority.HIGH,
        correlation_id: Optional[str] = None
    ) -> bool:
        """Notify about an error occurrence."""
        return await self.publish(
            NotificationType.ERROR_OCCURRED,
            f"Error: {error_type}",
            error_message,
            NotificationChannel.ERROR_EVENTS,
            priority,
            service_id=service_id,
            data={"error_type": error_type, **error_details},
            tags=["error"],
            correlation_id=correlation_id
        )

    async def get_subscription_stats(self, subscription_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a specific subscription."""
        if subscription_id not in self.subscriptions:
            return None

        sub = self.subscriptions[subscription_id]
        return {
            "subscription_id": sub.subscription_id,
            "channels": sub.channels,
            "active": sub.active,
            "created_at": sub.created_at.isoformat(),
            "last_message_at": sub.last_message_at.isoformat() if sub.last_message_at else None,
            "message_count": sub.message_count,
            "has_filters": sub.filters is not None
        }

    async def get_service_stats(self) -> Dict[str, Any]:
        """Get comprehensive notification service statistics."""
        return {
            "stats": self.stats.model_dump(),
            "active_subscriptions": len(self.subscriptions),
            "subscription_details": [
                {
                    "id": sub.subscription_id,
                    "channels": sub.channels,
                    "message_count": sub.message_count,
                    "active": sub.active
                }
                for sub in self.subscriptions.values()
            ],
            "service_status": {
                "running": self._running,
                "pubsub_connected": self.pubsub is not None,
                "listener_active": self._listener_task is not None and not self._listener_task.done()
            }
        }

    async def reset_stats(self):
        """Reset notification statistics."""
        self.stats = NotificationStats(last_reset=datetime.utcnow())
        logfire.info("Notification service statistics reset")


# Global notification service instance
_notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """
    Get global notification service instance.

    Returns:
        NotificationService: Global notification service instance
    """
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service


async def initialize_notification_service() -> NotificationService:
    """
    Initialize and return notification service.

    Returns:
        NotificationService: Initialized notification service
    """
    service = get_notification_service()
    await service.initialize()
    return service


async def shutdown_notification_service():
    """Shutdown the global notification service."""
    global _notification_service
    if _notification_service:
        await _notification_service.shutdown()
        _notification_service = None
