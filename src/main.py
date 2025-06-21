"""
Main Application Module for Machina Registry Service

This module provides the FastAPI application entry point for the Machina Registry
Service, implementing DevQ.ai's five-component architecture with dual protocol
support for both HTTP REST API and MCP (Model Context Protocol) interfaces.

Features:
- FastAPI application with automatic OpenAPI documentation
- Redis cache and pub/sub integration
- Logfire observability with comprehensive instrumentation
- CORS middleware for cross-origin requests
- Exception handling with custom error responses
- Health check endpoints for monitoring
- Graceful startup and shutdown lifecycle management

Components:
1. FastAPI Foundation Framework
2. Logfire Observability Integration
3. Database Integration (PostgreSQL)
4. Redis Cache and Pub/Sub System
5. Error Handling and Middleware
"""

import os
import sys
from typing import Dict, Any

import logfire
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

# Add src to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.core.config import settings, validate_environment_config
from app.core.exceptions import (
    MachinaException,
    create_http_exception,
    handle_exception,
)
from app.core.initialization import lifespan, get_application_health, is_application_ready


def create_application() -> FastAPI:
    """
    Create and configure the FastAPI application.

    This function creates the FastAPI application instance with all necessary
    middleware, exception handlers, and configuration for the Machina Registry
    Service.

    Returns:
        FastAPI: Configured application instance
    """
    # Create FastAPI application with integrated lifecycle management
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description="DevQ.ai MCP Registry & Management Platform - Unified MCP server registry, health monitoring, service discovery, and configuration management",
        version=settings.VERSION,
        debug=settings.DEBUG,
        lifespan=lifespan,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
    )

    # Configure Logfire observability
    try:
        if settings.LOGFIRE_TOKEN:
            logfire.configure(**settings.logfire_config)
            # Instrument FastAPI with Logfire
            logfire.instrument_fastapi(app, capture_headers=True)
            # Instrument database and cache connections
            logfire.instrument_sqlalchemy()
            logfire.instrument_httpx()
            logfire.info("Logfire observability configured successfully")
        else:
            logfire.info("Logfire token not provided, running without observability")
    except Exception as e:
        logfire.warning(f"Logfire configuration failed: {e}, continuing without observability")

    # Add CORS middleware
    if settings.CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ORIGINS,
            allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
            allow_methods=settings.CORS_ALLOW_METHODS,
            allow_headers=settings.CORS_ALLOW_HEADERS,
        )

    # Add middleware for request/response logging and performance monitoring
    @app.middleware("http")
    async def logging_middleware(request: Request, call_next):
        """Log all HTTP requests and responses for observability."""
        import time

        start_time = time.time()

        with logfire.span(
            "HTTP Request",
            method=request.method,
            url=str(request.url),
            user_agent=request.headers.get("user-agent"),
        ) as span:
            response = await call_next(request)

            process_time = time.time() - start_time

            span.set_attribute("status_code", response.status_code)
            span.set_attribute("process_time", process_time)
            span.set_attribute("response_size", response.headers.get("content-length", "unknown"))

            # Add process time header
            response.headers["X-Process-Time"] = str(process_time)

            # Log slow requests
            if process_time > 1.0:  # > 1 second
                logfire.warning(
                    "Slow request detected",
                    method=request.method,
                    url=str(request.url),
                    duration_ms=process_time * 1000,
                    status_code=response.status_code
                )

            return response

    return app


# Create the application instance
app = create_application()


# Exception handlers
@app.exception_handler(MachinaException)
async def machina_exception_handler(request: Request, exc: MachinaException):
    """Handle custom MachinaException instances."""
    logfire.error(
        "MachinaException handled",
        error_code=exc.error_code,
        message=exc.message,
        path=request.url.path,
        method=request.method,
        context=exc.context
    )

    http_exc = create_http_exception(exc)
    return JSONResponse(
        status_code=http_exc.status_code,
        content=http_exc.detail
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle standard HTTP exceptions."""
    logfire.warning(
        "HTTP exception",
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path,
        method=request.method
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": f"HTTP_{exc.status_code}",
            "message": exc.detail,
            "type": "HTTPException"
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors."""
    logfire.warning(
        "Request validation error",
        errors=exc.errors(),
        path=request.url.path,
        method=request.method
    )

    return JSONResponse(
        status_code=422,
        content={
            "error_code": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "type": "ValidationError",
            "details": exc.errors()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions."""
    machina_exc = handle_exception(exc)

    logfire.error(
        "Unhandled exception",
        exception_type=type(exc).__name__,
        message=str(exc),
        path=request.url.path,
        method=request.method,
        machina_error_code=machina_exc.error_code
    )

    if settings.DEBUG:
        # In debug mode, include the full traceback
        import traceback
        machina_exc.context["traceback"] = traceback.format_exc()

    http_exc = create_http_exception(machina_exc)
    return JSONResponse(
        status_code=http_exc.status_code,
        content=http_exc.detail
    )


# Health check endpoints
@app.get("/health", tags=["Health"])
async def health_check() -> Dict[str, Any]:
    """
    Comprehensive health check endpoint with all service status.

    Returns:
        Dict containing health status and service information
    """
    with logfire.span("Health check"):
        try:
            health_data = await get_application_health()

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
                "error": str(e),
                "service": settings.PROJECT_NAME,
                "version": settings.VERSION
            }


@app.get("/health/ready", tags=["Health"])
async def readiness_check() -> Dict[str, Any]:
    """
    Readiness check endpoint for Kubernetes/Docker deployments.

    Returns:
        Dict indicating if the service is ready to accept traffic
    """
    ready = is_application_ready()

    return {
        "ready": ready,
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "ready" if ready else "not_ready"
    }


@app.get("/health/live", tags=["Health"])
async def liveness_check() -> Dict[str, Any]:
    """
    Liveness check endpoint for Kubernetes/Docker deployments.

    Returns:
        Dict indicating if the service is alive
    """
    return {
        "alive": True,
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "uptime": "operational"
    }


@app.get("/", tags=["Root"])
async def root() -> Dict[str, Any]:
    """
    Root endpoint providing basic service information.

    Returns:
        Dict containing service information and available endpoints
    """
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "description": "DevQ.ai MCP Registry & Management Platform",
        "environment": settings.ENVIRONMENT,
        "features": {
            "mcp_enabled": settings.MCP_TOOLS_ENABLED,
            "cache_enabled": True,
            "observability_enabled": bool(settings.LOGFIRE_TOKEN),
            "debug_mode": settings.DEBUG
        },
        "endpoints": {
            "docs": "/docs" if settings.DEBUG else None,
            "health": "/health",
            "ready": "/health/ready",
            "live": "/health/live",
            "api": settings.API_V1_STR,
            "tasks": f"{settings.API_V1_STR}/tasks",
            "task_stats": f"{settings.API_V1_STR}/tasks/statistics",
            "task_enums": f"{settings.API_V1_STR}/tasks/enums"
        },
    }


# Cache management endpoints for development/debugging
if settings.DEBUG:
    @app.post("/debug/cache/clear", tags=["Debug"])
    async def clear_cache():
        """Clear all cache entries (DEBUG ONLY)."""
        try:
            from app.core.cache import get_cache_service
            cache_service = await get_cache_service()

            # Clear cache statistics
            await cache_service.clear_stats()

            logfire.info("Cache cleared via debug endpoint")
            return {"message": "Cache cleared successfully"}

        except Exception as e:
            logfire.error("Failed to clear cache", error=str(e))
            return {"error": str(e)}

    @app.get("/debug/cache/stats", tags=["Debug"])
    async def get_cache_stats():
        """Get cache statistics (DEBUG ONLY)."""
        try:
            from app.services.cache_service import get_cache_utilities
            cache_utils = await get_cache_utilities()

            metrics = await cache_utils.get_cache_metrics()
            return metrics

        except Exception as e:
            logfire.error("Failed to get cache stats", error=str(e))
            return {"error": str(e)}


# Include API routers
from app.api.v1.taskmaster import router as taskmaster_router
app.include_router(taskmaster_router, prefix=settings.API_V1_STR)

# MCP protocol support - Register MCP handlers
if settings.MCP_TOOLS_ENABLED:
    from app.mcp.handlers import register_mcp_handlers
    mcp_handlers = register_mcp_handlers(app)
    logfire.info("MCP protocol support enabled and handlers registered")
else:
    logfire.info("MCP protocol support disabled")


if __name__ == "__main__":
    import uvicorn

    # Validate configuration before starting
    try:
        validate_environment_config()
    except Exception as e:
        logfire.error("Configuration validation failed", error=str(e))
        sys.exit(1)

    # Configure uvicorn logging to work with Logfire
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["default"]["fmt"] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    logfire.info(
        "Starting Machina Registry Service",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        environment=settings.ENVIRONMENT,
        project_name=settings.PROJECT_NAME,
        version=settings.VERSION
    )

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        log_config=log_config,
        access_log=settings.DEBUG,
    )
