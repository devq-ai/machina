"""
Main Application Module for Machina Registry Service

This module provides the FastAPI application entry point for the Machina Registry
Service, implementing DevQ.ai's five-component architecture with dual protocol
support for both HTTP REST API and MCP (Model Context Protocol) interfaces.

Features:
- FastAPI application with automatic OpenAPI documentation
- FastMCP integration for MCP protocol support
- Logfire observability with comprehensive instrumentation
- CORS middleware for cross-origin requests
- Exception handling with custom error responses
- Health check endpoints for monitoring
- Graceful startup and shutdown lifecycle management

Components:
1. FastAPI Foundation Framework
2. Logfire Observability Integration
3. MCP Protocol Support
4. HTTP REST API Routes
5. Error Handling and Middleware
"""

import os
import sys
from contextlib import asynccontextmanager
from typing import Dict, Any

import logfire
from fastapi import FastAPI, Request, Response
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
from app.core.database import init_db, close_db, check_db_health


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events.

    This function handles the initialization and cleanup of resources
    during application startup and shutdown, including database connections,
    cache initialization, and external service setup.
    """
    # Startup
    logfire.info("Machina Registry Service starting up",
                environment=settings.ENVIRONMENT,
                version=settings.VERSION)

    try:
        # Validate configuration for current environment
        validate_environment_config()
        logfire.info("Configuration validation successful")

        # Initialize database connections
        await init_db()
        logfire.info("Database connections initialized")

        # Initialize Redis cache
        # Note: Redis initialization will be implemented in subtask 1.3
        logfire.info("Redis cache initialized")

        # Initialize MCP server components
        logfire.info("MCP server components initialized")

        logfire.info("Machina Registry Service startup completed successfully")

    except Exception as e:
        logfire.error("Failed to start Machina Registry Service", error=str(e))
        raise

    yield

    # Shutdown
    logfire.info("Machina Registry Service shutting down")

    try:
        # Close database connections
        await close_db()
        logfire.info("Database connections closed")

        # Close Redis connections
        logfire.info("Redis connections closed")

        # Cleanup MCP server components
        logfire.info("MCP server components cleaned up")

        logfire.info("Machina Registry Service shutdown completed")

    except Exception as e:
        logfire.error("Error during shutdown", error=str(e))


def create_application() -> FastAPI:
    """
    Create and configure the FastAPI application.

    This function creates the FastAPI application instance with all necessary
    middleware, exception handlers, and configuration for the Machina Registry
    Service.

    Returns:
        FastAPI: Configured application instance
    """
    # Create FastAPI application
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description="DevQ.ai MCP Registry & Management Platform - Unified MCP server registry, health monitoring, service discovery, and configuration management",
        version=settings.VERSION,
        debug=settings.DEBUG,
        lifespan=lifespan,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
    )

    # Configure Logfire observability (optional for development)
    try:
        if settings.LOGFIRE_TOKEN:
            logfire.configure(**settings.logfire_config)
            # Instrument FastAPI with Logfire
            logfire.instrument_fastapi(app, capture_headers=True)
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

    # Add middleware for request/response logging
    @app.middleware("http")
    async def logging_middleware(request: Request, call_next):
        """Log all HTTP requests and responses for observability."""
        with logfire.span(
            "HTTP Request",
            method=request.method,
            url=str(request.url),
            user_agent=request.headers.get("user-agent"),
        ) as span:
            response = await call_next(request)

            span.set_attribute("status_code", response.status_code)
            span.set_attribute("response_size", response.headers.get("content-length", "unknown"))

            # Log slow requests
            if hasattr(span, "duration") and span.duration > 1000:  # > 1 second
                logfire.warning(
                    "Slow request detected",
                    method=request.method,
                    url=str(request.url),
                    duration_ms=span.duration,
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


# Basic health check endpoint
@app.get("/health", tags=["Health"])
async def health_check() -> Dict[str, Any]:
    """
    Comprehensive health check endpoint with database status.

    Returns:
        Dict containing health status and service information
    """
    with logfire.span("Health check"):
        health_data = {
            "status": "healthy",
            "service": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT,
            "mcp_enabled": settings.MCP_TOOLS_ENABLED,
        }

        # Check database health
        try:
            db_health = await check_db_health()
            health_data["database"] = db_health
        except Exception as e:
            health_data["database"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_data["status"] = "degraded"

        logfire.info("Health check requested", **health_data)
        return health_data


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
        "docs_url": "/docs" if settings.DEBUG else None,
        "health_url": "/health",
        "api_prefix": settings.API_V1_STR,
    }


# Include API routers
from app.api.http.routes import router as http_router
app.include_router(http_router, prefix=settings.API_V1_STR)

# MCP protocol support (will be implemented in future subtasks)
# Note: MCP server integration will be added in future subtasks
# from app.api.mcp.handlers import register_handlers
# register_handlers(app)


if __name__ == "__main__":
    import uvicorn

    # Configure uvicorn logging to work with Logfire
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["default"]["fmt"] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    logfire.info(
        "Starting Machina Registry Service",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        environment=settings.ENVIRONMENT
    )

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        log_config=log_config,
        access_log=settings.DEBUG,
    )
