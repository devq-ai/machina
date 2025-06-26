"""
Service Discovery and Management API Endpoints for Machina Registry Service

This module provides comprehensive REST API endpoints for service discovery, registration,
and management operations. It implements Subtask 3.1 of Task 3 with full CRUD operations,
health monitoring, and integration with the service discovery engine from Task 2.

Features:
- Complete service CRUD operations with validation
- Integration with ServiceRegistry and UnifiedDiscoveryOrchestrator
- Health monitoring and status management
- Service discovery triggers and automation
- Filtering, pagination, and search capabilities
- Bulk operations for efficient management
- Comprehensive error handling and logging
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

import logfire
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import and_, or_, func

from app.core.database import get_db
from app.core.exceptions import MachinaException
from app.models.domain.registry_item import (
    RegistryItem,
    ServiceBuildType,
    ServiceProtocol,
    ServiceStatus,
    ServicePriority
)
from app.schemas.service_schemas import (
    ServiceCreate,
    ServiceUpdate,
    ServiceResponse,
    ServiceDetail,
    ServiceSummary,
    ServiceListResponse,
    ServiceFilter,
    ServiceSearchParams,
    ServiceHealthCheck,
    ServiceHealthResponse,
    ServiceStatusUpdate,
    ServiceDiscoveryRequest,
    ServiceDiscoveryResponse,
    ServiceRegistrationRequest,
    ServiceRegistrationResponse,
    ServiceConfig,
    ServiceConfigUpdate,
    PaginationParams,
    SortParams,
    BulkOperationRequest,
    BulkOperationResponse,
    ServiceSortField,
    SortDirection,
)
from app.discovery.service_registry import ServiceRegistry
from app.discovery.unified_discovery_orchestrator import UnifiedDiscoveryOrchestrator
from app.discovery.health_probe import HealthProbeFactory

# Create router with proper tags and metadata
router = APIRouter(
    prefix="/services",
    tags=["Services"],
    responses={
        404: {"description": "Service not found"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"}
    }
)

# Initialize components
service_registry = None
discovery_orchestrator = None
health_probe_factory = HealthProbeFactory()


async def get_service_registry() -> ServiceRegistry:
    """Get or initialize the service registry."""
    global service_registry
    if service_registry is None:
        service_registry = ServiceRegistry()
    return service_registry


async def get_discovery_orchestrator() -> UnifiedDiscoveryOrchestrator:
    """Get or initialize the discovery orchestrator."""
    global discovery_orchestrator
    if discovery_orchestrator is None:
        discovery_orchestrator = UnifiedDiscoveryOrchestrator()
    return discovery_orchestrator


def convert_db_to_response(db_service: RegistryItem) -> ServiceResponse:
    """Convert database model to response schema."""
    return ServiceResponse(
        id=db_service.id,
        name=db_service.name,
        display_name=db_service.display_name,
        description=db_service.description,
        build_type=db_service.build_type,
        protocol=db_service.protocol,
        priority=db_service.priority,
        location=db_service.location,
        endpoint=db_service.endpoint,
        port=db_service.port,
        version=db_service.version,
        tags=db_service.tags or [],
        status=db_service.status,
        is_required=db_service.is_required,
        is_enabled=db_service.is_enabled,
        auto_start=db_service.auto_start,
        is_active=db_service.is_active,
        last_health_check=db_service.last_health_check,
        response_time_ms=db_service.response_time_ms,
        success_count=db_service.success_count,
        failure_count=db_service.failure_count,
        health_score=db_service.get_health_score(),
        dependencies=db_service.dependencies or [],
        dependents=db_service.dependents or [],
        source=db_service.source,
        last_seen=db_service.last_seen,
        created_at=db_service.created_at,
        updated_at=db_service.updated_at,
        is_healthy=db_service.is_healthy(),
        is_critical=db_service.is_critical()
    )


def convert_db_to_detail(db_service: RegistryItem) -> ServiceDetail:
    """Convert database model to detailed response schema."""
    base_response = convert_db_to_response(db_service)
    return ServiceDetail(
        **base_response.dict(),
        service_metadata=db_service.service_metadata or {},
        config=db_service.config or {},
        created_by=db_service.created_by,
        updated_by=db_service.updated_by
    )


def convert_db_to_summary(db_service: RegistryItem) -> ServiceSummary:
    """Convert database model to summary schema."""
    return ServiceSummary(
        id=db_service.id,
        name=db_service.name,
        display_name=db_service.display_name,
        status=db_service.status,
        priority=db_service.priority,
        build_type=db_service.build_type,
        is_healthy=db_service.is_healthy(),
        is_critical=db_service.is_critical(),
        health_score=db_service.get_health_score(),
        last_health_check=db_service.last_health_check,
        updated_at=db_service.updated_at
    )


def build_filter_query(query, filters: Optional[ServiceFilter]):
    """Build SQLAlchemy query with filters."""
    if not filters:
        return query

    conditions = []

    if filters.status:
        conditions.append(RegistryItem.status.in_(filters.status))

    if filters.build_type:
        conditions.append(RegistryItem.build_type.in_(filters.build_type))

    if filters.protocol:
        conditions.append(RegistryItem.protocol.in_(filters.protocol))

    if filters.priority:
        conditions.append(RegistryItem.priority.in_(filters.priority))

    if filters.is_required is not None:
        conditions.append(RegistryItem.is_required == filters.is_required)

    if filters.is_enabled is not None:
        conditions.append(RegistryItem.is_enabled == filters.is_enabled)

    if filters.is_healthy is not None:
        if filters.is_healthy:
            conditions.append(
                and_(
                    RegistryItem.status == ServiceStatus.HEALTHY,
                    RegistryItem.is_active == True
                )
            )
        else:
            conditions.append(
                or_(
                    RegistryItem.status != ServiceStatus.HEALTHY,
                    RegistryItem.is_active == False
                )
            )

    if filters.tags:
        # OR operation for tags - service must have at least one of the specified tags
        tag_conditions = []
        for tag in filters.tags:
            tag_conditions.append(RegistryItem.tags.any(tag))
        conditions.append(or_(*tag_conditions))

    if filters.has_dependencies is not None:
        if filters.has_dependencies:
            conditions.append(func.array_length(RegistryItem.dependencies, 1) > 0)
        else:
            conditions.append(
                or_(
                    RegistryItem.dependencies.is_(None),
                    func.array_length(RegistryItem.dependencies, 1) == 0
                )
            )

    if conditions:
        query = query.where(and_(*conditions))

    return query


def build_search_query(query, search_query: Optional[str]):
    """Build SQLAlchemy query with search conditions."""
    if not search_query:
        return query

    search_term = f"%{search_query.lower()}%"
    search_conditions = [
        RegistryItem.name.ilike(search_term),
        RegistryItem.display_name.ilike(search_term),
        RegistryItem.description.ilike(search_term),
    ]

    # Search in tags (this requires a more complex query)
    # For now, we'll convert the search to a simple approach
    query = query.where(or_(*search_conditions))
    return query


def apply_sorting(query, sort: SortParams):
    """Apply sorting to the query."""
    sort_column = getattr(RegistryItem, sort.field.value, None)
    if sort_column is None:
        # Default to name sorting if field is invalid
        sort_column = RegistryItem.name

    if sort.direction == SortDirection.DESC:
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    return query


# Service CRUD Endpoints

@router.get(
    "/",
    response_model=ServiceListResponse,
    summary="List Services",
    description="Get a paginated list of services with optional filtering and search"
)
async def list_services(
    pagination: PaginationParams = Depends(),
    sort: SortParams = Depends(),
    search: Optional[ServiceSearchParams] = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    List all services with pagination, filtering, and search capabilities.

    Args:
        pagination: Pagination parameters (page, size)
        sort: Sorting parameters (field, direction)
        search: Search and filter parameters
        db: Database session

    Returns:
        Paginated list of services with metadata
    """
    with logfire.span("List services", page=pagination.page, size=pagination.size):
        try:
            # Build base query
            query = select(RegistryItem).where(RegistryItem.is_active == True)

            # Apply search if provided
            if search and search.query:
                query = build_search_query(query, search.query)

            # Apply filters if provided
            if search and search.filters:
                query = build_filter_query(query, search.filters)

            # Get total count before pagination
            count_query = select(func.count()).select_from(query.subquery())
            count_result = await db.execute(count_query)
            total = count_result.scalar()

            # Apply sorting
            query = apply_sorting(query, sort)

            # Apply pagination
            offset = (pagination.page - 1) * pagination.size
            query = query.offset(offset).limit(pagination.size)

            # Execute query
            result = await db.execute(query)
            services = result.scalars().all()

            # Convert to summary format
            items = [convert_db_to_summary(service) for service in services]

            # Calculate pagination metadata
            pages = (total + pagination.size - 1) // pagination.size
            has_next = pagination.page < pages
            has_prev = pagination.page > 1

            logfire.info(
                "Services listed",
                total=total,
                returned=len(items),
                page=pagination.page,
                pages=pages
            )

            return ServiceListResponse(
                items=items,
                total=total,
                page=pagination.page,
                size=pagination.size,
                pages=pages,
                has_next=has_next,
                has_prev=has_prev
            )

        except Exception as e:
            logfire.error("Failed to list services", error=str(e))
            raise HTTPException(status_code=500, detail=f"Failed to list services: {str(e)}")


@router.get(
    "/{service_id}",
    response_model=ServiceDetail,
    summary="Get Service",
    description="Get detailed information about a specific service"
)
async def get_service(
    service_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed information about a specific service.

    Args:
        service_id: UUID of the service to retrieve
        db: Database session

    Returns:
        Detailed service information

    Raises:
        HTTPException: If service is not found
    """
    with logfire.span("Get service", service_id=str(service_id)):
        try:
            query = select(RegistryItem).where(
                and_(
                    RegistryItem.id == service_id,
                    RegistryItem.is_active == True
                )
            )
            result = await db.execute(query)
            service = result.scalar_one_or_none()

            if not service:
                logfire.warning("Service not found", service_id=str(service_id))
                raise HTTPException(status_code=404, detail=f"Service {service_id} not found")

            logfire.info("Service retrieved", service_id=str(service_id), service_name=service.name)
            return convert_db_to_detail(service)

        except HTTPException:
            raise
        except Exception as e:
            logfire.error("Failed to get service", service_id=str(service_id), error=str(e))
            raise HTTPException(status_code=500, detail=f"Failed to get service: {str(e)}")


@router.post(
    "/",
    response_model=ServiceResponse,
    status_code=201,
    summary="Create Service",
    description="Create a new service registration"
)
async def create_service(
    service_data: ServiceCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new service registration.

    Args:
        service_data: Service creation data
        background_tasks: Background task queue
        db: Database session

    Returns:
        Created service information

    Raises:
        HTTPException: If service name already exists or validation fails
    """
    with logfire.span("Create service", service_name=service_data.name):
        try:
            # Check if service already exists
            existing_query = select(RegistryItem).where(
                and_(
                    RegistryItem.name == service_data.name,
                    RegistryItem.is_active == True
                )
            )
            existing_result = await db.execute(existing_query)
            existing_service = existing_result.scalar_one_or_none()

            if existing_service:
                logfire.warning("Service already exists", service_name=service_data.name)
                raise HTTPException(
                    status_code=409,
                    detail=f"Service with name '{service_data.name}' already exists"
                )

            # Create new service
            db_service = RegistryItem(
                name=service_data.name,
                display_name=service_data.display_name,
                description=service_data.description,
                build_type=service_data.build_type,
                protocol=service_data.protocol,
                priority=service_data.priority,
                location=service_data.location,
                endpoint=service_data.endpoint,
                port=service_data.port,
                version=service_data.version,
                tags=service_data.tags,
                is_required=service_data.is_required,
                is_enabled=service_data.is_enabled,
                auto_start=service_data.auto_start,
                dependencies=service_data.dependencies,
                service_metadata=service_data.service_metadata,
                config=service_data.config,
                health_check_url=service_data.health_check_url,
                source="api",
                created_by="api_user",  # TODO: Get from authentication
                updated_by="api_user"
            )

            db.add(db_service)
            await db.commit()
            await db.refresh(db_service)

            # Schedule health check if URL is provided
            if service_data.health_check_url:
                background_tasks.add_task(
                    perform_health_check,
                    db_service.id,
                    service_data.health_check_url
                )

            logfire.info(
                "Service created",
                service_id=str(db_service.id),
                service_name=db_service.name
            )

            return convert_db_to_response(db_service)

        except HTTPException:
            raise
        except Exception as e:
            logfire.error("Failed to create service", service_name=service_data.name, error=str(e))
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to create service: {str(e)}")


@router.put(
    "/{service_id}",
    response_model=ServiceResponse,
    summary="Update Service",
    description="Update an existing service"
)
async def update_service(
    service_id: UUID,
    service_data: ServiceUpdate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Update an existing service.

    Args:
        service_id: UUID of the service to update
        service_data: Service update data
        background_tasks: Background task queue
        db: Database session

    Returns:
        Updated service information

    Raises:
        HTTPException: If service is not found
    """
    with logfire.span("Update service", service_id=str(service_id)):
        try:
            # Get existing service
            query = select(RegistryItem).where(
                and_(
                    RegistryItem.id == service_id,
                    RegistryItem.is_active == True
                )
            )
            result = await db.execute(query)
            db_service = result.scalar_one_or_none()

            if not db_service:
                logfire.warning("Service not found for update", service_id=str(service_id))
                raise HTTPException(status_code=404, detail=f"Service {service_id} not found")

            # Update fields that are provided
            update_data = service_data.dict(exclude_unset=True)
            for field, value in update_data.items():
                if hasattr(db_service, field):
                    setattr(db_service, field, value)

            # Update audit fields
            db_service.updated_by = "api_user"  # TODO: Get from authentication
            db_service.updated_at = datetime.utcnow()

            await db.commit()
            await db.refresh(db_service)

            # Schedule health check if URL was updated
            if service_data.health_check_url is not None:
                background_tasks.add_task(
                    perform_health_check,
                    db_service.id,
                    service_data.health_check_url
                )

            logfire.info(
                "Service updated",
                service_id=str(service_id),
                service_name=db_service.name,
                updated_fields=list(update_data.keys())
            )

            return convert_db_to_response(db_service)

        except HTTPException:
            raise
        except Exception as e:
            logfire.error("Failed to update service", service_id=str(service_id), error=str(e))
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to update service: {str(e)}")


@router.delete(
    "/{service_id}",
    status_code=204,
    summary="Delete Service",
    description="Delete a service (soft delete)"
)
async def delete_service(
    service_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a service (soft delete).

    Args:
        service_id: UUID of the service to delete
        db: Database session

    Raises:
        HTTPException: If service is not found
    """
    with logfire.span("Delete service", service_id=str(service_id)):
        try:
            # Get existing service
            query = select(RegistryItem).where(
                and_(
                    RegistryItem.id == service_id,
                    RegistryItem.is_active == True
                )
            )
            result = await db.execute(query)
            db_service = result.scalar_one_or_none()

            if not db_service:
                logfire.warning("Service not found for deletion", service_id=str(service_id))
                raise HTTPException(status_code=404, detail=f"Service {service_id} not found")

            # Perform soft delete
            db_service.soft_delete(deleted_by="api_user")  # TODO: Get from authentication

            await db.commit()

            logfire.info(
                "Service deleted",
                service_id=str(service_id),
                service_name=db_service.name
            )

        except HTTPException:
            raise
        except Exception as e:
            logfire.error("Failed to delete service", service_id=str(service_id), error=str(e))
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to delete service: {str(e)}")


# Health and Status Endpoints

@router.post(
    "/{service_id}/health-check",
    response_model=ServiceHealthResponse,
    summary="Check Service Health",
    description="Perform a health check on a specific service"
)
async def check_service_health(
    service_id: UUID,
    health_check: ServiceHealthCheck = ServiceHealthCheck(),
    db: AsyncSession = Depends(get_db)
):
    """
    Perform a health check on a specific service.

    Args:
        service_id: UUID of the service to check
        health_check: Health check parameters
        db: Database session

    Returns:
        Health check results

    Raises:
        HTTPException: If service is not found
    """
    with logfire.span("Check service health", service_id=str(service_id)):
        try:
            # Get service
            query = select(RegistryItem).where(
                and_(
                    RegistryItem.id == service_id,
                    RegistryItem.is_active == True
                )
            )
            result = await db.execute(query)
            db_service = result.scalar_one_or_none()

            if not db_service:
                logfire.warning("Service not found for health check", service_id=str(service_id))
                raise HTTPException(status_code=404, detail=f"Service {service_id} not found")

            # Perform health check
            health_result = await perform_service_health_check(db_service)

            # Update service with health check results
            if health_result:
                db_service.update_health_status(
                    status=ServiceStatus(health_result["status"]),
                    response_time_ms=health_result.get("response_time_ms")
                )
                await db.commit()

            logfire.info(
                "Health check completed",
                service_id=str(service_id),
                service_name=db_service.name,
                status=health_result.get("status") if health_result else "unknown"
            )

            return ServiceHealthResponse(
                service_id=service_id,
                service_name=db_service.name,
                status=db_service.status,
                response_time_ms=db_service.response_time_ms,
                last_check=datetime.utcnow().isoformat(),
                error_message=health_result.get("error_message") if health_result else None,
                metadata=health_result.get("metadata", {}) if health_result else {}
            )

        except HTTPException:
            raise
        except Exception as e:
            logfire.error("Failed to check service health", service_id=str(service_id), error=str(e))
            raise HTTPException(status_code=500, detail=f"Failed to check service health: {str(e)}")


@router.put(
    "/{service_id}/status",
    response_model=ServiceResponse,
    summary="Update Service Status",
    description="Update the status of a service"
)
async def update_service_status(
    service_id: UUID,
    status_update: ServiceStatusUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update the status of a service.

    Args:
        service_id: UUID of the service to update
        status_update: New status information
        db: Database session

    Returns:
        Updated service information

    Raises:
        HTTPException: If service is not found
    """
    with logfire.span("Update service status", service_id=str(service_id)):
        try:
            # Get service
            query = select(RegistryItem).where(
                and_(
                    RegistryItem.id == service_id,
                    RegistryItem.is_active == True
                )
            )
            result = await db.execute(query)
            db_service = result.scalar_one_or_none()

            if not db_service:
                logfire.warning("Service not found for status update", service_id=str(service_id))
                raise HTTPException(status_code=404, detail=f"Service {service_id} not found")

            # Update status
            old_status = db_service.status
            db_service.update_health_status(status_update.status)
            db_service.updated_by = "api_user"  # TODO: Get from authentication

            await db.commit()
            await db.refresh(db_service)

            logfire.info(
                "Service status updated",
                service_id=str(service_id),
                service_name=db_service.name,
                old_status=old_status,
                new_status=status_update.status,
                reason=status_update.reason
            )

            return convert_db_to_response(db_service)

        except HTTPException:
            raise
        except Exception as e:
            logfire.error("Failed to update service status", service_id=str(service_id), error=str(e))
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to update service status: {str(e)}")


# Discovery Endpoints

@router.post(
    "/discover",
    response_model=ServiceDiscoveryResponse,
    summary="Discover Services",
    description="Trigger service discovery process"
)
async def discover_services(
    discovery_request: ServiceDiscoveryRequest = ServiceDiscoveryRequest(),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger the service discovery process.

    Args:
        discovery_request: Discovery parameters
        background_tasks: Background task queue
        db: Database session

    Returns:
        Discovery results summary
    """
    with logfire.span("Discover services", discovery_types=discovery_request.discovery_types):
        try:
            start_time = datetime.utcnow()

            # Get discovery orchestrator
            orchestrator = await get_discovery_orchestrator()

            # Perform discovery
            discovered_services = await orchestrator.discover_all_services()

            # Process discovered services
            registry = await get_service_registry()
            updated_count = 0
            error_count = 0
            errors = []

            for service_info in discovered_services:
                try:
                    # Register or update service in database
                    await register_discovered_service(service_info, db)
                    updated_count += 1
                except Exception as e:
                    error_count += 1
                    errors.append(f"Failed to register {service_info.name}: {str(e)}")
                    logfire.warning(
                        "Failed to register discovered service",
                        service_name=service_info.name,
                        error=str(e)
                    )

            # Calculate discovery time
            end_time = datetime.utcnow()
            discovery_time_ms = int((end_time - start_time).total_seconds() * 1000)

            # Get summary of discovered services
            services_summary = []
            if discovered_services:
                for service_info in discovered_services[:10]:  # Limit to first 10 for response size
                    try:
                        # Convert to summary format (simplified)
                        summary = ServiceSummary(
                            id=UUID("00000000-0000-0000-0000-000000000000"),  # Placeholder
                            name=service_info.name,
                            display_name=service_info.name,
                            status=ServiceStatus.UNKNOWN,
                            priority=ServicePriority.MEDIUM,
                            build_type=ServiceBuildType.FASTMCP,
                            is_healthy=False,
                            is_critical=False,
                            health_score=0.0,
                            last_health_check=None,
                            updated_at=datetime.utcnow()
                        )
                        services_summary.append(summary)
                    except Exception:
                        pass  # Skip invalid services

            logfire.info(
                "Service discovery completed",
                discovered_count=len(discovered_services),
                updated_count=updated_count,
                error_count=error_count,
                discovery_time_ms=discovery_time_ms
            )

            return ServiceDiscoveryResponse(
                discovered_count=len(discovered_services),
                updated_count=updated_count,
                error_count=error_count,
                discovery_time_ms=discovery_time_ms,
                services=services_summary,
                errors=errors[:10]  # Limit error list
            )

        except Exception as e:
            logfire.error("Failed to discover services", error=str(e))
            raise HTTPException(status_code=500, detail=f"Failed to discover services: {str(e)}")


@router.post(
    "/register",
    response_model=ServiceRegistrationResponse,
    summary="Register Service",
    description="Manually register a service with optional health validation"
)
async def register_service(
    registration_request: ServiceRegistrationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Manually register a service with optional health validation.

    Args:
        registration_request: Service registration data
        background_tasks: Background task queue
        db: Database session

    Returns:
        Registration result

    Raises:
        HTTPException: If registration fails or service already exists
    """
    with logfire.span("Register service", service_name=registration_request.service_data.name):
        try:
            service_data = registration_request.service_data

            # Check if service exists
            existing_query = select(RegistryItem).where(
                and_(
                    RegistryItem.name == service_data.name,
                    RegistryItem.is_active == True
                )
            )
            existing_result = await db.execute(existing_query)
            existing_service = existing_result.scalar_one_or_none()

            was_updated = False

            if existing_service and not registration_request.override_existing:
                logfire.warning("Service already exists", service_name=service_data.name)
                raise HTTPException(
                    status_code=409,
                    detail=f"Service '{service_data.name}' already exists. Use override_existing=true to update."
                )

            if existing_service:
                # Update existing service
                update_data = service_data.dict(exclude_unset=True)
                for field, value in update_data.items():
                    if hasattr(existing_service, field):
                        setattr(existing_service, field, value)

                existing_service.updated_by = "api_user"
                existing_service.updated_at = datetime.utcnow()
                db_service = existing_service
                was_updated = True
            else:
                # Create new service
                db_service = RegistryItem(
                    **service_data.dict(),
                    source="manual_registration",
                    created_by="api_user",
                    updated_by="api_user"
                )
                db.add(db_service)

            await db.commit()
            await db.refresh(db_service)

            # Perform health check if requested
            health_check_result = None
            if registration_request.validate_health and db_service.health_check_url:
                health_check_result = await perform_service_health_check(db_service)

            logfire.info(
                "Service registered",
                service_id=str(db_service.id),
                service_name=db_service.name,
                was_updated=was_updated
            )

            return ServiceRegistrationResponse(
                service=convert_db_to_response(db_service),
                was_updated=was_updated,
                health_check_result=health_check_result
            )

        except HTTPException:
            raise
        except Exception as e:
            logfire.error("Failed to register service", service_name=registration_request.service_data.name, error=str(e))
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to register service: {str(e)}")


# Configuration Management Endpoints

@router.get(
    "/{service_id}/config",
    response_model=ServiceConfig,
    summary="Get Service Configuration",
    description="Get the current configuration of a service"
)
async def get_service_config(
    service_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get the current configuration of a service."""
    with logfire.span("Get service config", service_id=str(service_id)):
        try:
            query = select(RegistryItem).where(
                and_(
                    RegistryItem.id == service_id,
                    RegistryItem.is_active == True
                )
            )
            result = await db.execute(query)
            service = result.scalar_one_or_none()

            if not service:
                raise HTTPException(status_code=404, detail=f"Service {service_id} not found")

            return ServiceConfig(
                config=service.config or {},
                version=service.version,
                description=f"Configuration for {service.name}"
            )

        except HTTPException:
            raise
        except Exception as e:
            logfire.error("Failed to get service config", service_id=str(service_id), error=str(e))
            raise HTTPException(status_code=500, detail=f"Failed to get service config: {str(e)}")


@router.put(
    "/{service_id}/config",
    response_model=ServiceConfig,
    summary="Update Service Configuration",
    description="Update the configuration of a service"
)
async def update_service_config(
    service_id: UUID,
    config_update: ServiceConfigUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update the configuration of a service."""
    with logfire.span("Update service config", service_id=str(service_id)):
        try:
            query = select(RegistryItem).where(
                and_(
                    RegistryItem.id == service_id,
                    RegistryItem.is_active == True
                )
            )
            result = await db.execute(query)
            service = result.scalar_one_or_none()

            if not service:
                raise HTTPException(status_code=404, detail=f"Service {service_id} not found")

            # Update configuration
            if config_update.merge_with_existing and service.config:
                # Merge with existing config
                new_config = {**service.config, **config_update.config}
            else:
                # Replace entire config
                new_config = config_update.config

            service.config = new_config
            service.updated_by = "api_user"
            service.updated_at = datetime.utcnow()

            await db.commit()

            logfire.info(
                "Service config updated",
                service_id=str(service_id),
                service_name=service.name,
                merged=config_update.merge_with_existing
            )

            return ServiceConfig(
                config=new_config,
                version=service.version,
                description=config_update.description or f"Updated configuration for {service.name}"
            )

        except HTTPException:
            raise
        except Exception as e:
            logfire.error("Failed to update service config", service_id=str(service_id), error=str(e))
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to update service config: {str(e)}")


# Bulk Operations

@router.post(
    "/bulk",
    response_model=BulkOperationResponse,
    summary="Bulk Operations",
    description="Perform bulk operations on multiple services"
)
async def bulk_operations(
    bulk_request: BulkOperationRequest,
    db: AsyncSession = Depends(get_db)
):
    """Perform bulk operations on multiple services."""
    with logfire.span("Bulk operations", operation=bulk_request.operation, count=len(bulk_request.service_ids)):
        try:
            results = []
            successful = 0
            failed = 0
            errors = []

            for service_id in bulk_request.service_ids:
                try:
                    query = select(RegistryItem).where(
                        and_(
                            RegistryItem.id == service_id,
                            RegistryItem.is_active == True
                        )
                    )
                    result = await db.execute(query)
                    service = result.scalar_one_or_none()

                    if not service:
                        failed += 1
                        errors.append(f"Service {service_id} not found")
                        results.append({
                            "service_id": str(service_id),
                            "success": False,
                            "error": "Service not found"
                        })
                        continue

                    # Perform operation based on type
                    if bulk_request.operation == "enable":
                        service.is_enabled = True
                    elif bulk_request.operation == "disable":
                        service.is_enabled = False
                    elif bulk_request.operation == "delete":
                        service.soft_delete(deleted_by="api_user")
                    else:
                        failed += 1
                        errors.append(f"Unknown operation: {bulk_request.operation}")
                        results.append({
                            "service_id": str(service_id),
                            "success": False,
                            "error": f"Unknown operation: {bulk_request.operation}"
                        })
                        continue

                    service.updated_by = "api_user"
                    service.updated_at = datetime.utcnow()
                    successful += 1
                    results.append({
                        "service_id": str(service_id),
                        "success": True,
                        "message": f"Operation {bulk_request.operation} completed"
                    })

                except Exception as e:
                    failed += 1
                    error_msg = f"Failed to {bulk_request.operation} service {service_id}: {str(e)}"
                    errors.append(error_msg)
                    results.append({
                        "service_id": str(service_id),
                        "success": False,
                        "error": str(e)
                    })

            await db.commit()

            logfire.info(
                "Bulk operation completed",
                operation=bulk_request.operation,
                total=len(bulk_request.service_ids),
                successful=successful,
                failed=failed
            )

            return BulkOperationResponse(
                total_requested=len(bulk_request.service_ids),
                successful=successful,
                failed=failed,
                results=results,
                errors=errors
            )

        except Exception as e:
            logfire.error("Failed to perform bulk operations", operation=bulk_request.operation, error=str(e))
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to perform bulk operations: {str(e)}")


# Helper Functions

async def perform_health_check(service_id: UUID, health_check_url: str):
    """Background task to perform health check."""
    try:
        # This would normally use the health probe factory
        # For now, we'll implement a simple HTTP check
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(health_check_url, timeout=5) as response:
                if response.status < 300:
                    status = ServiceStatus.HEALTHY
                else:
                    status = ServiceStatus.UNHEALTHY

        # Update database (this would need a new session)
        logfire.info("Health check completed", service_id=str(service_id), status=status)

    except Exception as e:
        logfire.error("Health check failed", service_id=str(service_id), error=str(e))


async def perform_service_health_check(service: RegistryItem) -> Optional[Dict[str, Any]]:
    """Perform health check on a service."""
    try:
        if not service.health_check_url:
            return None

        import aiohttp
        start_time = datetime.utcnow()

        async with aiohttp.ClientSession() as session:
            async with session.get(service.health_check_url, timeout=5) as response:
                end_time = datetime.utcnow()
                response_time_ms = int((end_time - start_time).total_seconds() * 1000)

                if response.status < 300:
                    status = "healthy"
                else:
                    status = "unhealthy"

                return {
                    "status": status,
                    "response_time_ms": response_time_ms,
                    "metadata": {
                        "http_status": response.status,
                        "url": service.health_check_url
                    }
                }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error_message": str(e),
            "metadata": {
                "url": service.health_check_url
            }
        }


async def register_discovered_service(service_info, db: AsyncSession):
    """Register a discovered service in the database."""
    try:
        # Check if service already exists
        existing_query = select(RegistryItem).where(
            and_(
                RegistryItem.name == service_info.name,
                RegistryItem.is_active == True
            )
        )
        existing_result = await db.execute(existing_query)
        existing_service = existing_result.scalar_one_or_none()

        if existing_service:
            # Update existing service
            existing_service.location = getattr(service_info, 'location', existing_service.location)
            existing_service.last_seen = datetime.utcnow().isoformat()
            existing_service.source = getattr(service_info, 'source', 'discovery')
            existing_service.updated_at = datetime.utcnow()
        else:
            # Create new service
            new_service = RegistryItem(
                name=service_info.name,
                display_name=getattr(service_info, 'display_name', service_info.name),
                build_type=getattr(service_info, 'build_type', ServiceBuildType.FASTMCP),
                location=getattr(service_info, 'location', None),
                source=getattr(service_info, 'source', 'discovery'),
                last_seen=datetime.utcnow().isoformat(),
                created_by="discovery_engine",
                updated_by="discovery_engine"
            )
            db.add(new_service)

        await db.commit()

    except Exception as e:
        await db.rollback()
        raise e
