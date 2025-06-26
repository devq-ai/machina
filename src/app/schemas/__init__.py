"""
Pydantic Schemas Module for Machina Registry Service

This module provides Pydantic models for request/response validation and serialization
across all API endpoints in the Machina Registry Service. It implements DevQ.ai's
standard API patterns with comprehensive validation, documentation, and type safety.

Features:
- Request/response models for all API endpoints
- Comprehensive field validation with custom validators
- Automatic OpenAPI schema generation
- Type-safe serialization and deserialization
- Integration with FastAPI dependency injection
- Support for filtering, pagination, and search parameters
"""

from .service_schemas import (
    # Service base schemas
    ServiceBase,
    ServiceCreate,
    ServiceUpdate,
    ServiceResponse,
    ServiceDetail,
    ServiceSummary,

    # Service listing and filtering
    ServiceListResponse,
    ServiceFilter,
    ServiceSearchParams,

    # Health and status schemas
    ServiceHealthCheck,
    ServiceHealthResponse,
    ServiceStatusUpdate,

    # Discovery and registration schemas
    ServiceDiscoveryRequest,
    ServiceDiscoveryResponse,
    ServiceRegistrationRequest,
    ServiceRegistrationResponse,

    # Configuration schemas
    ServiceConfig,
    ServiceConfigUpdate,

    # Utility schemas
    PaginationParams,
    SortParams,
    BulkOperationRequest,
    BulkOperationResponse,
)

__all__ = [
    # Service base schemas
    "ServiceBase",
    "ServiceCreate",
    "ServiceUpdate",
    "ServiceResponse",
    "ServiceDetail",
    "ServiceSummary",

    # Service listing and filtering
    "ServiceListResponse",
    "ServiceFilter",
    "ServiceSearchParams",

    # Health and status schemas
    "ServiceHealthCheck",
    "ServiceHealthResponse",
    "ServiceStatusUpdate",

    # Discovery and registration schemas
    "ServiceDiscoveryRequest",
    "ServiceDiscoveryResponse",
    "ServiceRegistrationRequest",
    "ServiceRegistrationResponse",

    # Configuration schemas
    "ServiceConfig",
    "ServiceConfigUpdate",

    # Utility schemas
    "PaginationParams",
    "SortParams",
    "BulkOperationRequest",
    "BulkOperationResponse",
]
