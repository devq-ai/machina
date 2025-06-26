"""
Service Schemas Module for Machina Registry Service

This module provides comprehensive Pydantic models for service discovery, registration,
and management API endpoints. It implements DevQ.ai's standard API patterns with
validation, documentation, and type safety for all service-related operations.

Features:
- Complete service CRUD operation schemas
- Health monitoring and status management schemas
- Service discovery and registration validation
- Configuration management with versioning
- Filtering, pagination, and search capabilities
- Integration with existing domain models and enums
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Union
from uuid import UUID

import logfire
from pydantic import BaseModel, Field, validator, root_validator
from enum import Enum

# Import domain model enums
from app.models.domain.registry_item import (
    ServiceBuildType,
    ServiceProtocol,
    ServiceStatus,
    ServicePriority
)


class ServiceSortField(str, Enum):
    """Enumeration of fields available for service sorting."""
    NAME = "name"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    STATUS = "status"
    PRIORITY = "priority"
    HEALTH_SCORE = "health_score"
    LAST_HEALTH_CHECK = "last_health_check"


class SortDirection(str, Enum):
    """Enumeration of sort directions."""
    ASC = "asc"
    DESC = "desc"


# Base Schemas
class ServiceBase(BaseModel):
    """Base schema with common service fields."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Unique service name (alphanumeric, hyphens, underscores)"
    )
    display_name: Optional[str] = Field(
        None,
        max_length=255,
        description="Human-readable display name"
    )
    description: Optional[str] = Field(
        None,
        description="Detailed description of service functionality"
    )
    build_type: ServiceBuildType = Field(
        ServiceBuildType.FASTMCP,
        description="Type of service build"
    )
    protocol: ServiceProtocol = Field(
        ServiceProtocol.STDIO,
        description="Communication protocol"
    )
    priority: ServicePriority = Field(
        ServicePriority.MEDIUM,
        description="Service priority level"
    )
    location: Optional[str] = Field(
        None,
        max_length=512,
        description="Service location (path, URL, container reference)"
    )
    endpoint: Optional[str] = Field(
        None,
        max_length=512,
        description="Service endpoint URL or connection string"
    )
    port: Optional[int] = Field(
        None,
        ge=1,
        le=65535,
        description="Service port number"
    )
    version: Optional[str] = Field(
        None,
        max_length=50,
        description="Service version string"
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Tags for categorization and filtering"
    )

    @validator('name')
    def validate_name(cls, v):
        """Validate service name format."""
        if not v:
            raise ValueError("Service name cannot be empty")

        # Allow alphanumeric, hyphens, and underscores
        if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9-_]*[a-zA-Z0-9]$', v):
            raise ValueError(
                "Service name must start and end with alphanumeric characters "
                "and can contain hyphens and underscores"
            )
        return v.lower()

    @validator('tags')
    def validate_tags(cls, v):
        """Validate and clean tags."""
        if not v:
            return []

        # Remove duplicates and empty tags
        cleaned_tags = list(set(tag.strip().lower() for tag in v if tag.strip()))
        return cleaned_tags[:20]  # Limit to 20 tags

    class Config:
        use_enum_values = True
        schema_extra = {
            "example": {
                "name": "task-master-mcp",
                "display_name": "TaskMaster MCP Server",
                "description": "AI-powered task management and workflow automation",
                "build_type": "fastmcp",
                "protocol": "stdio",
                "priority": "high",
                "location": "/mcp/mcp-servers/task-master",
                "port": 8080,
                "version": "1.0.0",
                "tags": ["ai", "automation", "mcp-server"]
            }
        }


class ServiceCreate(ServiceBase):
    """Schema for creating a new service."""

    # Optional fields for creation
    is_required: bool = Field(
        False,
        description="Whether service is required for core functionality"
    )
    is_enabled: bool = Field(
        True,
        description="Whether service is enabled for discovery"
    )
    auto_start: bool = Field(
        False,
        description="Whether to automatically start this service"
    )
    dependencies: List[str] = Field(
        default_factory=list,
        description="List of service names this service depends on"
    )
    service_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Service-specific metadata"
    )
    config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Service configuration parameters"
    )
    health_check_url: Optional[str] = Field(
        None,
        max_length=512,
        description="URL for health check endpoint"
    )

    class Config:
        schema_extra = {
            "example": {
                **ServiceBase.Config.schema_extra["example"],
                "is_required": True,
                "is_enabled": True,
                "auto_start": False,
                "dependencies": ["database-service"],
                "service_metadata": {
                    "framework": "fastapi",
                    "language": "python"
                },
                "config": {
                    "max_workers": 4,
                    "timeout": 30
                },
                "health_check_url": "http://localhost:8080/health"
            }
        }


class ServiceUpdate(BaseModel):
    """Schema for updating an existing service."""

    display_name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    build_type: Optional[ServiceBuildType] = None
    protocol: Optional[ServiceProtocol] = None
    priority: Optional[ServicePriority] = None
    location: Optional[str] = Field(None, max_length=512)
    endpoint: Optional[str] = Field(None, max_length=512)
    port: Optional[int] = Field(None, ge=1, le=65535)
    version: Optional[str] = Field(None, max_length=50)
    tags: Optional[List[str]] = None
    is_required: Optional[bool] = None
    is_enabled: Optional[bool] = None
    auto_start: Optional[bool] = None
    dependencies: Optional[List[str]] = None
    service_metadata: Optional[Dict[str, Any]] = None
    config: Optional[Dict[str, Any]] = None
    health_check_url: Optional[str] = Field(None, max_length=512)

    @validator('tags')
    def validate_tags(cls, v):
        """Validate and clean tags."""
        if v is None:
            return v

        # Remove duplicates and empty tags
        cleaned_tags = list(set(tag.strip().lower() for tag in v if tag.strip()))
        return cleaned_tags[:20]  # Limit to 20 tags

    class Config:
        use_enum_values = True


class ServiceResponse(ServiceBase):
    """Schema for service response with additional read-only fields."""

    id: UUID = Field(..., description="Unique service identifier")
    status: ServiceStatus = Field(..., description="Current health status")
    is_required: bool = Field(..., description="Required for core functionality")
    is_enabled: bool = Field(..., description="Enabled for discovery")
    auto_start: bool = Field(..., description="Auto-start enabled")
    is_active: bool = Field(..., description="Service is active")

    # Health and performance metrics
    last_health_check: Optional[str] = Field(
        None,
        description="Timestamp of last health check"
    )
    response_time_ms: Optional[int] = Field(
        None,
        description="Last response time in milliseconds"
    )
    success_count: int = Field(0, description="Number of successful checks")
    failure_count: int = Field(0, description="Number of failed checks")
    health_score: float = Field(0.0, ge=0.0, le=1.0, description="Health score (0-1)")

    # Dependencies and relationships
    dependencies: List[str] = Field(
        default_factory=list,
        description="Services this depends on"
    )
    dependents: List[str] = Field(
        default_factory=list,
        description="Services that depend on this"
    )

    # Discovery metadata
    source: Optional[str] = Field(None, description="Discovery source")
    last_seen: Optional[str] = Field(None, description="Last seen timestamp")

    # Timestamps
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    # Computed fields
    is_healthy: bool = Field(..., description="Service is currently healthy")
    is_critical: bool = Field(..., description="Service is critical to operation")

    class Config:
        use_enum_values = True
        orm_mode = True


class ServiceDetail(ServiceResponse):
    """Detailed service schema with full metadata."""

    service_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Complete service metadata"
    )
    config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Service configuration"
    )

    # Additional audit fields
    created_by: Optional[str] = Field(None, description="Created by user/system")
    updated_by: Optional[str] = Field(None, description="Updated by user/system")


class ServiceSummary(BaseModel):
    """Lightweight service summary for lists."""

    id: UUID
    name: str
    display_name: Optional[str]
    status: ServiceStatus
    priority: ServicePriority
    build_type: ServiceBuildType
    is_healthy: bool
    is_critical: bool
    health_score: float
    last_health_check: Optional[str]
    updated_at: datetime

    class Config:
        use_enum_values = True
        orm_mode = True


# Filtering and Search Schemas
class ServiceFilter(BaseModel):
    """Schema for filtering services."""

    status: Optional[List[ServiceStatus]] = Field(
        None,
        description="Filter by health status"
    )
    build_type: Optional[List[ServiceBuildType]] = Field(
        None,
        description="Filter by build type"
    )
    protocol: Optional[List[ServiceProtocol]] = Field(
        None,
        description="Filter by protocol"
    )
    priority: Optional[List[ServicePriority]] = Field(
        None,
        description="Filter by priority"
    )
    is_required: Optional[bool] = Field(
        None,
        description="Filter by required status"
    )
    is_enabled: Optional[bool] = Field(
        None,
        description="Filter by enabled status"
    )
    is_healthy: Optional[bool] = Field(
        None,
        description="Filter by health status"
    )
    tags: Optional[List[str]] = Field(
        None,
        description="Filter by tags (OR operation)"
    )
    has_dependencies: Optional[bool] = Field(
        None,
        description="Filter services with/without dependencies"
    )

    class Config:
        use_enum_values = True


class ServiceSearchParams(BaseModel):
    """Schema for service search parameters."""

    query: Optional[str] = Field(
        None,
        min_length=1,
        max_length=255,
        description="Search query (name, description, tags)"
    )
    filters: Optional[ServiceFilter] = Field(
        None,
        description="Additional filters"
    )

    @validator('query')
    def validate_query(cls, v):
        """Validate search query."""
        if v:
            return v.strip()
        return v


class PaginationParams(BaseModel):
    """Schema for pagination parameters."""

    page: int = Field(
        1,
        ge=1,
        description="Page number (1-based)"
    )
    size: int = Field(
        20,
        ge=1,
        le=100,
        description="Number of items per page"
    )


class SortParams(BaseModel):
    """Schema for sorting parameters."""

    field: ServiceSortField = Field(
        ServiceSortField.NAME,
        description="Field to sort by"
    )
    direction: SortDirection = Field(
        SortDirection.ASC,
        description="Sort direction"
    )

    class Config:
        use_enum_values = True


class ServiceListResponse(BaseModel):
    """Schema for paginated service list response."""

    items: List[ServiceSummary] = Field(..., description="List of services")
    total: int = Field(..., ge=0, description="Total number of services")
    page: int = Field(..., ge=1, description="Current page number")
    size: int = Field(..., ge=1, description="Items per page")
    pages: int = Field(..., ge=0, description="Total number of pages")
    has_next: bool = Field(..., description="Has next page")
    has_prev: bool = Field(..., description="Has previous page")

    class Config:
        schema_extra = {
            "example": {
                "items": [
                    {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "name": "task-master-mcp",
                        "display_name": "TaskMaster MCP Server",
                        "status": "healthy",
                        "priority": "high",
                        "build_type": "fastmcp",
                        "is_healthy": True,
                        "is_critical": True,
                        "health_score": 0.95,
                        "last_health_check": "2023-12-01T10:30:00Z",
                        "updated_at": "2023-12-01T10:00:00Z"
                    }
                ],
                "total": 1,
                "page": 1,
                "size": 20,
                "pages": 1,
                "has_next": False,
                "has_prev": False
            }
        }


# Health and Status Schemas
class ServiceHealthCheck(BaseModel):
    """Schema for health check request."""

    force_check: bool = Field(
        False,
        description="Force immediate health check"
    )
    include_metrics: bool = Field(
        True,
        description="Include performance metrics"
    )


class ServiceHealthResponse(BaseModel):
    """Schema for health check response."""

    service_id: UUID = Field(..., description="Service identifier")
    service_name: str = Field(..., description="Service name")
    status: ServiceStatus = Field(..., description="Health status")
    response_time_ms: Optional[int] = Field(
        None,
        description="Response time in milliseconds"
    )
    last_check: str = Field(..., description="Last check timestamp")
    error_message: Optional[str] = Field(
        None,
        description="Error message if unhealthy"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional health metadata"
    )

    class Config:
        use_enum_values = True


class ServiceStatusUpdate(BaseModel):
    """Schema for updating service status."""

    status: ServiceStatus = Field(..., description="New status")
    reason: Optional[str] = Field(
        None,
        max_length=255,
        description="Reason for status change"
    )

    class Config:
        use_enum_values = True


# Discovery and Registration Schemas
class ServiceDiscoveryRequest(BaseModel):
    """Schema for service discovery request."""

    discovery_types: List[str] = Field(
        default=["local", "docker", "external"],
        description="Types of discovery to perform"
    )
    force_refresh: bool = Field(
        False,
        description="Force refresh of all discovered services"
    )
    include_inactive: bool = Field(
        False,
        description="Include inactive/disabled services"
    )


class ServiceDiscoveryResponse(BaseModel):
    """Schema for service discovery response."""

    discovered_count: int = Field(..., ge=0, description="Number of discovered services")
    updated_count: int = Field(..., ge=0, description="Number of updated services")
    error_count: int = Field(..., ge=0, description="Number of discovery errors")
    discovery_time_ms: int = Field(..., ge=0, description="Discovery time in milliseconds")
    services: List[ServiceSummary] = Field(
        default_factory=list,
        description="Discovered services"
    )
    errors: List[str] = Field(
        default_factory=list,
        description="Discovery error messages"
    )


class ServiceRegistrationRequest(BaseModel):
    """Schema for manual service registration."""

    service_data: ServiceCreate = Field(..., description="Service data")
    validate_health: bool = Field(
        True,
        description="Validate service health during registration"
    )
    override_existing: bool = Field(
        False,
        description="Override existing service if name conflicts"
    )


class ServiceRegistrationResponse(BaseModel):
    """Schema for service registration response."""

    service: ServiceResponse = Field(..., description="Registered service")
    was_updated: bool = Field(..., description="Whether existing service was updated")
    health_check_result: Optional[ServiceHealthResponse] = Field(
        None,
        description="Health check result if validation was requested"
    )


# Configuration Schemas
class ServiceConfig(BaseModel):
    """Schema for service configuration."""

    config: Dict[str, Any] = Field(..., description="Configuration parameters")
    version: Optional[str] = Field(None, description="Configuration version")
    description: Optional[str] = Field(None, description="Configuration description")


class ServiceConfigUpdate(BaseModel):
    """Schema for configuration update."""

    config: Dict[str, Any] = Field(..., description="New configuration parameters")
    merge_with_existing: bool = Field(
        True,
        description="Merge with existing config or replace entirely"
    )
    description: Optional[str] = Field(None, description="Update description")


# Bulk Operations Schemas
class BulkOperationRequest(BaseModel):
    """Schema for bulk operations on services."""

    service_ids: List[UUID] = Field(
        ...,
        min_items=1,
        max_items=100,
        description="List of service IDs to operate on"
    )
    operation: str = Field(
        ...,
        description="Operation to perform (enable, disable, delete, etc.)"
    )
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Operation-specific parameters"
    )


class BulkOperationResponse(BaseModel):
    """Schema for bulk operation response."""

    total_requested: int = Field(..., ge=0, description="Total operations requested")
    successful: int = Field(..., ge=0, description="Successful operations")
    failed: int = Field(..., ge=0, description="Failed operations")
    results: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Individual operation results"
    )
    errors: List[str] = Field(
        default_factory=list,
        description="Error messages for failed operations"
    )
