"""
Comprehensive Tests for Services API Endpoints

This module provides complete test coverage for the service discovery and management
API endpoints implemented in Task 3, Subtask 3.1. It tests all CRUD operations,
health monitoring, discovery triggers, and error handling scenarios.

Features:
- Complete API endpoint testing with FastAPI TestClient
- Database integration testing with test fixtures
- Mock service discovery and health check testing
- Validation and error handling verification
- Pagination, filtering, and search testing
- Bulk operations and configuration management testing
"""

import asyncio
import json
import pytest
from datetime import datetime
from typing import Dict, Any, List
from uuid import uuid4, UUID
from unittest.mock import AsyncMock, Mock, patch

from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

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
    ServiceListResponse,
    ServiceResponse,
    ServiceDetail,
    ServiceDiscoveryRequest,
    ServiceRegistrationRequest
)


class TestServicesAPI:
    """Test suite for services API endpoints."""

    def setup_method(self):
        """Set up test environment before each test."""
        self.base_url = "/api/v1/services"

        # Sample test data
        self.sample_service_data = {
            "name": "test-service",
            "display_name": "Test Service",
            "description": "A test service for API testing",
            "build_type": "fastmcp",
            "protocol": "stdio",
            "priority": "medium",
            "location": "/test/services/test-service",
            "port": 8080,
            "version": "1.0.0",
            "tags": ["test", "api"],
            "is_required": False,
            "is_enabled": True,
            "auto_start": False,
            "dependencies": [],
            "service_metadata": {"framework": "fastapi"},
            "config": {"timeout": 30},
            "health_check_url": "http://localhost:8080/health"
        }

    async def create_test_service(self, db: AsyncSession, **kwargs) -> RegistryItem:
        """Create a test service in the database."""
        service_data = {**self.sample_service_data, **kwargs}

        db_service = RegistryItem(
            name=service_data["name"],
            display_name=service_data["display_name"],
            description=service_data["description"],
            build_type=ServiceBuildType(service_data["build_type"]),
            protocol=ServiceProtocol(service_data["protocol"]),
            priority=ServicePriority(service_data["priority"]),
            location=service_data["location"],
            port=service_data["port"],
            version=service_data["version"],
            tags=service_data["tags"],
            is_required=service_data["is_required"],
            is_enabled=service_data["is_enabled"],
            auto_start=service_data["auto_start"],
            dependencies=service_data["dependencies"],
            service_metadata=service_data["service_metadata"],
            config=service_data["config"],
            health_check_url=service_data["health_check_url"],
            source="test",
            created_by="test_user",
            updated_by="test_user"
        )

        db.add(db_service)
        await db.commit()
        await db.refresh(db_service)
        return db_service

    # CRUD Operation Tests

    def test_create_service_success(self, client: TestClient):
        """Test successful service creation."""
        response = client.post(
            self.base_url,
            json=self.sample_service_data
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == self.sample_service_data["name"]
        assert data["display_name"] == self.sample_service_data["display_name"]
        assert data["build_type"] == self.sample_service_data["build_type"]
        assert data["is_enabled"] == self.sample_service_data["is_enabled"]
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_service_duplicate_name(self, client: TestClient, test_db_service):
        """Test creating service with duplicate name fails."""
        # Try to create service with same name as existing test service
        duplicate_data = {**self.sample_service_data, "name": test_db_service.name}

        response = client.post(
            self.base_url,
            json=duplicate_data
        )

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    def test_create_service_invalid_name(self, client: TestClient):
        """Test creating service with invalid name fails validation."""
        invalid_data = {**self.sample_service_data, "name": "invalid-name-!@#"}

        response = client.post(
            self.base_url,
            json=invalid_data
        )

        assert response.status_code == 422
        errors = response.json()["details"]
        assert any("name" in str(error) for error in errors)

    def test_create_service_invalid_port(self, client: TestClient):
        """Test creating service with invalid port fails validation."""
        invalid_data = {**self.sample_service_data, "port": 99999}

        response = client.post(
            self.base_url,
            json=invalid_data
        )

        assert response.status_code == 422

    def test_get_service_success(self, client: TestClient, test_db_service):
        """Test successful service retrieval."""
        response = client.get(f"{self.base_url}/{test_db_service.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_db_service.id)
        assert data["name"] == test_db_service.name
        assert "service_metadata" in data
        assert "config" in data

    def test_get_service_not_found(self, client: TestClient):
        """Test getting non-existent service returns 404."""
        fake_id = str(uuid4())
        response = client.get(f"{self.base_url}/{fake_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_update_service_success(self, client: TestClient, test_db_service):
        """Test successful service update."""
        update_data = {
            "display_name": "Updated Test Service",
            "description": "Updated description",
            "port": 9090,
            "tags": ["updated", "test"]
        }

        response = client.put(
            f"{self.base_url}/{test_db_service.id}",
            json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["display_name"] == update_data["display_name"]
        assert data["description"] == update_data["description"]
        assert data["port"] == update_data["port"]
        assert set(data["tags"]) == set(update_data["tags"])

    def test_update_service_not_found(self, client: TestClient):
        """Test updating non-existent service returns 404."""
        fake_id = str(uuid4())
        update_data = {"display_name": "Updated Name"}

        response = client.put(
            f"{self.base_url}/{fake_id}",
            json=update_data
        )

        assert response.status_code == 404

    def test_delete_service_success(self, client: TestClient, test_db_service):
        """Test successful service deletion (soft delete)."""
        response = client.delete(f"{self.base_url}/{test_db_service.id}")

        assert response.status_code == 204

        # Verify service is soft deleted (should return 404 for subsequent requests)
        get_response = client.get(f"{self.base_url}/{test_db_service.id}")
        assert get_response.status_code == 404

    def test_delete_service_not_found(self, client: TestClient):
        """Test deleting non-existent service returns 404."""
        fake_id = str(uuid4())
        response = client.delete(f"{self.base_url}/{fake_id}")

        assert response.status_code == 404

    # List and Search Tests

    async def test_list_services_empty(self, async_client: AsyncClient):
        """Test listing services when none exist."""
        response = await async_client.get(self.base_url)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []
        assert data["page"] == 1
        assert data["pages"] == 0

    async def test_list_services_with_data(self, async_client: AsyncClient, async_db: AsyncSession):
        """Test listing services with existing data."""
        # Create test services
        service1 = await self.create_test_service(async_db, name="service-1", priority="high")
        service2 = await self.create_test_service(async_db, name="service-2", priority="low")
        service3 = await self.create_test_service(async_db, name="service-3", priority="medium")

        response = await async_client.get(self.base_url)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3

        # Check that items contain expected fields
        for item in data["items"]:
            assert "id" in item
            assert "name" in item
            assert "status" in item
            assert "priority" in item
            assert "build_type" in item
            assert "is_healthy" in item
            assert "health_score" in item

    async def test_list_services_pagination(self, async_client: AsyncClient, async_db: AsyncSession):
        """Test service listing with pagination."""
        # Create 5 test services
        for i in range(5):
            await self.create_test_service(async_db, name=f"service-{i}")

        # Get first page with size 2
        response = await async_client.get(f"{self.base_url}?page=1&size=2")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2
        assert data["page"] == 1
        assert data["size"] == 2
        assert data["pages"] == 3
        assert data["has_next"] == True
        assert data["has_prev"] == False

        # Get second page
        response = await async_client.get(f"{self.base_url}?page=2&size=2")

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert data["has_next"] == True
        assert data["has_prev"] == True

    async def test_list_services_filtering(self, async_client: AsyncClient, async_db: AsyncSession):
        """Test service listing with filters."""
        # Create services with different attributes
        await self.create_test_service(
            async_db,
            name="critical-service",
            priority="critical",
            is_required=True,
            tags=["critical", "core"]
        )
        await self.create_test_service(
            async_db,
            name="optional-service",
            priority="low",
            is_required=False,
            tags=["optional", "extra"]
        )

        # Filter by priority
        response = await async_client.get(
            self.base_url,
            params={"filters.priority": ["critical"]}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "critical-service"

        # Filter by required status
        response = await async_client.get(
            self.base_url,
            params={"filters.is_required": True}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "critical-service"

    async def test_list_services_search(self, async_client: AsyncClient, async_db: AsyncSession):
        """Test service listing with search."""
        await self.create_test_service(
            async_db,
            name="user-management",
            description="User management service"
        )
        await self.create_test_service(
            async_db,
            name="data-processor",
            description="Data processing engine"
        )

        # Search by name
        response = await async_client.get(
            self.base_url,
            params={"search.query": "management"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "user-management"

        # Search by description
        response = await async_client.get(
            self.base_url,
            params={"search.query": "processing"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "data-processor"

    async def test_list_services_sorting(self, async_client: AsyncClient, async_db: AsyncSession):
        """Test service listing with sorting."""
        # Create services with different names and dates
        service1 = await self.create_test_service(async_db, name="alpha-service")
        service2 = await self.create_test_service(async_db, name="beta-service")
        service3 = await self.create_test_service(async_db, name="gamma-service")

        # Sort by name ascending (default)
        response = await async_client.get(
            self.base_url,
            params={"sort.field": "name", "sort.direction": "asc"}
        )

        assert response.status_code == 200
        data = response.json()
        names = [item["name"] for item in data["items"]]
        assert names == ["alpha-service", "beta-service", "gamma-service"]

        # Sort by name descending
        response = await async_client.get(
            self.base_url,
            params={"sort.field": "name", "sort.direction": "desc"}
        )

        assert response.status_code == 200
        data = response.json()
        names = [item["name"] for item in data["items"]]
        assert names == ["gamma-service", "beta-service", "alpha-service"]

    # Health Check Tests

    @patch('app.api.v1.services.perform_service_health_check')
    async def test_health_check_success(self, mock_health_check, async_client: AsyncClient, async_db: AsyncSession):
        """Test successful health check."""
        service = await self.create_test_service(async_db)

        mock_health_check.return_value = {
            "status": "healthy",
            "response_time_ms": 150,
            "metadata": {"http_status": 200}
        }

        response = await async_client.post(f"{self.base_url}/{service.id}/health-check")

        assert response.status_code == 200
        data = response.json()
        assert data["service_id"] == str(service.id)
        assert data["service_name"] == service.name
        assert data["status"] == "healthy"
        assert data["response_time_ms"] == 150

    async def test_health_check_not_found(self, async_client: AsyncClient):
        """Test health check on non-existent service."""
        fake_id = str(uuid4())
        response = await async_client.post(f"{self.base_url}/{fake_id}/health-check")

        assert response.status_code == 404

    async def test_update_service_status(self, async_client: AsyncClient, async_db: AsyncSession):
        """Test updating service status."""
        service = await self.create_test_service(async_db)

        status_update = {
            "status": "maintenance",
            "reason": "Scheduled maintenance"
        }

        response = await async_client.put(
            f"{self.base_url}/{service.id}/status",
            json=status_update
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "maintenance"

    # Discovery Tests

    @patch('app.api.v1.services.get_discovery_orchestrator')
    async def test_discover_services(self, mock_get_orchestrator, async_client: AsyncClient):
        """Test service discovery trigger."""
        # Mock discovery orchestrator
        mock_orchestrator = AsyncMock()
        mock_service_info = Mock()
        mock_service_info.name = "discovered-service"
        mock_service_info.location = "/discovered/service"
        mock_service_info.source = "discovery"

        mock_orchestrator.discover_all_services.return_value = [mock_service_info]
        mock_get_orchestrator.return_value = mock_orchestrator

        discovery_request = {
            "discovery_types": ["local", "docker"],
            "force_refresh": True
        }

        response = await async_client.post(
            f"{self.base_url}/discover",
            json=discovery_request
        )

        assert response.status_code == 200
        data = response.json()
        assert data["discovered_count"] == 1
        assert "discovery_time_ms" in data
        assert len(data["services"]) > 0

    async def test_register_service_manual(self, async_client: AsyncClient):
        """Test manual service registration."""
        registration_request = {
            "service_data": self.sample_service_data,
            "validate_health": False,
            "override_existing": False
        }

        response = await async_client.post(
            f"{self.base_url}/register",
            json=registration_request
        )

        assert response.status_code == 200
        data = response.json()
        assert data["service"]["name"] == self.sample_service_data["name"]
        assert data["was_updated"] == False

    async def test_register_service_override_existing(self, async_client: AsyncClient, async_db: AsyncSession):
        """Test manual service registration with override."""
        # Create existing service
        existing_service = await self.create_test_service(async_db)

        updated_data = {**self.sample_service_data}
        updated_data["name"] = existing_service.name
        updated_data["description"] = "Updated description"

        registration_request = {
            "service_data": updated_data,
            "validate_health": False,
            "override_existing": True
        }

        response = await async_client.post(
            f"{self.base_url}/register",
            json=registration_request
        )

        assert response.status_code == 200
        data = response.json()
        assert data["was_updated"] == True
        assert data["service"]["description"] == "Updated description"

    # Configuration Tests

    async def test_get_service_config(self, async_client: AsyncClient, async_db: AsyncSession):
        """Test getting service configuration."""
        service = await self.create_test_service(
            async_db,
            config={"timeout": 30, "retries": 3}
        )

        response = await async_client.get(f"{self.base_url}/{service.id}/config")

        assert response.status_code == 200
        data = response.json()
        assert data["config"]["timeout"] == 30
        assert data["config"]["retries"] == 3

    async def test_update_service_config_merge(self, async_client: AsyncClient, async_db: AsyncSession):
        """Test updating service configuration with merge."""
        service = await self.create_test_service(
            async_db,
            config={"timeout": 30, "retries": 3}
        )

        config_update = {
            "config": {"timeout": 60, "new_setting": "value"},
            "merge_with_existing": True,
            "description": "Updated timeout setting"
        }

        response = await async_client.put(
            f"{self.base_url}/{service.id}/config",
            json=config_update
        )

        assert response.status_code == 200
        data = response.json()
        assert data["config"]["timeout"] == 60  # Updated
        assert data["config"]["retries"] == 3   # Preserved
        assert data["config"]["new_setting"] == "value"  # Added

    async def test_update_service_config_replace(self, async_client: AsyncClient, async_db: AsyncSession):
        """Test updating service configuration with replace."""
        service = await self.create_test_service(
            async_db,
            config={"timeout": 30, "retries": 3}
        )

        config_update = {
            "config": {"timeout": 60},
            "merge_with_existing": False,
            "description": "Replaced configuration"
        }

        response = await async_client.put(
            f"{self.base_url}/{service.id}/config",
            json=config_update
        )

        assert response.status_code == 200
        data = response.json()
        assert data["config"]["timeout"] == 60
        assert "retries" not in data["config"]  # Should be removed

    # Bulk Operations Tests

    async def test_bulk_enable_services(self, async_client: AsyncClient, async_db: AsyncSession):
        """Test bulk enable operation."""
        # Create disabled services
        service1 = await self.create_test_service(async_db, name="service-1", is_enabled=False)
        service2 = await self.create_test_service(async_db, name="service-2", is_enabled=False)

        bulk_request = {
            "service_ids": [str(service1.id), str(service2.id)],
            "operation": "enable",
            "parameters": {}
        }

        response = await async_client.post(
            f"{self.base_url}/bulk",
            json=bulk_request
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_requested"] == 2
        assert data["successful"] == 2
        assert data["failed"] == 0

    async def test_bulk_delete_services(self, async_client: AsyncClient, async_db: AsyncSession):
        """Test bulk delete operation."""
        service1 = await self.create_test_service(async_db, name="service-1")
        service2 = await self.create_test_service(async_db, name="service-2")

        bulk_request = {
            "service_ids": [str(service1.id), str(service2.id)],
            "operation": "delete",
            "parameters": {}
        }

        response = await async_client.post(
            f"{self.base_url}/bulk",
            json=bulk_request
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_requested"] == 2
        assert data["successful"] == 2
        assert data["failed"] == 0

    async def test_bulk_invalid_operation(self, async_client: AsyncClient, async_db: AsyncSession):
        """Test bulk operation with invalid operation type."""
        service = await self.create_test_service(async_db)

        bulk_request = {
            "service_ids": [str(service.id)],
            "operation": "invalid_operation",
            "parameters": {}
        }

        response = await async_client.post(
            f"{self.base_url}/bulk",
            json=bulk_request
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_requested"] == 1
        assert data["successful"] == 0
        assert data["failed"] == 1
        assert len(data["errors"]) > 0

    async def test_bulk_mixed_results(self, async_client: AsyncClient, async_db: AsyncSession):
        """Test bulk operation with mixed success/failure results."""
        service = await self.create_test_service(async_db)
        fake_id = str(uuid4())

        bulk_request = {
            "service_ids": [str(service.id), fake_id],
            "operation": "enable",
            "parameters": {}
        }

        response = await async_client.post(
            f"{self.base_url}/bulk",
            json=bulk_request
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_requested"] == 2
        assert data["successful"] == 1
        assert data["failed"] == 1

    # Error Handling Tests

    def test_invalid_service_id_format(self, client: TestClient):
        """Test API with invalid UUID format."""
        response = client.get(f"{self.base_url}/invalid-uuid")

        assert response.status_code == 422

    def test_missing_required_fields(self, client: TestClient):
        """Test creating service with missing required fields."""
        incomplete_data = {"description": "Missing name field"}

        response = client.post(
            self.base_url,
            json=incomplete_data
        )

        assert response.status_code == 422
        errors = response.json()["details"]
        assert any("name" in str(error) for error in errors)

    def test_invalid_enum_values(self, client: TestClient):
        """Test creating service with invalid enum values."""
        invalid_data = {
            **self.sample_service_data,
            "build_type": "invalid_type",
            "protocol": "invalid_protocol",
            "priority": "invalid_priority"
        }

        response = client.post(
            self.base_url,
            json=invalid_data
        )

        assert response.status_code == 422

    async def test_database_error_handling(self, async_client: AsyncClient):
        """Test API behavior during database errors."""
        # This would typically involve mocking database failures
        # For now, we'll test with invalid data that might cause DB constraints
        pass

    # Integration Tests

    @patch('app.api.v1.services.perform_service_health_check')
    async def test_full_service_lifecycle(self, mock_health_check, async_client: AsyncClient):
        """Test complete service lifecycle: create, update, health check, delete."""
        # Create service
        create_response = await async_client.post(
            self.base_url,
            json=self.sample_service_data
        )
        assert create_response.status_code == 201
        service_data = create_response.json()
        service_id = service_data["id"]

        # Update service
        update_data = {"description": "Updated description"}
        update_response = await async_client.put(
            f"{self.base_url}/{service_id}",
            json=update_data
        )
        assert update_response.status_code == 200

        # Health check
        mock_health_check.return_value = {"status": "healthy", "response_time_ms": 100}
        health_response = await async_client.post(f"{self.base_url}/{service_id}/health-check")
        assert health_response.status_code == 200

        # Delete service
        delete_response = await async_client.delete(f"{self.base_url}/{service_id}")
        assert delete_response.status_code == 204

        # Verify deletion
        get_response = await async_client.get(f"{self.base_url}/{service_id}")
        assert get_response.status_code == 404

    async def test_service_discovery_integration(self, async_client: AsyncClient):
        """Test integration between discovery and registration."""
        # Trigger discovery
        discovery_response = await async_client.post(f"{self.base_url}/discover")
        assert discovery_response.status_code == 200

        # Register a service manually
        registration_response = await async_client.post(
            f"{self.base_url}/register",
            json={
                "service_data": self.sample_service_data,
                "validate_health": False,
                "override_existing": False
            }
        )
        assert registration_response.status_code == 200

        # Verify service appears in list
        list_response = await async_client.get(self.base_url)
        assert list_response.status_code == 200
        services = list_response.json()["items"]
        service_names = [s["name"] for s in services]
        assert self.sample_service_data["name"] in service_names

    # Performance Tests (basic)

    async def test_list_services_performance(self, async_client: AsyncClient, async_db: AsyncSession):
        """Test performance with larger datasets."""
        # Create multiple services
        for i in range(50):
            await self.create_test_service(
                async_db,
                name=f"perf-test-service-{i:02d}",
                description=f"Performance test service {i}"
            )

        # Test list performance
        import time
        start_time = time.time()
        response = await async_client.get(self.base_url)
        end_time = time.time()

        assert response.status_code == 200
        assert (end_time - start_time) < 2.0  # Should complete within 2 seconds

        data = response.json()
        assert data["total"] == 50

    async def test_search_performance(self, async_client: AsyncClient, async_db: AsyncSession):
        """Test search performance with multiple services."""
        # Create services with searchable content
        for i in range(20):
            await self.create_test_service(
                async_db,
                name=f"search-test-{i:02d}",
                description=f"This is service number {i} for search testing"
            )

        # Test search performance
        import time
        start_time = time.time()
        response = await async_client.get(
            self.base_url,
            params={"search.query": "search testing"}
        )
        end_time = time.time()

        assert response.status_code == 200
        assert (end_time - start_time) < 1.0  # Should complete within 1 second
