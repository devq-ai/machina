"""
Registry Item Domain Model for Machina Registry Service

This module defines the RegistryItem model which represents MCP servers and services
in the Machina Registry. It extends the BaseModel with specific fields and functionality
for managing MCP service metadata, health status, and configuration.

Features:
- Complete MCP service metadata storage
- Health status tracking and history
- Configuration management with validation
- Service discovery metadata
- Build type and protocol specification
- Dependency tracking between services
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from enum import Enum

import logfire
from sqlalchemy import Column, String, Text, JSON, Enum as SQLEnum, Boolean, Integer
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import validates

from app.models.base import BaseModel


class ServiceBuildType(str, Enum):
    """Enumeration of supported MCP service build types."""
    FASTMCP = "fastmcp"
    STUB = "stub"
    EXTERNAL = "external"
    OFFICIAL = "official"
    CUSTOM = "custom"
    DOCKER = "docker"


class ServiceProtocol(str, Enum):
    """Enumeration of supported MCP service protocols."""
    STDIO = "stdio"
    HTTP = "http"
    WEBSOCKET = "websocket"
    TCP = "tcp"
    UNIX_SOCKET = "unix_socket"


class ServiceStatus(str, Enum):
    """Enumeration of service health statuses."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    MAINTENANCE = "maintenance"
    DISABLED = "disabled"


class ServicePriority(str, Enum):
    """Enumeration of service priority levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RegistryItem(BaseModel):
    """
    Registry item model representing an MCP service or server.

    This model stores comprehensive metadata about MCP services including
    their configuration, health status, dependencies, and operational data.
    """

    # Basic service identification
    name = Column(
        String(255),
        nullable=False,
        index=True,
        unique=True,
        doc="Unique service name (e.g., 'task-master-mcp-server')"
    )

    display_name = Column(
        String(255),
        nullable=True,
        doc="Human-readable display name for the service"
    )

    description = Column(
        Text,
        nullable=True,
        doc="Detailed description of the service functionality"
    )

    # Service classification
    build_type = Column(
        SQLEnum(ServiceBuildType),
        nullable=False,
        default=ServiceBuildType.FASTMCP,
        index=True,
        doc="Type of service build (fastmcp, stub, external, etc.)"
    )

    protocol = Column(
        SQLEnum(ServiceProtocol),
        nullable=False,
        default=ServiceProtocol.STDIO,
        index=True,
        doc="Communication protocol used by the service"
    )

    priority = Column(
        SQLEnum(ServicePriority),
        nullable=False,
        default=ServicePriority.MEDIUM,
        index=True,
        doc="Service priority level for resource allocation"
    )

    # Service location and access
    location = Column(
        String(512),
        nullable=True,
        doc="File system path, URL, or container reference"
    )

    endpoint = Column(
        String(512),
        nullable=True,
        doc="Service endpoint URL or connection string"
    )

    port = Column(
        Integer,
        nullable=True,
        doc="Service port number (if applicable)"
    )

    # Service metadata and configuration
    version = Column(
        String(50),
        nullable=True,
        doc="Service version string"
    )

    tags = Column(
        ARRAY(String),
        nullable=True,
        default=list,
        doc="Array of tags for categorization and filtering"
    )

    service_metadata = Column(
        JSON,
        nullable=True,
        default=dict,
        doc="Flexible JSON metadata for service-specific data"
    )

    config = Column(
        JSON,
        nullable=True,
        default=dict,
        doc="Service configuration parameters"
    )

    # Health and status tracking
    status = Column(
        SQLEnum(ServiceStatus),
        nullable=False,
        default=ServiceStatus.UNKNOWN,
        index=True,
        doc="Current health status of the service"
    )

    last_health_check = Column(
        String,
        nullable=True,
        doc="Timestamp of last health check (ISO format)"
    )

    health_check_url = Column(
        String(512),
        nullable=True,
        doc="URL for health check endpoint"
    )

    response_time_ms = Column(
        Integer,
        nullable=True,
        doc="Last recorded response time in milliseconds"
    )

    # Service flags and toggles
    is_required = Column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        doc="Whether this service is required for core functionality"
    )

    is_enabled = Column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        doc="Whether this service is enabled for discovery"
    )

    auto_start = Column(
        Boolean,
        nullable=False,
        default=False,
        doc="Whether to automatically start this service"
    )

    # Dependency management
    dependencies = Column(
        ARRAY(String),
        nullable=True,
        default=list,
        doc="Array of service names this service depends on"
    )

    dependents = Column(
        ARRAY(String),
        nullable=True,
        default=list,
        doc="Array of service names that depend on this service"
    )

    # Registry and discovery metadata
    source = Column(
        String(255),
        nullable=True,
        doc="Source of service discovery (local, docker, external, etc.)"
    )

    registry_url = Column(
        String(512),
        nullable=True,
        doc="URL of the registry where this service was discovered"
    )

    last_seen = Column(
        String,
        nullable=True,
        doc="Timestamp when service was last seen during discovery"
    )

    # Statistics and analytics
    success_count = Column(
        Integer,
        nullable=False,
        default=0,
        doc="Number of successful health checks or operations"
    )

    failure_count = Column(
        Integer,
        nullable=False,
        default=0,
        doc="Number of failed health checks or operations"
    )

    def __init__(self, **kwargs):
        """Initialize registry item with validation and defaults."""
        # Ensure arrays are initialized as lists
        if 'tags' not in kwargs:
            kwargs['tags'] = []
        if 'dependencies' not in kwargs:
            kwargs['dependencies'] = []
        if 'dependents' not in kwargs:
            kwargs['dependents'] = []
        if 'service_metadata' not in kwargs:
            kwargs['service_metadata'] = {}
        if 'config' not in kwargs:
            kwargs['config'] = {}

        # Ensure counter fields are initialized
        if 'success_count' not in kwargs:
            kwargs['success_count'] = 0
        if 'failure_count' not in kwargs:
            kwargs['failure_count'] = 0

        super().__init__(**kwargs)

    def __repr__(self) -> str:
        """String representation of the registry item."""
        return (
            f"<RegistryItem("
            f"name='{self.name}', "
            f"build_type={self.build_type}, "
            f"status={self.status}, "
            f"is_active={self.is_active}"
            f")>"
        )

    @validates('name')
    def validate_name(self, key: str, value: str) -> str:
        """Validate service name format."""
        if not value:
            raise ValueError("Service name cannot be empty")

        if len(value) > 255:
            raise ValueError("Service name cannot exceed 255 characters")

        # Basic validation for service name format
        import re
        if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9-_]*[a-zA-Z0-9]$', value):
            raise ValueError(
                "Service name must start and end with alphanumeric characters "
                "and can contain hyphens and underscores"
            )

        return value.lower()

    @validates('port')
    def validate_port(self, key: str, value: Optional[int]) -> Optional[int]:
        """Validate port number range."""
        if value is not None:
            if not isinstance(value, int) or value < 1 or value > 65535:
                raise ValueError("Port must be an integer between 1 and 65535")
        return value

    @validates('version')
    def validate_version(self, key: str, value: Optional[str]) -> Optional[str]:
        """Validate version string format."""
        if value is not None:
            if len(value) > 50:
                raise ValueError("Version string cannot exceed 50 characters")
        return value

    def update_health_status(self, status: ServiceStatus, response_time_ms: Optional[int] = None) -> None:
        """
        Update the health status of the service.

        Args:
            status: New health status
            response_time_ms: Optional response time in milliseconds
        """
        old_status = self.status
        self.status = status
        self.last_health_check = datetime.utcnow().isoformat()

        if response_time_ms is not None:
            self.response_time_ms = response_time_ms

        # Update success/failure counters
        if status == ServiceStatus.HEALTHY:
            self.success_count += 1
        elif status == ServiceStatus.UNHEALTHY:
            self.failure_count += 1

        logfire.info(
            "Service health status updated",
            service_name=self.name,
            old_status=old_status,
            new_status=status,
            response_time_ms=response_time_ms
        )

    def add_dependency(self, dependency_name: str) -> None:
        """
        Add a dependency to this service.

        Args:
            dependency_name: Name of the service this depends on
        """
        if not self.dependencies:
            self.dependencies = []

        if dependency_name not in self.dependencies:
            self.dependencies.append(dependency_name)
            logfire.debug(
                "Dependency added",
                service_name=self.name,
                dependency=dependency_name
            )

    def remove_dependency(self, dependency_name: str) -> bool:
        """
        Remove a dependency from this service.

        Args:
            dependency_name: Name of the dependency to remove

        Returns:
            True if dependency was removed, False if not found
        """
        if self.dependencies and dependency_name in self.dependencies:
            self.dependencies.remove(dependency_name)
            logfire.debug(
                "Dependency removed",
                service_name=self.name,
                dependency=dependency_name
            )
            return True
        return False

    def add_tag(self, tag: str) -> None:
        """
        Add a tag to this service.

        Args:
            tag: Tag to add
        """
        if not self.tags:
            self.tags = []

        if tag not in self.tags:
            self.tags.append(tag)

    def remove_tag(self, tag: str) -> bool:
        """
        Remove a tag from this service.

        Args:
            tag: Tag to remove

        Returns:
            True if tag was removed, False if not found
        """
        if self.tags and tag in self.tags:
            self.tags.remove(tag)
            return True
        return False

    def has_tag(self, tag: str) -> bool:
        """
        Check if service has a specific tag.

        Args:
            tag: Tag to check for

        Returns:
            True if service has the tag
        """
        return self.tags is not None and tag in self.tags

    def update_metadata(self, new_metadata: Dict[str, Any]) -> None:
        """
        Update service metadata.

        Args:
            new_metadata: Dictionary of metadata to merge
        """
        if not self.service_metadata:
            self.service_metadata = {}

        self.service_metadata.update(new_metadata)
        self.updated_at = datetime.utcnow()

    def update_config(self, new_config: Dict[str, Any]) -> None:
        """
        Update service configuration.

        Args:
            new_config: Dictionary of configuration to merge
        """
        if not self.config:
            self.config = {}

        self.config.update(new_config)
        self.updated_at = datetime.utcnow()

    def get_health_score(self) -> float:
        """
        Calculate a health score based on success/failure ratio.

        Returns:
            Health score between 0.0 and 1.0
        """
        total_checks = self.success_count + self.failure_count
        if total_checks == 0:
            return 0.5  # Unknown health

        return self.success_count / total_checks

    def is_healthy(self) -> bool:
        """
        Check if the service is currently healthy.

        Returns:
            True if service status is healthy
        """
        return self.status == ServiceStatus.HEALTHY and self.is_active

    def is_critical(self) -> bool:
        """
        Check if this service is critical to system operation.

        Returns:
            True if service is required or has critical priority
        """
        return self.is_required or self.priority == ServicePriority.CRITICAL

    def to_dict(self, include_deleted: bool = False, exclude: Optional[Set[str]] = None) -> Dict[str, Any]:
        """
        Convert to dictionary with registry-specific formatting.

        Args:
            include_deleted: Whether to include soft-deleted records
            exclude: Set of field names to exclude

        Returns:
            Dictionary representation optimized for API responses
        """
        result = super().to_dict(include_deleted=include_deleted, exclude=exclude)

        if result:
            # Add computed fields
            result['health_score'] = self.get_health_score()
            result['is_healthy'] = self.is_healthy()
            result['is_critical'] = self.is_critical()

            # Format enum values as strings
            if 'build_type' in result and result['build_type']:
                result['build_type'] = result['build_type'].value
            if 'protocol' in result and result['protocol']:
                result['protocol'] = result['protocol'].value
            if 'status' in result and result['status']:
                result['status'] = result['status'].value
            if 'priority' in result and result['priority']:
                result['priority'] = result['priority'].value

        return result

    @classmethod
    def create_from_discovery(
        cls,
        name: str,
        build_type: ServiceBuildType,
        location: str,
        discovered_by: str,
        **kwargs
    ) -> 'RegistryItem':
        """
        Create a registry item from service discovery data.

        Args:
            name: Service name
            build_type: Type of service build
            location: Service location or path
            discovered_by: System or user that discovered the service
            **kwargs: Additional service metadata

        Returns:
            New RegistryItem instance
        """
        return cls(
            name=name,
            build_type=build_type,
            location=location,
            source=discovered_by,
            last_seen=datetime.utcnow().isoformat(),
            created_by=discovered_by,
            updated_by=discovered_by,
            **kwargs
        )
