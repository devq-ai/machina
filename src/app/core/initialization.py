"""
Application Initialization Module for Machina Registry Service

This module provides centralized initialization and shutdown procedures for all
core services including database, cache, and observability components. It implements
DevQ.ai's standard initialization patterns with proper error handling and logging.

Features:
- Coordinated startup and shutdown of all services
- Health check aggregation across all components
- Graceful error handling during initialization
- Service dependency management
- Logfire observability integration
- Environment-specific initialization logic
"""

import asyncio
import signal
import sys
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager

import logfire
from fastapi import FastAPI

from .config import Settings, get_settings
from .database import init_db, close_db, check_db_health
from .cache import get_cache_service, close_cache_service
from .exceptions import InitializationError


class ServiceManager:
    """
    Centralized service manager for application lifecycle.

    Manages initialization, health monitoring, and shutdown of all
    core services in the proper order with dependency handling.
    """

    def __init__(self, settings: Settings):
        """
        Initialize service manager.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.services_initialized: List[str] = []
        self.shutdown_handlers: List[callable] = []
        self._health_check_cache: Optional[Dict[str, Any]] = None
        self._last_health_check: Optional[float] = None

    async def initialize_all_services(self) -> None:
        """
        Initialize all application services in the correct order.

        Order of initialization:
        1. Logfire observability
        2. Database connections
        3. Redis cache service
        4. Additional services (future expansion)

        Raises:
            InitializationError: If any service fails to initialize
        """
        try:
            with logfire.span("Application Service Initialization"):
                logfire.info(
                    "Starting service initialization",
                    environment=self.settings.ENVIRONMENT,
                    project_name=self.settings.PROJECT_NAME
                )

                # 1. Initialize Logfire (already done via config, but verify)
                await self._initialize_observability()

                # 2. Initialize Database
                await self._initialize_database()

                # 3. Initialize Cache Service
                await self._initialize_cache()

                # 4. Register shutdown handlers
                self._register_shutdown_handlers()

                logfire.info(
                    "All services initialized successfully",
                    services=self.services_initialized,
                    total_services=len(self.services_initialized)
                )

        except Exception as e:
            logfire.error(
                "Service initialization failed",
                error=str(e),
                initialized_services=self.services_initialized
            )

            # Attempt cleanup of partially initialized services
            await self._emergency_cleanup()
            raise InitializationError(
                f"Failed to initialize services: {str(e)}"
            ) from e

    async def _initialize_observability(self) -> None:
        """Initialize Logfire observability."""
        try:
            with logfire.span("Logfire Initialization"):
                # Logfire is already configured via settings, just verify
                logfire.info("Logfire observability active")
                self.services_initialized.append("logfire")

        except Exception as e:
            raise InitializationError(f"Failed to initialize observability: {str(e)}") from e

    async def _initialize_database(self) -> None:
        """Initialize database connections."""
        try:
            with logfire.span("Database Service Initialization"):
                await init_db()

                # Verify database connectivity
                health = await check_db_health()
                if health.get("status") != "healthy":
                    raise InitializationError("Database health check failed")

                self.services_initialized.append("database")
                self.shutdown_handlers.append(close_db)

                logfire.info("Database service initialized successfully")

        except Exception as e:
            raise InitializationError(f"Failed to initialize database: {str(e)}") from e

    async def _initialize_cache(self) -> None:
        """Initialize Redis cache service."""
        try:
            with logfire.span("Cache Service Initialization"):
                cache_service = await get_cache_service(self.settings)

                # Verify cache connectivity
                health = await cache_service.health_check()
                if health.get("status") != "healthy":
                    raise InitializationError("Cache health check failed")

                self.services_initialized.append("cache")
                self.shutdown_handlers.append(close_cache_service)

                logfire.info("Cache service initialized successfully")

        except Exception as e:
            raise InitializationError(f"Failed to initialize cache: {str(e)}") from e

    def _register_shutdown_handlers(self) -> None:
        """Register signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logfire.info(f"Received signal {signum}, initiating graceful shutdown...")
            asyncio.create_task(self.shutdown_all_services())

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def shutdown_all_services(self) -> None:
        """
        Shutdown all services in reverse order of initialization.

        Ensures graceful cleanup of all resources with proper error handling.
        """
        try:
            with logfire.span("Application Service Shutdown"):
                logfire.info(
                    "Starting graceful shutdown",
                    services_to_shutdown=len(self.shutdown_handlers)
                )

                # Execute shutdown handlers in reverse order
                for handler in reversed(self.shutdown_handlers):
                    try:
                        await handler()
                        logfire.debug(f"Shutdown handler completed: {handler.__name__}")
                    except Exception as e:
                        logfire.error(
                            f"Error during shutdown of {handler.__name__}",
                            error=str(e)
                        )

                self.services_initialized.clear()
                self.shutdown_handlers.clear()

                logfire.info("Graceful shutdown completed")

        except Exception as e:
            logfire.error("Error during shutdown", error=str(e))

    async def _emergency_cleanup(self) -> None:
        """Emergency cleanup for failed initialization."""
        logfire.warning("Performing emergency cleanup after initialization failure")

        for handler in reversed(self.shutdown_handlers):
            try:
                await handler()
            except Exception as cleanup_error:
                logfire.error(
                    f"Emergency cleanup failed for {handler.__name__}",
                    error=str(cleanup_error)
                )

    async def get_service_health(self, use_cache: bool = True) -> Dict[str, Any]:
        """
        Get comprehensive health status of all services.

        Args:
            use_cache: Whether to use cached health data (for performance)

        Returns:
            Dictionary containing health status of all services
        """
        import time

        # Check if we should use cached results
        current_time = time.time()
        if (use_cache and self._health_check_cache and self._last_health_check and
            (current_time - self._last_health_check) < 30):  # 30 second cache
            return self._health_check_cache

        try:
            with logfire.span("Service Health Check"):
                health_data = {
                    "overall_status": "healthy",
                    "timestamp": current_time,
                    "services": {},
                    "summary": {
                        "total_services": len(self.services_initialized),
                        "healthy_services": 0,
                        "unhealthy_services": 0
                    }
                }

                # Check database health
                if "database" in self.services_initialized:
                    try:
                        db_health = await check_db_health()
                        health_data["services"]["database"] = db_health
                        if db_health.get("status") == "healthy":
                            health_data["summary"]["healthy_services"] += 1
                        else:
                            health_data["summary"]["unhealthy_services"] += 1
                            health_data["overall_status"] = "degraded"
                    except Exception as e:
                        health_data["services"]["database"] = {
                            "status": "unhealthy",
                            "error": str(e)
                        }
                        health_data["summary"]["unhealthy_services"] += 1
                        health_data["overall_status"] = "unhealthy"

                # Check cache health
                if "cache" in self.services_initialized:
                    try:
                        cache_service = await get_cache_service()
                        cache_health = await cache_service.health_check()
                        health_data["services"]["cache"] = cache_health
                        if cache_health.get("status") == "healthy":
                            health_data["summary"]["healthy_services"] += 1
                        else:
                            health_data["summary"]["unhealthy_services"] += 1
                            health_data["overall_status"] = "degraded"
                    except Exception as e:
                        health_data["services"]["cache"] = {
                            "status": "unhealthy",
                            "error": str(e)
                        }
                        health_data["summary"]["unhealthy_services"] += 1
                        health_data["overall_status"] = "unhealthy"

                # Cache the results
                self._health_check_cache = health_data
                self._last_health_check = current_time

                logfire.info(
                    "Health check completed",
                    overall_status=health_data["overall_status"],
                    healthy_services=health_data["summary"]["healthy_services"],
                    unhealthy_services=health_data["summary"]["unhealthy_services"]
                )

                return health_data

        except Exception as e:
            logfire.error("Health check failed", error=str(e))
            return {
                "overall_status": "error",
                "timestamp": current_time,
                "error": str(e),
                "services": {},
                "summary": {
                    "total_services": len(self.services_initialized),
                    "healthy_services": 0,
                    "unhealthy_services": len(self.services_initialized)
                }
            }

    def get_service_status(self) -> Dict[str, Any]:
        """
        Get current service initialization status.

        Returns:
            Dictionary with service status information
        """
        return {
            "initialized_services": self.services_initialized.copy(),
            "total_services": len(self.services_initialized),
            "shutdown_handlers": len(self.shutdown_handlers),
            "environment": self.settings.ENVIRONMENT,
            "project_name": self.settings.PROJECT_NAME
        }


# Global service manager instance
_service_manager: Optional[ServiceManager] = None


def get_service_manager(settings: Optional[Settings] = None) -> ServiceManager:
    """
    Get or create the global service manager instance.

    Args:
        settings: Optional settings instance

    Returns:
        ServiceManager: Global service manager
    """
    global _service_manager

    if _service_manager is None:
        if settings is None:
            settings = get_settings()
        _service_manager = ServiceManager(settings)

    return _service_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager for service initialization and cleanup.

    This function is used with FastAPI's lifespan parameter to ensure
    proper startup and shutdown of all services.

    Args:
        app: FastAPI application instance

    Usage:
        app = FastAPI(lifespan=lifespan)
    """
    service_manager = get_service_manager()

    try:
        # Startup
        logfire.info("Application startup initiated")
        await service_manager.initialize_all_services()

        # Store service manager in app state
        app.state.service_manager = service_manager

        logfire.info("Application startup completed successfully")
        yield

    except Exception as e:
        logfire.error("Application startup failed", error=str(e))
        # Attempt cleanup before re-raising
        await service_manager._emergency_cleanup()
        raise

    finally:
        # Shutdown
        logfire.info("Application shutdown initiated")
        await service_manager.shutdown_all_services()
        logfire.info("Application shutdown completed")


async def initialize_application(settings: Optional[Settings] = None) -> ServiceManager:
    """
    Initialize application services programmatically.

    Alternative to using the lifespan context manager for cases where
    you need manual control over service initialization.

    Args:
        settings: Optional settings instance

    Returns:
        ServiceManager: Initialized service manager

    Raises:
        InitializationError: If initialization fails
    """
    service_manager = get_service_manager(settings)
    await service_manager.initialize_all_services()
    return service_manager


async def shutdown_application() -> None:
    """
    Shutdown application services programmatically.

    Companion function to initialize_application() for manual
    service lifecycle management.
    """
    global _service_manager

    if _service_manager:
        await _service_manager.shutdown_all_services()
        _service_manager = None


async def get_application_health() -> Dict[str, Any]:
    """
    Get comprehensive application health status.

    Returns:
        Dictionary containing health information for all services
    """
    service_manager = get_service_manager()
    return await service_manager.get_service_health()


def is_application_ready() -> bool:
    """
    Check if application is fully initialized and ready.

    Returns:
        True if all critical services are initialized
    """
    global _service_manager

    if not _service_manager:
        return False

    required_services = {"database", "cache"}
    initialized_services = set(_service_manager.services_initialized)

    return required_services.issubset(initialized_services)


# Development and testing utilities
async def reset_application_state() -> None:
    """
    Reset application state for testing.

    WARNING: This should only be used in testing environments.
    """
    global _service_manager

    if _service_manager:
        await _service_manager.shutdown_all_services()

    _service_manager = None

    logfire.warning("Application state reset - FOR TESTING ONLY")


def get_initialization_status() -> Dict[str, Any]:
    """
    Get current initialization status for monitoring.

    Returns:
        Dictionary with initialization status information
    """
    global _service_manager

    if not _service_manager:
        return {
            "status": "not_initialized",
            "services": [],
            "ready": False
        }

    return {
        "status": "initialized" if _service_manager.services_initialized else "initializing",
        "services": _service_manager.services_initialized.copy(),
        "ready": is_application_ready(),
        "service_count": len(_service_manager.services_initialized)
    }
