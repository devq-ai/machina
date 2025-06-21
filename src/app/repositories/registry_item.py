"""
Registry Item Repository for Machina Registry Service

This module provides the RegistryItemRepository class which extends the BaseRepository
with domain-specific operations for MCP service registry management. It includes
specialized queries, filtering, and operations tailored to the registry item domain.

Features:
- Domain-specific query methods for service discovery
- Health status filtering and monitoring operations
- Dependency tracking and resolution queries
- Service type and protocol filtering
- Tag-based searching and categorization
- Performance optimized queries for registry operations
"""

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

import logfire
from sqlalchemy import and_, or_, select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.registry_item import (
    RegistryItem,
    ServiceBuildType,
    ServiceProtocol,
    ServiceStatus,
    ServicePriority
)
from app.repositories.base import BaseRepository
from app.core.exceptions import DatabaseError, NotFoundError


class RegistryItemRepository(BaseRepository[RegistryItem]):
    """
    Repository for registry item domain operations.

    Provides specialized database operations for MCP service registry management,
    including service discovery, health monitoring, and dependency resolution.
    """

    def __init__(self):
        """Initialize the registry item repository."""
        super().__init__(RegistryItem)

    async def get_by_name(
        self,
        db: AsyncSession,
        name: str,
        include_deleted: bool = False
    ) -> Optional[RegistryItem]:
        """
        Get a registry item by service name.

        Args:
            db: Database session
            name: Service name to search for
            include_deleted: Whether to include soft-deleted records

        Returns:
            RegistryItem or None if not found
        """
        return await self.get_by_field(db, "name", name, include_deleted=include_deleted)

    async def get_by_build_type(
        self,
        db: AsyncSession,
        build_type: ServiceBuildType,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False
    ) -> List[RegistryItem]:
        """
        Get registry items by build type.

        Args:
            db: Database session
            build_type: Service build type to filter by
            skip: Number of records to skip
            limit: Maximum number of records to return
            include_deleted: Whether to include soft-deleted records

        Returns:
            List of registry items matching the build type
        """
        filters = {"build_type": build_type}
        return await self.get_multi(
            db=db,
            skip=skip,
            limit=limit,
            include_deleted=include_deleted,
            filters=filters,
            order_by="name"
        )

    async def get_by_status(
        self,
        db: AsyncSession,
        status: ServiceStatus,
        skip: int = 0,
        limit: int = 100
    ) -> List[RegistryItem]:
        """
        Get registry items by health status.

        Args:
            db: Database session
            status: Service status to filter by
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of registry items with the specified status
        """
        filters = {"status": status}
        return await self.get_multi(
            db=db,
            skip=skip,
            limit=limit,
            include_deleted=False,
            filters=filters,
            order_by="last_health_check",
            order_desc=True
        )

    async def get_healthy_services(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100
    ) -> List[RegistryItem]:
        """
        Get all healthy and active services.

        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of healthy registry items
        """
        try:
            with logfire.span("Get healthy services"):
                query = select(RegistryItem).where(
                    and_(
                        RegistryItem.status == ServiceStatus.HEALTHY,
                        RegistryItem.is_active.is_(True),
                        RegistryItem.deleted_at.is_(None)
                    )
                ).order_by(RegistryItem.name).offset(skip).limit(limit)

                result = await db.execute(query)
                services = result.scalars().all()

                logfire.debug(f"Found {len(services)} healthy services")
                return list(services)

        except Exception as e:
            logfire.error("Error getting healthy services", error=str(e))
            raise DatabaseError(
                operation="get_healthy_services",
                message=f"Failed to get healthy services: {str(e)}",
                cause=e
            )

    async def get_required_services(
        self,
        db: AsyncSession,
        include_unhealthy: bool = False
    ) -> List[RegistryItem]:
        """
        Get all required services for system operation.

        Args:
            db: Database session
            include_unhealthy: Whether to include unhealthy required services

        Returns:
            List of required registry items
        """
        try:
            with logfire.span("Get required services"):
                conditions = [
                    RegistryItem.is_required.is_(True),
                    RegistryItem.deleted_at.is_(None)
                ]

                if not include_unhealthy:
                    conditions.append(RegistryItem.status == ServiceStatus.HEALTHY)

                query = select(RegistryItem).where(
                    and_(*conditions)
                ).order_by(RegistryItem.priority.desc(), RegistryItem.name)

                result = await db.execute(query)
                services = result.scalars().all()

                logfire.debug(f"Found {len(services)} required services")
                return list(services)

        except Exception as e:
            logfire.error("Error getting required services", error=str(e))
            raise DatabaseError(
                operation="get_required_services",
                message=f"Failed to get required services: {str(e)}",
                cause=e
            )

    async def get_by_tags(
        self,
        db: AsyncSession,
        tags: List[str],
        match_all: bool = False,
        skip: int = 0,
        limit: int = 100
    ) -> List[RegistryItem]:
        """
        Get registry items by tags.

        Args:
            db: Database session
            tags: List of tags to search for
            match_all: If True, service must have all tags; if False, any tag matches
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of registry items matching the tag criteria
        """
        try:
            with logfire.span("Get services by tags"):
                query = select(RegistryItem).where(
                    RegistryItem.deleted_at.is_(None)
                )

                if match_all:
                    # Service must have all specified tags
                    for tag in tags:
                        query = query.where(RegistryItem.tags.contains([tag]))
                else:
                    # Service must have at least one of the specified tags
                    tag_conditions = [RegistryItem.tags.contains([tag]) for tag in tags]
                    query = query.where(or_(*tag_conditions))

                query = query.order_by(RegistryItem.name).offset(skip).limit(limit)

                result = await db.execute(query)
                services = result.scalars().all()

                logfire.debug(
                    f"Found {len(services)} services with tags",
                    tags=tags,
                    match_all=match_all
                )
                return list(services)

        except Exception as e:
            logfire.error("Error getting services by tags", error=str(e))
            raise DatabaseError(
                operation="get_by_tags",
                message=f"Failed to get services by tags: {str(e)}",
                cause=e
            )

    async def get_dependencies(
        self,
        db: AsyncSession,
        service_name: str
    ) -> Tuple[List[RegistryItem], List[RegistryItem]]:
        """
        Get dependencies and dependents for a service.

        Args:
            db: Database session
            service_name: Name of the service to get dependencies for

        Returns:
            Tuple of (dependencies, dependents) lists

        Raises:
            NotFoundError: If service is not found
        """
        try:
            with logfire.span("Get service dependencies"):
                # Get the main service
                service = await self.get_by_name(db, service_name)
                if not service:
                    raise NotFoundError(
                        resource_type="RegistryItem",
                        identifier=service_name
                    )

                dependencies = []
                dependents = []

                # Get dependencies (services this service depends on)
                if service.dependencies:
                    dep_query = select(RegistryItem).where(
                        and_(
                            RegistryItem.name.in_(service.dependencies),
                            RegistryItem.deleted_at.is_(None)
                        )
                    )
                    dep_result = await db.execute(dep_query)
                    dependencies = list(dep_result.scalars().all())

                # Get dependents (services that depend on this service)
                if service.dependents:
                    dependent_query = select(RegistryItem).where(
                        and_(
                            RegistryItem.name.in_(service.dependents),
                            RegistryItem.deleted_at.is_(None)
                        )
                    )
                    dependent_result = await db.execute(dependent_query)
                    dependents = list(dependent_result.scalars().all())

                logfire.debug(
                    "Retrieved service dependencies",
                    service_name=service_name,
                    dependencies_count=len(dependencies),
                    dependents_count=len(dependents)
                )

                return dependencies, dependents

        except NotFoundError:
            raise
        except Exception as e:
            logfire.error("Error getting service dependencies", error=str(e))
            raise DatabaseError(
                operation="get_dependencies",
                message=f"Failed to get dependencies for {service_name}: {str(e)}",
                cause=e
            )

    async def search_services(
        self,
        db: AsyncSession,
        search_term: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[RegistryItem]:
        """
        Search services by name, description, or tags.

        Args:
            db: Database session
            search_term: Term to search for
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of matching registry items
        """
        search_fields = ["name", "display_name", "description"]
        return await self.search(
            db=db,
            search_term=search_term,
            search_fields=search_fields,
            skip=skip,
            limit=limit,
            include_deleted=False
        )

    async def get_stale_services(
        self,
        db: AsyncSession,
        stale_hours: int = 24
    ) -> List[RegistryItem]:
        """
        Get services that haven't been seen or health checked recently.

        Args:
            db: Database session
            stale_hours: Number of hours to consider a service stale

        Returns:
            List of stale registry items
        """
        try:
            with logfire.span("Get stale services"):
                cutoff_time = datetime.utcnow() - timedelta(hours=stale_hours)
                cutoff_iso = cutoff_time.isoformat()

                query = select(RegistryItem).where(
                    and_(
                        RegistryItem.deleted_at.is_(None),
                        or_(
                            RegistryItem.last_seen < cutoff_iso,
                            RegistryItem.last_health_check < cutoff_iso,
                            RegistryItem.last_seen.is_(None),
                            RegistryItem.last_health_check.is_(None)
                        )
                    )
                ).order_by(RegistryItem.last_seen.desc().nullslast())

                result = await db.execute(query)
                services = result.scalars().all()

                logfire.debug(
                    f"Found {len(services)} stale services",
                    stale_hours=stale_hours
                )
                return list(services)

        except Exception as e:
            logfire.error("Error getting stale services", error=str(e))
            raise DatabaseError(
                operation="get_stale_services",
                message=f"Failed to get stale services: {str(e)}",
                cause=e
            )

    async def get_service_statistics(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Get comprehensive statistics about the service registry.

        Args:
            db: Database session

        Returns:
            Dictionary containing various statistics
        """
        try:
            with logfire.span("Get service statistics"):
                # Total services
                total_count = await self.count(db, include_deleted=False)

                # Count by status
                status_counts = {}
                for status in ServiceStatus:
                    count = await self.count(db, filters={"status": status})
                    status_counts[status.value] = count

                # Count by build type
                build_type_counts = {}
                for build_type in ServiceBuildType:
                    count = await self.count(db, filters={"build_type": build_type})
                    build_type_counts[build_type.value] = count

                # Count by priority
                priority_counts = {}
                for priority in ServicePriority:
                    count = await self.count(db, filters={"priority": priority})
                    priority_counts[priority.value] = count

                # Required services count
                required_count = await self.count(db, filters={"is_required": True})

                # Active services count
                active_count = await self.count(db, filters={"is_active": True})

                # Health score average
                health_query = select(
                    func.avg(
                        func.cast(RegistryItem.success_count, db.bind.dialect.FLOAT) /
                        func.nullif(RegistryItem.success_count + RegistryItem.failure_count, 0)
                    )
                ).where(
                    and_(
                        RegistryItem.deleted_at.is_(None),
                        RegistryItem.success_count + RegistryItem.failure_count > 0
                    )
                )
                health_result = await db.execute(health_query)
                avg_health_score = health_result.scalar() or 0.0

                stats = {
                    "total_services": total_count,
                    "active_services": active_count,
                    "required_services": required_count,
                    "average_health_score": round(avg_health_score, 3),
                    "status_distribution": status_counts,
                    "build_type_distribution": build_type_counts,
                    "priority_distribution": priority_counts,
                    "last_updated": datetime.utcnow().isoformat()
                }

                logfire.info("Generated service statistics", **stats)
                return stats

        except Exception as e:
            logfire.error("Error getting service statistics", error=str(e))
            raise DatabaseError(
                operation="get_service_statistics",
                message=f"Failed to get service statistics: {str(e)}",
                cause=e
            )

    async def update_health_status(
        self,
        db: AsyncSession,
        service_name: str,
        status: ServiceStatus,
        response_time_ms: Optional[int] = None,
        commit: bool = True
    ) -> bool:
        """
        Update the health status of a service.

        Args:
            db: Database session
            service_name: Name of the service to update
            status: New health status
            response_time_ms: Optional response time in milliseconds
            commit: Whether to commit the transaction

        Returns:
            True if service was updated, False if not found
        """
        try:
            with logfire.span("Update service health status"):
                service = await self.get_by_name(db, service_name)
                if not service:
                    return False

                service.update_health_status(status, response_time_ms)

                if commit:
                    await db.commit()

                return True

        except Exception as e:
            await db.rollback()
            logfire.error("Error updating service health status", error=str(e))
            raise DatabaseError(
                operation="update_health_status",
                message=f"Failed to update health status for {service_name}: {str(e)}",
                cause=e
            )

    async def bulk_update_last_seen(
        self,
        db: AsyncSession,
        service_names: List[str],
        timestamp: Optional[datetime] = None,
        commit: bool = True
    ) -> int:
        """
        Bulk update the last_seen timestamp for multiple services.

        Args:
            db: Database session
            service_names: List of service names to update
            timestamp: Timestamp to set (defaults to current time)
            commit: Whether to commit the transaction

        Returns:
            Number of services updated
        """
        try:
            with logfire.span("Bulk update last seen"):
                if not service_names:
                    return 0

                if timestamp is None:
                    timestamp = datetime.utcnow()

                # Use bulk update for better performance
                stmt = (
                    RegistryItem.__table__.update()
                    .where(RegistryItem.name.in_(service_names))
                    .values(
                        last_seen=timestamp.isoformat(),
                        updated_at=timestamp
                    )
                )

                result = await db.execute(stmt)
                updated_count = result.rowcount

                if commit:
                    await db.commit()

                logfire.debug(
                    f"Bulk updated last_seen for {updated_count} services",
                    service_count=len(service_names),
                    updated_count=updated_count
                )

                return updated_count

        except Exception as e:
            await db.rollback()
            logfire.error("Error bulk updating last seen", error=str(e))
            raise DatabaseError(
                operation="bulk_update_last_seen",
                message=f"Failed to bulk update last seen: {str(e)}",
                cause=e
            )
